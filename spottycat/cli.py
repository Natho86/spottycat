"""
spottycat.cli - Main CLI entry point

Main Click CLI application with command groups for managing AWS GPU spot instances.
Provides global options, configuration management, and lazy command loading.
"""

import os
import sys
import logging
from typing import Optional

import click
import colorama
from colorama import Fore, Style

from spottycat import __version__
from spottycat.core.config import Config
from spottycat.core.aws_client import AWSClient


# Initialize colorama for cross-platform colored output
colorama.init()


def setup_logging(debug: bool = False) -> None:
    """Configure logging based on debug mode."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Reduce boto3/botocore logging noise in non-debug mode
    if not debug:
        logging.getLogger('boto3').setLevel(logging.WARNING)
        logging.getLogger('botocore').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)


def validate_aws_credentials(profile: Optional[str] = None, region: Optional[str] = None) -> bool:
    """Validate AWS credentials and connectivity."""
    try:
        # This will raise an exception if credentials are invalid
        aws_client = AWSClient(profile=profile, region=region)
        aws_client.get_current_user()
        return True
    except Exception as e:
        click.echo(f"{Fore.RED}Error: AWS credentials validation failed: {e}{Style.RESET_ALL}", err=True)
        return False


class SpottyCatGroup(click.Group):
    """Custom Click group with enhanced functionality."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._commands_loaded = False
    
    def list_commands(self, ctx):
        """Return list of available commands."""
        self._ensure_commands_loaded()
        return super().list_commands(ctx)
    
    def get_command(self, ctx, cmd_name):
        """Get command by name, loading command groups if needed."""
        self._ensure_commands_loaded()
        return super().get_command(ctx, cmd_name)
    
    def _ensure_commands_loaded(self):
        """Lazy load command groups."""
        if self._commands_loaded:
            return
        
        try:
            # Import and register command groups
            from spottycat.commands.quotas import quotas
            from spottycat.commands.requests import requests
            from spottycat.commands.instances import instances
            from spottycat.commands.templates import templates
            from spottycat.commands.keys import keys
            from spottycat.commands.security_groups import security_groups
            
            # Register command groups
            self.add_command(quotas)
            self.add_command(requests)
            self.add_command(instances)
            self.add_command(templates)
            self.add_command(keys)
            self.add_command(security_groups)
            
            self._commands_loaded = True
            
        except ImportError as e:
            # Commands not yet implemented - this is expected during development
            logging.debug(f"Command import failed (expected during development): {e}")


