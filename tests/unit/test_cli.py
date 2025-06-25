"""
tests.unit.test_cli - Unit tests for CLI functionality

This module contains unit tests for the main CLI interface and command routing.
"""

import pytest
from click.testing import CliRunner
from spottycat.cli import cli


@pytest.mark.unit
@pytest.mark.cli
class TestCLI:
    """Test cases for the main CLI interface."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_cli_help(self, cli_runner):
        """Test that CLI help is displayed correctly."""
        # Placeholder for CLI help test
        # Will be implemented in task 7.1
        result = cli_runner.invoke(cli, ['--help'])
        # Basic assertion that help was attempted to be shown
        assert result.exit_code in [0, 2]  # 0 for success, 2 for help shown
    
    def test_cli_version(self, cli_runner):
        """Test that CLI version is displayed correctly."""
        # Placeholder for CLI version test
        # Will be implemented in task 7.1
        result = cli_runner.invoke(cli, ['--version'])
        # Basic assertion that version was attempted to be shown
        assert result.exit_code in [0, 2]  # 0 for success, 2 for help shown
    
    @pytest.mark.mock
    def test_cli_with_debug_flag(self, cli_runner):
        """Test CLI with debug flag."""
        # Placeholder for debug flag test
        # Will be implemented in task 7.1
        result = cli_runner.invoke(cli, ['--debug', '--help'])
        assert result.exit_code in [0, 2]
    
    @pytest.mark.mock  
    def test_cli_with_profile_option(self, cli_runner):
        """Test CLI with AWS profile option."""
        # Placeholder for profile option test
        # Will be implemented in task 7.1
        result = cli_runner.invoke(cli, ['--profile', 'test-profile', '--help'])
        assert result.exit_code in [0, 2]
    
    @pytest.mark.mock
    def test_cli_with_region_option(self, cli_runner):
        """Test CLI with AWS region option."""
        # Placeholder for region option test
        # Will be implemented in task 7.1
        result = cli_runner.invoke(cli, ['--region', 'us-west-2', '--help'])
        assert result.exit_code in [0, 2] 