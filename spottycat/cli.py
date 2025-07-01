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
        config_obj = Config(config_file=config)
        config_obj.load_config()  # Ensure config is loaded!
        ctx.obj['config'] = config_obj
    except Exception as e:
        if debug:
            click.echo(f"{Fore.YELLOW}Warning: Could not load configuration: {e}{Style.RESET_ALL}", err=True)
        config_obj = Config()
        config_obj.load_config()
        ctx.obj['config'] = config_obj
    
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


@cli.command()
@click.option('--key-name', default='spottycat-key', help='Name for the SSH key pair')
@click.option('--key-type', type=click.Choice(['rsa', 'ed25519']), default='rsa', help='Type of SSH key')
@click.option('--output', '-o', type=click.Path(), help='Path to save the downloaded private key')
@click.option('--security-group', default='spottycat-sg', help='Name for the security group')
@click.pass_context
def up(ctx, key_name, key_type, output, security_group):
    """
    Automated setup: create security group, SSH key, and launch templates for all available GPU instance types.
    Now always creates/uses the security group in the default VPC.
    """
    from rich.console import Console
    import os
    console = Console()
    aws_client = ctx.obj.get('aws_client')
    config_obj = ctx.obj.get('config')
    debug = ctx.obj.get('debug', False)
    if not aws_client:
        console.print('[bold red]Error:[/bold red] AWS client not initialized. Check your credentials and config.')
        return

    # Ensure config is loaded (in case it was not)
    if hasattr(config_obj, 'load_config'):
        config_obj.load_config()

    # S3 bucket prompt logic (move to start)
    s3_bucket = config_obj.config_data.get('s3_bucket', {}).get('name', '') if config_obj else ''
    if not s3_bucket:
        s3_bucket = click.prompt(
            "Enter S3 bucket name for wordlists/rules (leave blank to skip)",
            default="", show_default=False
        )
        if config_obj:
            if 's3_bucket' not in config_obj.config_data:
                config_obj.config_data['s3_bucket'] = {}
            config_obj.config_data['s3_bucket']['name'] = s3_bucket
    if s3_bucket:
        console.print(f"[cyan]S3 bucket set to:[/cyan] {s3_bucket}")
    else:
        console.print("[yellow]No S3 bucket will be used. Instances will not sync wordlists/rules from S3.[/yellow]")

    # 1. Find the default VPC
    try:
        vpcs = aws_client.ec2_client.describe_vpcs(Filters=[{'Name': 'isDefault', 'Values': ['true']}])['Vpcs']
        if not vpcs:
            console.print('[bold red]No default VPC found in this region.[/bold red]')
            return
        default_vpc_id = vpcs[0]['VpcId']
    except Exception as e:
        console.print(f"[bold red]Error finding default VPC:[/bold red] {e}")
        return

    # 2. Ensure security group exists in the default VPC
    sg_id = None
    try:
        sgs = aws_client.ec2_client.describe_security_groups(
            Filters=[{'Name': 'group-name', 'Values': [security_group]}, {'Name': 'vpc-id', 'Values': [default_vpc_id]}]
        )['SecurityGroups']
        if sgs:
            sg_id = sgs[0]['GroupId']
            console.print(f"[green]Security group '{security_group}' already exists in default VPC (ID: {sg_id})[/green]")
        else:
            resp = aws_client.ec2_client.create_security_group(
                GroupName=security_group,
                Description='SpottyCat managed security group',
                VpcId=default_vpc_id,
                TagSpecifications=[{
                    'ResourceType': 'security-group',
                    'Tags': [{'Key': 'CreatedBy', 'Value': 'spottycat'}]
                }]
            )
            sg_id = resp['GroupId']
            # Allow SSH
            aws_client.ec2_client.authorize_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=[{
                    'IpProtocol': 'tcp',
                    'FromPort': 22,
                    'ToPort': 22,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                }]
            )
            console.print(f"[green]Created security group '{security_group}' in default VPC (ID: {sg_id})[/green]")
    except Exception as e:
        console.print(f"[bold red]Error ensuring security group:[/bold red] {e}")
        return

    # 2. Ensure SSH key pair exists and download
    key_path = output or os.path.expanduser(f"~/.spottycat/{key_name}.pem")
    os.makedirs(os.path.dirname(key_path), exist_ok=True)
    key_exists = False
    try:
        keys = aws_client.ec2_client.describe_key_pairs(KeyNames=[key_name])['KeyPairs']
        if keys:
            key_exists = True
            console.print(f"[green]SSH key pair '{key_name}' already exists in AWS[/green]")
            if not os.path.exists(key_path):
                console.print(f"[yellow]Private key not found locally at {key_path}. Please download it from AWS if needed.[/yellow]")
        else:
            key_exists = False
    except Exception:
        key_exists = False
    if not key_exists:
        try:
            resp = aws_client.ec2_client.create_key_pair(KeyName=key_name, KeyType=key_type)
            private_key = resp.get('KeyMaterial')
            with open(key_path, 'w') as f:
                f.write(private_key)
            os.chmod(key_path, 0o400)
            console.print(f"[green]Created SSH key pair '{key_name}' and saved private key to {key_path}[/green]")
        except Exception as e:
            console.print(f"[bold red]Error creating SSH key pair:[/bold red] {e}")
            return

    # 3. Query available GPU instance types (using quotas logic or static list)
    # For demo, use a static list; in production, query quotas or config
    gpu_types = [
        'g4dn.xlarge', 'g4dn.2xlarge', 'p3.2xlarge', 'g5.xlarge', 'g3.4xlarge'
    ]
    # TODO: Optionally, dynamically query quotas for available types

    # 4. For each type, ensure launch template exists
    from spottycat.utils.launch_template_builder import LaunchTemplateBuilder
    builder = LaunchTemplateBuilder(aws_client)
    created_templates = []
    for instance_type in gpu_types:
        template_name = f"spottycat-{instance_type.replace('.', '-')}-template"
        try:
            existing = aws_client.ec2_client.describe_launch_templates(
                Filters=[{'Name': 'launch-template-name', 'Values': [template_name]}]
            )['LaunchTemplates']
            if existing:
                console.print(f"[green]Launch template '{template_name}' already exists[/green]")
                continue
            # Build template config
            config = builder.build_template(
                instance_type=instance_type,
                key_name=key_name,
                config=config_obj,
                region=aws_client.region,
                ami_id=None,
                user_data=None
            )
            req = {
                'LaunchTemplateName': template_name,
                'VersionDescription': 'Created by spottycat up',
                'LaunchTemplateData': config
            }
            resp = aws_client.ec2_client.create_launch_template(**req)
            created_templates.append(template_name)
            console.print(f"[green]Created launch template '{template_name}' for {instance_type}[/green]")
        except Exception as e:
            console.print(f"[yellow]Skipped or failed to create template '{template_name}': {e}[/yellow]")

    # 5. Print summary and next steps
    console.print(f"\n[bold green]Setup complete![/bold green]")
    console.print(f"Security group: [cyan]{security_group}[/cyan] (ID: {sg_id})")
    console.print(f"SSH key: [cyan]{key_name}[/cyan] (private key at {key_path})")
    console.print(f"Launch templates created for: [magenta]{', '.join(gpu_types)}[/magenta]")
    console.print("You can now submit a spot instance request, e.g.:")
    console.print(f"[bold]spottycat requests submit --instance-type g4dn.xlarge[/bold]")

    # 6. Optionally, offer to add to ~/.ssh/config
    ssh_config_path = os.path.expanduser('~/.ssh/config')
    if click.confirm(f"Add entry to {ssh_config_path} for this key?", default=False):
        host_block = f"\nHost spottycat-gpu\n    HostName <instance-public-ip>\n    User ubuntu\n    IdentityFile {key_path}\n    IdentitiesOnly yes\n    StrictHostKeyChecking no\n"
        with open(ssh_config_path, 'a') as f:
            f.write(host_block)
        console.print(f"[green]Added SSH config entry. Replace <instance-public-ip> with your instance's public IP.[/green]")