@click.group(cls=SpottyCatGroup, context_settings={'help_option_names': ['-h', '--help']})
@click.version_option(version=__version__, prog_name='spottycat')
@click.option(
    '--debug/--no-debug', 
    default=False, 
    envvar='SPOTTYCAT_DEBUG',
    help='Enable debug mode with verbose logging'
)
@click.option(
    '--profile', 
    envvar='SPOTTYCAT_AWS_PROFILE',
    help='AWS profile name to use (overrides AWS_PROFILE)'
)
@click.option(
    '--region', 
    envvar='SPOTTYCAT_AWS_REGION',
    help='AWS region to use (overrides AWS_DEFAULT_REGION)'
)
@click.option(
    '--config', 
    '-c',
    type=click.Path(exists=True),
    envvar='SPOTTYCAT_CONFIG',
    help='Path to configuration file'
)
@click.option(
    '--no-color',
    is_flag=True,
    envvar='SPOTTYCAT_NO_COLOR',
    help='Disable colored output'
)
@click.pass_context
def cli(ctx, debug, profile, region, config, no_color):
    """
    🐱 spottycat - AWS GPU Spot Instance Manager
    
    A comprehensive CLI tool for managing AWS GPU spot instances with:
    • Intelligent cost control and budget management
    • Automated launch template creation
    • Real-time quota and pricing monitoring
    • Security group and SSH key management
    
    Examples:
      spottycat quotas list --instance-type g4dn.xlarge
      spottycat requests create --template my-gpu-template --max-price 0.50
      spottycat instances list --running
    """
    # Disable colorama if requested
    if no_color:
        colorama.deinit()
    
    # Setup logging
    setup_logging(debug)
    
    # Ensure that ctx.obj exists and is a dict for sharing state
    ctx.ensure_object(dict)
    
    # Load configuration
    try:
        config_obj = Config(config_path=config)
        ctx.obj['config'] = config_obj
    except Exception as e:
        if debug:
            click.echo(f"{Fore.YELLOW}Warning: Could not load configuration: {e}{Style.RESET_ALL}", err=True)
        ctx.obj['config'] = Config()  # Use default config
    
    # Override config with CLI options
    if profile:
        ctx.obj['config'].aws.profile = profile
    if region:
        ctx.obj['config'].aws.region = region
    
    # Store global state in context
    ctx.obj['debug'] = debug
    ctx.obj['no_color'] = no_color
    
    # Initialize AWS client with retry logic
    try:
        aws_client = AWSClient(
            profile=ctx.obj['config'].aws.profile,
            region=ctx.obj['config'].aws.region
        )
        ctx.obj['aws_client'] = aws_client
    except Exception as e:
        if debug:
            logging.exception("Failed to initialize AWS client")
        ctx.obj['aws_client'] = None
        if ctx.invoked_subcommand and ctx.invoked_subcommand not in ['--help', '--version']:
            click.echo(f"{Fore.RED}Error: Failed to initialize AWS client: {e}{Style.RESET_ALL}", err=True)
            click.echo(f"{Fore.YELLOW}Hint: Check your AWS credentials and configuration{Style.RESET_ALL}", err=True)


@cli.command()
@click.pass_context
def config_check(ctx):
    """Check configuration and AWS connectivity."""
    config_obj = ctx.obj.get('config')
    aws_client = ctx.obj.get('aws_client')
    
    click.echo(f"{Fore.CYAN}Configuration Check{Style.RESET_ALL}")
    click.echo("=" * 50)
    
    # Check configuration
    if config_obj:
        click.echo(f"{Fore.GREEN}✓{Style.RESET_ALL} Configuration loaded successfully")
        click.echo(f"  Config file: {config_obj.config_file or 'default'}")
        click.echo(f"  AWS Profile: {config_obj.aws.profile or 'default'}")
        click.echo(f"  AWS Region: {config_obj.aws.region or 'us-east-1'}")
    else:
        click.echo(f"{Fore.RED}✗{Style.RESET_ALL} Configuration failed to load")
    
    # Check AWS connectivity
    if aws_client:
        try:
            user_info = aws_client.get_current_user()
            click.echo(f"{Fore.GREEN}✓{Style.RESET_ALL} AWS connectivity verified")
            click.echo(f"  User ARN: {user_info.get('Arn', 'Unknown')}")
            click.echo(f"  User ID: {user_info.get('UserId', 'Unknown')}")
        except Exception as e:
            click.echo(f"{Fore.RED}✗{Style.RESET_ALL} AWS connectivity failed: {e}")
    else:
        click.echo(f"{Fore.RED}✗{Style.RESET_ALL} AWS client not initialized")
    
    # Check permissions (basic test)
    if aws_client:
        try:
            # Test basic EC2 permissions
            aws_client.ec2_client.describe_regions(RegionNames=[aws_client.region])
            click.echo(f"{Fore.GREEN}✓{Style.RESET_ALL} Basic EC2 permissions verified")
        except Exception as e:
            click.echo(f"{Fore.YELLOW}⚠{Style.RESET_ALL} EC2 permissions check failed: {e}")


def main():
    """Entry point for the CLI application."""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo(f"\n{Fore.YELLOW}Operation cancelled by user{Style.RESET_ALL}", err=True)
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        click.echo(f"{Fore.RED}Unexpected error: {e}{Style.RESET_ALL}", err=True)
        logging.exception("Unexpected error in main CLI")
        sys.exit(1)


if __name__ == '__main__':
    main() 