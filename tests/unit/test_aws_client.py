"""
tests.unit.test_aws_client - Unit tests for AWS client wrapper

This module contains unit tests for AWS client wrapper with mocked boto3 responses.
"""

import pytest
from unittest.mock import Mock, patch


@pytest.mark.unit
@pytest.mark.aws
@pytest.mark.mock
class TestAWSClient:
    """Test cases for the AWS client wrapper."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Placeholder for test setup
        # Will be implemented in task 7.1
        pass
    
    @patch('boto3.Session')
    def test_aws_client_initialization(self, mock_session):
        """Test AWS client initialization with/without profile/region."""
        from spottycat.core.aws_client import AWSClient
        mock_session.return_value = Mock()
        # Default
        client = AWSClient()
        assert client.session is not None
        # With profile
        client = AWSClient(profile='test-profile')
        assert client.profile == 'test-profile'
        # With region
        client = AWSClient(region='us-west-2')
        assert client.region == 'us-west-2'
    
    @patch('boto3.Session')
    def test_ec2_client_creation(self, mock_session):
        """Test EC2 client creation and describe_instances call."""
        from spottycat.core.aws_client import AWSClient
        mock_sess = Mock()
        mock_ec2 = Mock()
        mock_sess.client.return_value = mock_ec2
        mock_session.return_value = mock_sess
        client = AWSClient()
        # describe_instances
        mock_ec2.describe_instances.return_value = {'Reservations': []}
        resp = client.describe_instances()
        assert resp == {'Reservations': []}
        mock_ec2.describe_instances.assert_called_once()
    
    @patch('boto3.Session')
    def test_describe_spot_instance_requests(self, mock_session):
        """Test describe_spot_instance_requests call."""
        from spottycat.core.aws_client import AWSClient
        mock_sess = Mock()
        mock_ec2 = Mock()
        mock_sess.client.return_value = mock_ec2
        mock_session.return_value = mock_sess
        client = AWSClient()
        mock_ec2.describe_spot_instance_requests.return_value = {'SpotInstanceRequests': []}
        resp = client.describe_spot_instance_requests()
        assert resp == {'SpotInstanceRequests': []}
        mock_ec2.describe_spot_instance_requests.assert_called_once()
    
    @patch('boto3.Session')
    def test_get_current_user(self, mock_session):
        """Test get_current_user returns identity and handles errors."""
        from spottycat.core.aws_client import AWSClient
        mock_sess = Mock()
        mock_sts = Mock()
        mock_sess.client.side_effect = lambda service, **kwargs: mock_sts if service == 'sts' else Mock()
        mock_session.return_value = mock_sess
        client = AWSClient()
        mock_sts.get_caller_identity.return_value = {'Arn': 'arn:aws:iam::123:user/test'}
        assert client.get_current_user()['Arn'] == 'arn:aws:iam::123:user/test'
        # Error case
        mock_sts.get_caller_identity.side_effect = Exception('NoCreds')
        try:
            client.get_current_user()
        except RuntimeError as e:
            assert 'Unable to get current AWS user' in str(e)
    
    @patch('boto3.Session')
    def test_get_gpu_instance_quota(self, mock_session):
        """Test get_gpu_instance_quota for known/unknown instance types."""
        from spottycat.core.aws_client import AWSClient
        mock_sess = Mock()
        mock_quotas = Mock()
        mock_sess.client.side_effect = lambda service, **kwargs: mock_quotas if service == 'service-quotas' else Mock()
        mock_session.return_value = mock_sess
        client = AWSClient()
        mock_quotas.get_service_quota.return_value = {'Quota': {'Value': 4.0}}
        assert client.get_gpu_instance_quota('g4dn.xlarge') == 4.0
        # Unknown family
        try:
            client.get_gpu_instance_quota('unknown.xlarge')
        except RuntimeError as e:
            assert 'No quota code mapping' in str(e)
    
    @patch('boto3.Session')
    def test_get_spot_price(self, mock_session):
        """Test get_spot_price for valid/invalid instance types."""
        from spottycat.core.aws_client import AWSClient
        mock_sess = Mock()
        mock_pricing = Mock()
        mock_sess.client.side_effect = lambda service, **kwargs: mock_pricing if service == 'pricing' else Mock()
        mock_session.return_value = mock_sess
        client = AWSClient()
        # Valid
        mock_pricing.get_products.return_value = {'PriceList': ['{"terms":{"OnDemand":{"X":{"priceDimensions":{"Y":{"pricePerUnit":{"USD":"0.42"}}}}}}']}
        assert client.get_spot_price('g4dn.xlarge', region='us-east-1') == 0.42
        # No price found
        mock_pricing.get_products.return_value = {'PriceList': []}
        try:
            client.get_spot_price('g4dn.xlarge', region='us-east-1')
        except RuntimeError as e:
            assert 'No spot price found' in str(e)
    
    @patch('boto3.Session')
    def test_error_handling(self, mock_session):
        """Test error handling for describe_instances and quotas."""
        from spottycat.core.aws_client import AWSClient
        mock_sess = Mock()
        mock_ec2 = Mock()
        mock_quotas = Mock()
        mock_sess.client.side_effect = lambda service, **kwargs: mock_ec2 if service == 'ec2' else (mock_quotas if service == 'service-quotas' else Mock())
        mock_session.return_value = mock_sess
        client = AWSClient()
        # describe_instances error
        mock_ec2.describe_instances.side_effect = Exception('fail')
        try:
            client.describe_instances()
        except RuntimeError as e:
            assert 'Unable to describe EC2 instances' in str(e)
        # quota error
        mock_quotas.get_service_quota.side_effect = Exception('fail')
        try:
            client.get_gpu_instance_quota('g4dn.xlarge')
        except RuntimeError as e:
            assert 'Unable to fetch GPU quota' in str(e)
    
    @patch('boto3.client')
    def test_ec2_client_creation(self, mock_client):
        """Test EC2 client creation."""
        # Placeholder for EC2 client creation test
        # Will be implemented in task 7.1
        mock_ec2 = Mock()
        mock_client.return_value = mock_ec2
        # Test will be implemented with actual EC2 client logic
        assert mock_client is not None
    
    def test_aws_client_with_profile(self, mock_aws_client):
        """Test AWS client initialization with profile."""
        # Placeholder for profile-based initialization test
        # Will be implemented in task 7.1
        assert mock_aws_client.profile is None  # Default profile
        
    def test_aws_client_with_region(self, mock_aws_client):
        """Test AWS client initialization with region."""
        # Placeholder for region-based initialization test
        # Will be implemented in task 7.1
        assert mock_aws_client.region == 'us-east-1'  # Test region
    
    @pytest.mark.mock
    def test_get_ec2_client(self, mock_aws_client, mock_ec2_client):
        """Test getting EC2 client."""
        # Placeholder for EC2 client getter test
        # Will be implemented in task 7.1
        mock_aws_client.get_ec2_client.return_value = mock_ec2_client
        client = mock_aws_client.get_ec2_client()
        assert client == mock_ec2_client
        mock_aws_client.get_ec2_client.assert_called_once()
    
    @pytest.mark.mock
    def test_get_pricing_client(self, mock_aws_client, mock_pricing_client):
        """Test getting Pricing client."""
        # Placeholder for Pricing client getter test
        # Will be implemented in task 7.1
        mock_aws_client.get_pricing_client.return_value = mock_pricing_client
        client = mock_aws_client.get_pricing_client()
        assert client == mock_pricing_client
        mock_aws_client.get_pricing_client.assert_called_once()
    
    @pytest.mark.mock
    def test_get_service_quotas_client(self, mock_aws_client, mock_service_quotas_client):
        """Test getting Service Quotas client."""
        # Placeholder for Service Quotas client getter test
        # Will be implemented in task 7.1
        mock_aws_client.get_service_quotas_client.return_value = mock_service_quotas_client
        client = mock_aws_client.get_service_quotas_client()
        assert client == mock_service_quotas_client
        mock_aws_client.get_service_quotas_client.assert_called_once() 