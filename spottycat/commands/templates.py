"""
spottycat.commands.templates - Launch template management

This module implements commands for managing AWS launch templates
for GPU instances.
"""

import click
from rich.console import Console
from rich.table import Table
import json
from . import print_budget_alerts


@click.group()
def templates():
    """Manage AWS launch templates."""
    pass


@templates.command()
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
@click.pass_context
def list(ctx, as_json):
    """List available AWS launch templates."""
    console = Console()
    aws_client = ctx.obj.get('aws_client')
    debug = ctx.obj.get('debug', False)
    if not aws_client:
        console.print('[bold red]Error:[/bold red] AWS client not initialized. Check your credentials and config.')
        return
    print_budget_alerts(ctx)
    try:
        resp = aws_client.ec2_client.describe_launch_templates()
        templates = resp.get('LaunchTemplates', [])
        if as_json:
            console.print_json(json.dumps(templates, default=str))
            return
        if not templates:
            console.print('[bold yellow]No launch templates found.[/bold yellow]')
            return
        table = Table(title="Launch Templates")
        table.add_column("Template ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="magenta")
        table.add_column("Latest Version", style="green")
        table.add_column("Created", style="yellow")
        for tmpl in templates:
            table.add_row(
                tmpl.get('LaunchTemplateId', ''),
                tmpl.get('LaunchTemplateName', ''),
                str(tmpl.get('LatestVersionNumber', '')),
                str(tmpl.get('CreateTime', '')),
            )
        console.print(table)
        if debug:
            console.print(f"[debug] Launch templates raw result: {templates}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


@templates.command()
@click.option('--instance-type', required=True, help='EC2 instance type (e.g., g4dn.xlarge)')
@click.option('--ami-id', default=None, help='Custom AMI ID (overrides Ubuntu 22.04 selection)')
@click.option('--user-data-file', default=None, help='Path to custom user data script (optional)')
@click.option('--validate', is_flag=True, help='Validate the launch template before output')
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
@click.pass_context
def create(ctx, instance_type, ami_id, user_data_file, validate, as_json):
    """Create a new launch template with Ubuntu 22.04 AMI selection and optional custom user data."""
    console = Console()
    aws_client = ctx.obj.get('aws_client')
    config_obj = ctx.obj.get('config')
    debug = ctx.obj.get('debug', False)
    if not aws_client:
        console.print('[bold red]Error:[/bold red] AWS client not initialized. Check your credentials and config.')
        return
    print_budget_alerts(ctx)
    from spottycat.utils.launch_template_builder import LaunchTemplateBuilder
    try:
        # Ensure config is loaded
        if hasattr(config_obj, 'load_config'):
            config_obj.load_config()
        # Use config values for region/profile if not overridden
        region = config_obj.region or aws_client.region
        profile = config_obj.profile or aws_client.profile
        builder = LaunchTemplateBuilder(aws_client)
        # Build template using config values
        config = builder.build_template(
            instance_type,
            ami_id=ami_id,
            user_data=user_data_file,
            config=config_obj,
            region=region
        )
        if validate:
            is_valid, errors = builder.validate_template(config)
            if is_valid:
                console.print('[bold green]Template validation passed.[/bold green]')
            else:
                console.print('[bold red]Template validation failed:[/bold red]')
                for err in errors:
                    console.print(f'- {err}')
                return
        if as_json:
            console.print_json(json.dumps(config, default=str))
        else:
            table = Table(title="Launch Template Preview")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="magenta")
            for k, v in config.items():
                table.add_row(str(k), str(v))
            console.print(table)
        if debug:
            console.print(f"[debug] Launch template config: {config}")
        # Confirm with user before submitting to AWS
        if not as_json:
            if not click.confirm("Submit this launch template to AWS?"):
                console.print("[yellow]Aborted by user.[/yellow]")
                return
        # Prepare create_launch_template call
        template_name = f"spottycat-{instance_type.replace('.', '-')}-template"
        # Use config for name prefix if set
        lt_cfg = config_obj.config_data.get('launch_template', {}) if config_obj else {}
        name_prefix = lt_cfg.get('name_prefix', 'spottycat')
        template_name = f"{name_prefix}-{instance_type.replace('.', '-')}-template"
        # Build request
        req = {
            'LaunchTemplateName': template_name,
            'VersionDescription': 'Created by spottycat',
            'LaunchTemplateData': config
        }
        try:
            response = aws_client.ec2_client.create_launch_template(**req)
            if as_json:
                console.print_json(json.dumps(response, default=str))
            else:
                lt = response.get('LaunchTemplate', {})
                console.print(f"[bold green]Launch template created! ID: {lt.get('LaunchTemplateId')} Name: {lt.get('LaunchTemplateName')}[/bold green]")
                table = Table(title="Created Launch Template")
                table.add_column("Field", style="cyan")
                table.add_column("Value", style="magenta")
                for k, v in lt.items():
                    table.add_row(str(k), str(v))
                console.print(table)
        except Exception as e:
            console.print(f"[bold red]Error creating launch template in AWS:[/bold red] {e}")
        if debug:
            console.print(f"[debug] Launch template create request: {req}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


@templates.command()
@click.argument('template_id')
@click.pass_context
def delete(ctx, template_id):
    """Delete a launch template by ID."""
    console = Console()
    aws_client = ctx.obj.get('aws_client')
    debug = ctx.obj.get('debug', False)
    if not aws_client:
        console.print('[bold red]Error:[/bold red] AWS client not initialized. Check your credentials and config.')
        return
    print_budget_alerts(ctx)
    try:
        response = aws_client.ec2_client.delete_launch_template(LaunchTemplateId=template_id)
        console.print(f'[bold green]Launch template {template_id} deleted successfully.[/bold green]')
        if debug:
            console.print(f"[debug] Delete response: {response}")
    except Exception as e:
        console.print(f'[bold red]Error deleting launch template:[/bold red] {e}')


# Placeholder for launch template commands
# Will be implemented in task 4.4 