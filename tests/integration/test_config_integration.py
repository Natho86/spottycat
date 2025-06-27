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

    def test_s3_bucket_config_validation(self, tmp_path):
        """Test config validation for required S3 fields and 7z documentation."""
        from spottycat.core.config import Config
        import yaml
        # Valid config
        valid_config = {
            's3_bucket': {
                'name': 'spottycat-data-20250626',
                'instance_profile': 'spottycat-s3-profile'
            }
        }
        valid_file = tmp_path / "valid_config.yaml"
        with open(valid_file, 'w') as f:
            yaml.dump(valid_config, f)
        config = Config(str(valid_file))
        config.load_config()
        assert config.validate() is True

        # Invalid config (missing s3_bucket.name)
        invalid_config = {
            's3_bucket': {
                'instance_profile': 'spottycat-s3-profile'
            }
        }
        invalid_file = tmp_path / "invalid_config.yaml"
        with open(invalid_file, 'w') as f:
            yaml.dump(invalid_config, f)
        config = Config(str(invalid_file))
        config.load_config()
        import pytest
        with pytest.raises(ValueError, match="Missing required S3 bucket name"):
            config.validate()

    def test_user_data_script_includes_7z_decompression(self):
        """Test that the user data script includes S3 sync and 7z decompression for wordlists and rules."""
        from spottycat.utils.user_data_scripts import UserDataScriptGenerator
        s3_bucket = "spottycat-data-20250626"
        wordlists_prefix = "wordlists/"
        rules_prefix = "rules/"
        gen = UserDataScriptGenerator()
        # Simulate the script generation as in launch_template_builder
        script = f"""
# Install AWS CLI if not present
apt-get install -y awscli

# Create mount points
mkdir -p /mnt/wordlists
mkdir -p /mnt/rules

# Sync wordlists and rules from S3 bucket
aws s3 sync s3://{s3_bucket}/{wordlists_prefix} /mnt/wordlists/
aws s3 sync s3://{s3_bucket}/{rules_prefix} /mnt/rules/
"""
        script += gen.generate_7z_decompression_script("/mnt/wordlists", cleanup=True)
        script += gen.generate_7z_decompression_script("/mnt/rules", cleanup=True)
        # Check for expected commands
        assert "apt-get install -y p7zip-full" in script
        assert "7z x \"$archive\" -o/mnt/wordlists" in script
        assert "7z x \"$archive\" -o/mnt/rules" in script
        assert "aws s3 sync s3://spottycat-data-20250626/wordlists/ /mnt/wordlists/" in script
        assert "aws s3 sync s3://spottycat-data-20250626/rules/ /mnt/rules/" in script 

    def test_cracked_sync_script_includes_error_handling(self):
        """Test that the cracked sync script includes error handling/logging and directory creation."""
        from spottycat.utils.user_data_scripts import UserDataScriptGenerator
        gen = UserDataScriptGenerator()
        script = gen.generate_cracked_sync_script("mybucket", "cracked/")
        assert "mkdir -p /mnt/cracked" in script
        assert "/var/log/cracked-upload.log" in script
        assert "if ! aws s3 cp" in script
        assert "Failed to upload $file to S3" in script
        assert "Uploading $file to s3://mybucket/cracked/" in script 