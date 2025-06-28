"""
spottycat.commands.requests - Spot request management commands

This module implements commands for creating, listing, and canceling 
AWS spot instance requests.
"""

import click
from rich.console import Console
from rich.table import Table
import json
from . import print_budget_alerts


@click.group()
def requests():
    """Manage AWS spot instance requests."""
    pass


@requests.command()
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
@click.pass_context
def list(ctx, as_json):
    """List current AWS spot instance requests."""
    console = Console()
    aws_client = ctx.obj.get('aws_client')
    debug = ctx.obj.get('debug', False)
    if not aws_client:
        console.print('[bold red]Error:[/bold red] AWS client not initialized. Check your credentials and config.')
        return
    print_budget_alerts(ctx)
    try:
        requests_data = [
            req for req in aws_client.describe_spot_instance_requests_paginated()
        ]
        if as_json:
            console.print_json(json.dumps(requests_data))
        else:
            table = Table(title="Spot Instance Requests")
            table.add_column("Request ID", style="cyan", no_wrap=True)
            table.add_column("State", style="magenta")
            table.add_column("Type", style="green")
            table.add_column("Instance Type", style="yellow")
            table.add_column("Status Message", style="white")
            found = False
            for req in requests_data:
                found = True
                table.add_row(
                    req.get('SpotInstanceRequestId', ''),
                    req.get('State', ''),
                    req.get('Type', ''),
                    req.get('LaunchSpecification', {}).get('InstanceType', ''),
                    req.get('Status', {}).get('Message', '')
                )
            if found:
                console.print(table)
            else:
                console.print('[bold yellow]No spot instance requests found.[/bold yellow]')
        if debug:
            console.print(f"[debug] Spot requests raw result: {requests_data}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


@requests.command()
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
@click.pass_context
def create(ctx, as_json):
    """Create a new spot instance request using the latest launch template."""
    console = Console()
    aws_client = ctx.obj.get('aws_client')
    config = ctx.obj.get('config')
    debug = ctx.obj.get('debug', False)
    if not aws_client:
        console.print('[bold red]Error:[/bold red] AWS client not initialized. Check your credentials and config.')
        return
    print_budget_alerts(ctx)
    try:
        # 1. Check for key pairs
        key_pairs = aws_client.ec2_client.describe_key_pairs().get('KeyPairs', [])
        # 2. Check for security groups
        sec_groups = aws_client.ec2_client.describe_security_groups().get('SecurityGroups', [])
        # 3. Check for launch templates
        launch_templates = aws_client.ec2_client.describe_launch_templates().get('LaunchTemplates', [])
        missing = []
        if not key_pairs:
            missing.append('SSH key pair')
        if not sec_groups:
            missing.append('security group')
        if not launch_templates:
            missing.append('launch template')
        if missing:
            console.print(f"[bold red]Cannot create spot request. Missing required configuration: {', '.join(missing)}[/bold red]")
            if 'SSH key pair' in missing:
                console.print("[yellow]Create a key pair with: spottycat keys create <key-name>[/yellow]")
            if 'security group' in missing:
                console.print("[yellow]Create a security group with: spottycat security-groups create[/yellow]")
            if 'launch template' in missing:
                console.print("[yellow]Create a launch template with: spottycat templates create --instance-type <type>[/yellow]")
            return
        # List resources for confirmation
        console.print("[bold green]Found the following resources:[/bold green]")
        table = Table(title="Key Pairs")
        table.add_column("Key Name", style="cyan")
        table.add_column("Fingerprint", style="magenta")
        for key in key_pairs:
            table.add_row(key.get('KeyName', ''), key.get('KeyFingerprint', ''))
        console.print(table)
        table = Table(title="Security Groups")
        table.add_column("Group ID", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Description", style="green")
        for group in sec_groups:
            table.add_row(group.get('GroupId', ''), group.get('GroupName', ''), group.get('Description', ''))
        console.print(table)
        table = Table(title="Launch Templates")
        table.add_column("Template ID", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Latest Version", style="green")
        for tmpl in launch_templates:
            table.add_row(tmpl.get('LaunchTemplateId', ''), tmpl.get('LaunchTemplateName', ''), str(tmpl.get('LatestVersionNumber', '')))
        console.print(table)
        # Use the latest launch template
        latest_template = sorted(launch_templates, key=lambda t: t.get('CreateTime', ''), reverse=True)[0]
        template_id = latest_template['LaunchTemplateId']
        template_name = latest_template['LaunchTemplateName']
        version = str(latest_template['LatestVersionNumber'])
        # Confirm with user
        if not as_json:
            if not click.confirm(f"Proceed to submit spot request using launch template '{template_name}' (ID: {template_id}, version: {version})?"):
                console.print("[yellow]Aborted by user.[/yellow]")
                return
        # Prepare spot request
        # Use config for instance count, max price, etc.
        spot_cfg = config.config_data.get('spot', {}) if config else {}
        max_price = spot_cfg.get('max_spot_price') or None
        instance_count = config.config_data.get('instances', {}).get('max_concurrent_instances', 1) if config else 1
        # Use key pair and security group from config if set, else pick first
        key_name = config.config_data.get('security', {}).get('key_pair', {}).get('name') if config else None
        if not key_name and key_pairs:
            key_name = key_pairs[0].get('KeyName')
        sg_id = None
        sg_cfg = config.config_data.get('security', {}).get('security_group', {}) if config else {}
        if sg_cfg.get('name'):
            for group in sec_groups:
                if group.get('GroupName') == sg_cfg['name']:
                    sg_id = group.get('GroupId')
                    break
        if not sg_id and sec_groups:
            sg_id = sec_groups[0].get('GroupId')
        # Build launch specification
        launch_spec = {
            'KeyName': key_name,
            'SecurityGroupIds': [sg_id] if sg_id else [],
        }
        # Submit spot request
        try:
            req_args = {
                'InstanceCount': instance_count,
                'LaunchTemplate': {
                    'LaunchTemplateId': template_id,
                    'Version': version
                },
                'Type': 'one-time',
            }
            if max_price:
                req_args['SpotPrice'] = str(max_price)
            if key_name:
                launch_spec['KeyName'] = key_name
            if sg_id:
                launch_spec['SecurityGroupIds'] = [sg_id]
            # Attach launch spec if needed (for overrides)
            if launch_spec['KeyName'] or launch_spec['SecurityGroupIds']:
                req_args['LaunchSpecification'] = launch_spec
            response = aws_client.ec2_client.request_spot_instances(**req_args)
            requests = response.get('SpotInstanceRequests', [])
            if as_json:
                console.print_json(json.dumps(requests, default=str))
            else:
                for req in requests:
                    console.print(f"[bold green]Spot request submitted! ID: {req.get('SpotInstanceRequestId')} Status: {req.get('State')}[/bold green]")
        except Exception as e:
            console.print(f"[bold red]Error submitting spot request:[/bold red] {e}")
        if debug:
            console.print(f"[debug] Spot request args: {req_args}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


@requests.command()
@click.argument('request_id')
@click.pass_context
def cancel(ctx, request_id):
    """Cancel a spot instance request by ID (stub)."""
    click.echo(f"[stub] Cancel spot request {request_id}: Not yet implemented.")


# Placeholder for spot request-related commands
# Will be implemented in task 4.2 