@cli.command()
@click.pass_context
def cleanup(ctx):
    """
    Remove all spottycat-managed AWS resources and local SSH config/key.
    """
    from rich.console import Console
    import os
    import re
    console = Console()
    aws_client = ctx.obj.get('aws_client')
    config_obj = ctx.obj.get('config')
    debug = ctx.obj.get('debug', False)
    if not aws_client:
        console.print('[bold red]Error:[/bold red] AWS client not initialized. Check your credentials and config.')
        return

    # 1. Terminate all running spottycat EC2 instances
    console.print('[cyan]Terminating all running spottycat EC2 instances...[/cyan]')
    reservations = aws_client.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': ['pending', 'running', 'stopping', 'stopped']}]).get('Reservations', [])
    spottycat_instance_ids = []
    for reservation in reservations:
        for inst in reservation.get('Instances', []):
            tags = {t['Key']: t['Value'] for t in inst.get('Tags', [])} if inst.get('Tags') else {}
            if any('spottycat' in (tags.get(k, '')).lower() for k in tags) or 'spottycat' in inst.get('InstanceType', '').lower():
                spottycat_instance_ids.append(inst['InstanceId'])
    if spottycat_instance_ids:
        aws_client.ec2_client.terminate_instances(InstanceIds=spottycat_instance_ids)
        console.print(f"[green]Terminated instances: {', '.join(spottycat_instance_ids)}[/green]")
    else:
        console.print('[yellow]No spottycat EC2 instances found.[/yellow]')

    # 2. Cancel all spottycat spot requests
    console.print('[cyan]Canceling all spottycat spot requests...[/cyan]')
    spot_requests = aws_client.ec2_client.describe_spot_instance_requests().get('SpotInstanceRequests', [])
    spottycat_request_ids = [r['SpotInstanceRequestId'] for r in spot_requests if 'spottycat' in (r.get('LaunchGroup', '') + r.get('SpotInstanceRequestId', '')).lower()]
    if spottycat_request_ids:
        aws_client.ec2_client.cancel_spot_instance_requests(SpotInstanceRequestIds=spottycat_request_ids)
        console.print(f"[green]Canceled spot requests: {', '.join(spottycat_request_ids)}[/green]")
    else:
        console.print('[yellow]No spottycat spot requests found.[/yellow]')

    # 3. Delete all spottycat launch templates
    console.print('[cyan]Deleting all spottycat launch templates...[/cyan]')
    templates = aws_client.ec2_client.describe_launch_templates().get('LaunchTemplates', [])
    deleted_templates = []
    for tmpl in templates:
        if 'spottycat' in tmpl.get('LaunchTemplateName', '').lower():
            aws_client.ec2_client.delete_launch_template(LaunchTemplateId=tmpl['LaunchTemplateId'])
            deleted_templates.append(tmpl['LaunchTemplateName'])
    if deleted_templates:
        console.print(f"[green]Deleted launch templates: {', '.join(deleted_templates)}[/green]")
    else:
        console.print('[yellow]No spottycat launch templates found.[/yellow]')

    # 4. Delete the spottycat security group in the default VPC
    console.print('[cyan]Deleting spottycat security group...[/cyan]')
    try:
        vpcs = aws_client.ec2_client.describe_vpcs(Filters=[{'Name': 'isDefault', 'Values': ['true']}])['Vpcs']
        if vpcs:
            default_vpc_id = vpcs[0]['VpcId']
            sgs = aws_client.ec2_client.describe_security_groups(Filters=[{'Name': 'group-name', 'Values': ['spottycat-sg']}, {'Name': 'vpc-id', 'Values': [default_vpc_id]}])['SecurityGroups']
            for sg in sgs:
                try:
                    aws_client.ec2_client.delete_security_group(GroupId=sg['GroupId'])
                    console.print(f"[green]Deleted security group: {sg['GroupId']}[/green]")
                except Exception as e:
                    console.print(f"[yellow]Could not delete security group {sg['GroupId']}: {e}")
        else:
            console.print('[yellow]No default VPC found.[/yellow]')
    except Exception as e:
        console.print(f"[yellow]Error deleting security group: {e}")

    # 5. Delete the spottycat-key SSH key pair from AWS and local disk
    console.print('[cyan]Deleting spottycat-key SSH key pair from AWS and local disk...[/cyan]')
    try:
        aws_client.ec2_client.delete_key_pair(KeyName='spottycat-key')
        console.print('[green]Deleted SSH key pair spottycat-key from AWS.[/green]')
    except Exception as e:
        console.print(f"[yellow]Could not delete SSH key pair from AWS: {e}")
    key_path = os.path.expanduser('~/.spottycat/spottycat-key.pem')
    if os.path.exists(key_path):
        os.remove(key_path)
        console.print(f"[green]Deleted local SSH key: {key_path}[/green]")
    else:
        console.print(f"[yellow]No local SSH key found at {key_path}.[/yellow]")

    # 6. Remove the spottycat SSH config entry from ~/.ssh/config
    console.print('[cyan]Removing spottycat SSH config entry from ~/.ssh/config...[/cyan]')
    ssh_config_path = os.path.expanduser('~/.ssh/config')
    if os.path.exists(ssh_config_path):
        with open(ssh_config_path, 'r') as f:
            lines = f.readlines()
        new_lines = []
        in_block = False
        for line in lines:
            if re.match(r'^Host +spottycat-gpu', line):
                in_block = True
                continue
            if in_block and line.startswith('Host '):
                in_block = False
            if not in_block:
                new_lines.append(line)
        with open(ssh_config_path, 'w') as f:
            f.writelines(new_lines)
        console.print('[green]Removed spottycat SSH config entry.[/green]')
    else:
        console.print('[yellow]No SSH config file found at ~/.ssh/config.[/yellow]')

    console.print('[bold green]Cleanup complete![/bold green]')


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