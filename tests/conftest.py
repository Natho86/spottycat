"""
tests.conftest - Shared test fixtures and configuration

This module provides pytest fixtures for testing spottycat functionality,
including AWS client mocking, CLI testing, and configuration management.
"""

import os
import pytest
import tempfile
import shutil
from unittest.mock import Mock, patch
from pathlib import Path

# Import Click testing utilities
from click.testing import CliRunner

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "data"


@pytest.fixture
def cli_runner():
    """Provide a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_dir():
    """Provide a temporary directory that gets cleaned up after test."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_aws_credentials():
    """Mock AWS credentials for testing."""
    with patch.dict(os.environ, {
        'AWS_ACCESS_KEY_ID': 'testing',
        'AWS_SECRET_ACCESS_KEY': 'testing',
        'AWS_SECURITY_TOKEN': 'testing',
        'AWS_SESSION_TOKEN': 'testing',
        'AWS_DEFAULT_REGION': 'us-east-1'
    }):
        yield


@pytest.fixture
def mock_ec2_client():
    """Provide a mocked EC2 client."""
    with patch('boto3.client') as mock_client:
        mock_ec2 = Mock()
        mock_client.return_value = mock_ec2
        
        # Mock common EC2 responses
        mock_ec2.describe_instances.return_value = {
            'Reservations': []
        }
        mock_ec2.describe_spot_instance_requests.return_value = {
            'SpotInstanceRequests': []
        }
        mock_ec2.describe_spot_price_history.return_value = {
            'SpotPriceHistory': [
                {
                    'InstanceType': 'g4dn.xlarge',
                    'ProductDescription': 'Linux/UNIX',
                    'SpotPrice': '0.30',
                    'Timestamp': '2023-01-01T00:00:00Z',
                    'AvailabilityZone': 'us-east-1a'
                }
            ]
        }
        
        yield mock_ec2


@pytest.fixture
def mock_pricing_client():
    """Provide a mocked AWS Pricing client."""
    with patch('boto3.client') as mock_client:
        mock_pricing = Mock()
        mock_client.return_value = mock_pricing
        
        # Mock pricing response
        mock_pricing.get_products.return_value = {
            'PriceList': [
                '{"product":{"productFamily":"Compute Instance"},"terms":{"OnDemand":{"PRICE123":{"priceDimensions":{"PRICE123.JRTCKXETXF":{"unit":"Hrs","pricePerUnit":{"USD":"0.526"}}}}}}}'
            ]
        }
        
        yield mock_pricing


@pytest.fixture
def mock_service_quotas_client():
    """Provide a mocked Service Quotas client."""
    with patch('boto3.client') as mock_client:
        mock_quotas = Mock()
        mock_client.return_value = mock_quotas
        
        # Mock service quotas response
        mock_quotas.get_service_quota.return_value = {
            'Quota': {
                'ServiceCode': 'ec2',
                'QuotaCode': 'L-DB2E81BA',
                'QuotaName': 'Running On-Demand G instances',
                'Value': 8.0,
                'Unit': 'None'
            }
        }
        
        yield mock_quotas


@pytest.fixture
def sample_config():
    """Provide a sample configuration dictionary."""
    return {
        'aws': {
            'region': 'us-east-1',
            'profile': '',
            'fallback_regions': ['us-west-2', 'eu-west-1']
        },
        'budget': {
            'max_total_budget': 100.0,
            'max_per_instance_budget': 50.0,
            'tracking_period': 'daily',
            'alerts': {
                'warning_threshold': 75,
                'critical_threshold': 90
            }
        },
        'instances': {
            'preferred_types': ['g4dn.xlarge', 'g4dn.2xlarge'],
            'default_instance_type': 'g4dn.xlarge',
            'max_concurrent_instances': 3
        },
        'spot': {
            'max_spot_price': '',
            'interruption_behavior': 'terminate',
            'persistent': False
        }
    }


@pytest.fixture
def sample_config_file(temp_dir, sample_config):
    """Provide a temporary configuration file."""
    import yaml
    
    config_file = Path(temp_dir) / "test_config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(sample_config, f)
    
    return str(config_file)


@pytest.fixture
def mock_aws_client():
    """Provide a mocked AWSClient instance."""
    from spottycat.core.aws_client import AWSClient
    
    with patch.object(AWSClient, '__init__', return_value=None):
        mock_client = AWSClient.__new__(AWSClient)
        mock_client.profile = None
        mock_client.region = 'us-east-1'
        
        # Add mocked methods
        mock_client.get_ec2_client = Mock()
        mock_client.get_pricing_client = Mock()
        mock_client.get_service_quotas_client = Mock()
        
        yield mock_client


