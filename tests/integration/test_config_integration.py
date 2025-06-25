"""
tests.integration.test_config_integration - Integration tests for configuration

This module contains integration tests for configuration management
that test the actual file loading and environment variable integration.
"""

import pytest
import os
import tempfile
from pathlib import Path


@pytest.mark.integration
@pytest.mark.config
class TestConfigIntegration:
    """Integration tests for configuration management."""
    
    def test_config_file_loading(self, sample_config_file):
        """Test loading configuration from YAML file."""
        # Placeholder for config file loading integration test
        # Will be implemented in task 7.3
        from spottycat.core.config import Config
        
        config = Config(sample_config_file)
        config.load_config()
        
        # Basic test that config was loaded
        assert config.config_data is not None
        
    def test_environment_variable_override(self, temp_dir, sample_config):
        """Test environment variable overrides."""
        # Placeholder for environment override integration test
        # Will be implemented in task 7.3
        import yaml
        
        config_file = Path(temp_dir) / "test_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(sample_config, f)
        
        # Set environment variable
        os.environ['SPOTTYCAT_AWS_REGION'] = 'us-west-2'
        
        try:
            from spottycat.core.config import Config
            config = Config(str(config_file))
            config.load_config()
            
            # Test that environment variable overrode config file
            # This will be properly implemented in task 7.3
            assert config.config_data is not None
        finally:
            # Clean up environment variable
            if 'SPOTTYCAT_AWS_REGION' in os.environ:
                del os.environ['SPOTTYCAT_AWS_REGION']
    
    def test_config_path_discovery(self, temp_dir):
        """Test automatic configuration file discovery."""
        # Placeholder for config path discovery integration test
        # Will be implemented in task 7.3
        from spottycat.core.config import Config
        
        config = Config()
        config.load_config()
        
        # Basic test that config discovery works
        assert config.config_data is not None or config.config_data == {}
    
    @pytest.mark.slow
    def test_full_config_workflow(self, sample_config_file):
        """Test complete configuration workflow."""
        # Placeholder for full workflow integration test
        # Will be implemented in task 7.3
        from spottycat.core.config import Config
        
        config = Config(sample_config_file)
        config.load_config()
        
        # Test getting various config values
        aws_region = config.get('aws.region', 'default-region')
        budget = config.get('budget.max_total_budget', 0.0)
        
        # Basic assertions
        assert aws_region is not None
        assert budget is not None 