"""
spottycat.core.config - Configuration management

This module implements configuration management functionality
supporting both YAML files and environment variables.
"""

import os
from typing import Dict, Any
from types import SimpleNamespace


class Config:
    """
    Configuration management class supporting YAML files and environment variables.
    """
    
    def __init__(self, config_file=None):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Path to YAML configuration file
        """
        self.config_file = config_file
        self.config_data: Dict[str, Any] = {}
    
    def load_config(self):
        """Load configuration from file and environment variables."""
        import yaml
        
        # Default configuration paths to check
        default_paths = [
            "~/.spottycat/config.yaml",
            "~/.config/spottycat/config.yaml",
            "./config/config.yaml",
            "./spottycat.yaml"
        ]
        
        config_path = self.config_file
        if not config_path:
            # Try default paths
            for path in default_paths:
                expanded_path = os.path.expanduser(path)
                if os.path.exists(expanded_path):
                    config_path = expanded_path
                    break
        
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.config_data = yaml.safe_load(f) or {}
        
        # Override with environment variables if they exist
        self._load_env_overrides()
    
    def _load_env_overrides(self):
        """Load configuration overrides from environment variables."""
        env_mappings = {
            'SPOTTYCAT_AWS_REGION': ['aws', 'region'],
            'SPOTTYCAT_AWS_PROFILE': ['aws', 'profile'],
            'SPOTTYCAT_MAX_BUDGET': ['budget', 'max_total_budget'],
            'SPOTTYCAT_INSTANCE_TYPE': ['instances', 'default_instance_type'],
            'SPOTTYCAT_MAX_SPOT_PRICE': ['spot', 'max_spot_price'],
            'SPOTTYCAT_LOG_LEVEL': ['cli', 'log_level'],
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                self._set_nested_value(config_path, value)
    
    def _set_nested_value(self, path_list, value):
        """Set a nested configuration value."""
        current = self.config_data
        for key in path_list[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path_list[-1]] = value
    
    def get(self, key: str, default=None):
        """Get configuration value by key."""
        return self.config_data.get(key, default) 

    @property
    def aws(self):
        aws_dict = self.config_data.get('aws', {})
        # Ensure both profile and region are present as attributes
        return SimpleNamespace(
            profile=aws_dict.get('profile', None),
            region=aws_dict.get('region', None)
        )

    @property
    def profile(self):
        return self.aws.profile

    @property
    def region(self):
        return self.aws.region 

    def validate(self):
        """Validate required configuration fields for S3 and 7z archive usage."""
        s3_bucket = self.config_data.get('s3_bucket', {})
        if not s3_bucket.get('name'):
            raise ValueError("Missing required S3 bucket name in config under 's3_bucket.name'.")
        # Check for documentation note about .7z archives
        # (We can't enforce file upload, but we can check for the doc string in config)
        doc_lines = self.config_data.get('_comments', [])
        # If using ruamel.yaml or similar, you could check for comments, but with PyYAML, just ensure the field is present
        # Optionally, warn if user hasn't set a note about 7z usage
        # For now, just pass if s3_bucket.name is set
        return True 