@pytest.fixture
def mock_cost_calculator():
    """Provide a mocked CostCalculator instance."""
    from spottycat.core.cost_calculator import CostCalculator
    
    with patch.object(CostCalculator, '__init__', return_value=None):
        mock_calc = CostCalculator.__new__(CostCalculator)
        mock_calc.aws_client = Mock()
        
        # Add mocked methods
        mock_calc.calculate_spot_price = Mock(return_value=0.30)
        mock_calc.calculate_budget_remaining = Mock(return_value=75.0)
        mock_calc.check_budget_alerts = Mock(return_value=[])
        
        yield mock_calc


@pytest.fixture
def mock_config():
    """Provide a mocked Config instance."""
    from spottycat.core.config import Config
    
    with patch.object(Config, '__init__', return_value=None):
        mock_conf = Config.__new__(Config)
        mock_conf.config_file = None
        mock_conf.config_data = {}
        
        # Add mocked methods
        mock_conf.load_config = Mock()
        mock_conf.get = Mock(side_effect=lambda key, default=None: default)
        
        yield mock_conf


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    original_env = os.environ.copy()
    
    # Set test-specific environment variables
    os.environ['SPOTTYCAT_TEST_MODE'] = 'true'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_launch_template_builder():
    """Provide a mocked LaunchTemplateBuilder instance."""
    from spottycat.utils.launch_template_builder import LaunchTemplateBuilder
    
    with patch.object(LaunchTemplateBuilder, '__init__', return_value=None):
        mock_builder = LaunchTemplateBuilder.__new__(LaunchTemplateBuilder)
        mock_builder.aws_client = Mock()
        
        # Add mocked methods
        mock_builder.build_template = Mock(return_value={
            'LaunchTemplateName': 'test-template',
            'LaunchTemplateData': {
                'ImageId': 'ami-12345678',
                'InstanceType': 'g4dn.xlarge',
                'KeyName': 'test-keypair'
            }
        })
        
        yield mock_builder


@pytest.fixture
def mock_user_data_generator():
    """Provide a mocked UserDataScriptGenerator instance."""
    from spottycat.utils.user_data_scripts import UserDataScriptGenerator
    
    with patch.object(UserDataScriptGenerator, '__init__', return_value=None):
        mock_generator = UserDataScriptGenerator.__new__(UserDataScriptGenerator)
        
        # Add mocked methods
        mock_generator.generate_nvidia_driver_script = Mock(return_value="#!/bin/bash\n# NVIDIA driver installation")
        mock_generator.generate_cuda_toolkit_script = Mock(return_value="#!/bin/bash\n# CUDA toolkit installation")
        mock_generator.generate_hashcat_script = Mock(return_value="#!/bin/bash\n# Hashcat installation")
        mock_generator.combine_scripts = Mock(return_value="#!/bin/bash\n# Combined installation script")
        
        yield mock_generator


# Test data fixtures
@pytest.fixture
def sample_spot_instance_request():
    """Provide sample spot instance request data."""
    return {
        'SpotInstanceRequestId': 'sir-12345678',
        'SpotPrice': '0.30',
        'Type': 'one-time',
        'State': 'active',
        'Status': {
            'Code': 'fulfilled',
            'Message': 'Your Spot request is fulfilled.'
        },
        'InstanceId': 'i-1234567890abcdef0',
        'LaunchSpecification': {
            'ImageId': 'ami-12345678',
            'InstanceType': 'g4dn.xlarge',
            'KeyName': 'test-keypair'
        },
        'CreateTime': '2023-01-01T00:00:00Z'
    }


@pytest.fixture
def sample_ec2_instance():
    """Provide sample EC2 instance data."""
    return {
        'InstanceId': 'i-1234567890abcdef0',
        'InstanceType': 'g4dn.xlarge',
        'State': {
            'Name': 'running',
            'Code': 16
        },
        'PublicIpAddress': '203.0.113.1',
        'PrivateIpAddress': '10.0.1.100',
        'LaunchTime': '2023-01-01T00:00:00Z',
        'Tags': [
            {'Key': 'Name', 'Value': 'spottycat-instance'},
            {'Key': 'CreatedBy', 'Value': 'spottycat'}
        ]
    }


# Pytest hook to add custom markers
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests that don't require external dependencies"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests that may require AWS services"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take a long time to run"
    )
    config.addinivalue_line(
        "markers", "aws: Tests that interact with AWS services"
    )
    config.addinivalue_line(
        "markers", "mock: Tests that use mocked AWS services"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names."""
    for item in items:
        # Add markers based on test location and name
        if "test_aws" in item.nodeid:
            item.add_marker(pytest.mark.aws)
        if "test_cli" in item.nodeid:
            item.add_marker(pytest.mark.cli)
        if "mock" in item.name:
            item.add_marker(pytest.mark.mock)
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit) 