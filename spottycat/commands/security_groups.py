"""
spottycat.commands.security_groups - Security group configuration

This module implements commands for security group creation and management
for GPU instances.
"""

import click
from rich.console import Console
from rich.table import Table
import json
from . import print_budget_alerts
import requests


@click.group()
def security_groups():
    """Manage security groups."""
    pass


@security_groups.command()
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
@click.pass_context
def list(ctx, as_json):
    """List available security groups."""
    console = Console()
    aws_client = ctx.obj.get('aws_client')
    debug = ctx.obj.get('debug', False)
    if not aws_client:
        console.print('[bold red]Error:[/bold red] AWS client not initialized. Check your credentials and config.')
        return
    print_budget_alerts(ctx)
    try:
        resp = aws_client.ec2_client.describe_security_groups()
        groups = resp.get('SecurityGroups', [])
        if as_json:
            console.print_json(json.dumps(groups, default=str))
            return
        if not groups:
            console.print('[bold yellow]No security groups found.[/bold yellow]')
            return
        table = Table(title="Security Groups")
        table.add_column("Group ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="magenta")
        table.add_column("Description", style="green")
        table.add_column("VPC ID", style="yellow")
        for group in groups:
            table.add_row(
                group.get('GroupId', ''),
                group.get('GroupName', ''),
                group.get('Description', ''),
                group.get('VpcId', '')
            )
        console.print(table)
        if debug:
            console.print(f"[debug] Security groups raw result: {groups}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


@security_groups.command()
@click.option('--name', default='spottycat-sg', help='Security group name')
@click.option('--description', default='Security group for spottycat GPU instances', help='Security group description')
@click.option('--vpc-id', default=None, help='VPC ID (optional, uses default if not specified)')
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
@click.pass_context
def create(ctx, name, description, vpc_id, as_json):
    """Create a new security group with SSH access (port 22) from your public IP."""
    console = Console()
    aws_client = ctx.obj.get('aws_client')
    debug = ctx.obj.get('debug', False)
    if not aws_client:
        console.print('[bold red]Error:[/bold red] AWS client not initialized. Check your credentials and config.')
        return
    print_budget_alerts(ctx)
    ec2 = aws_client.ec2_client
    try:
        # Detect user's public IP
        ip = requests.get('https://checkip.amazonaws.com', timeout=5).text.strip()
        # Find VPC ID if not provided
        if not vpc_id:
            vpcs = ec2.describe_vpcs().get('Vpcs', [])
            if not vpcs:
                raise RuntimeError('No VPCs found in this region.')
            vpc_id = vpcs[0]['VpcId']
        # Create the security group
        resp = ec2.create_security_group(GroupName=name, Description=description, VpcId=vpc_id)
        group_id = resp['GroupId']
        # Authorize SSH ingress from user's IP
        ec2.authorize_security_group_ingress(
            GroupId=group_id,
            IpPermissions=[{
                'IpProtocol': 'tcp',
                'FromPort': 22,
                'ToPort': 22,
                'IpRanges': [{
                    'CidrIp': f'{ip}/32',
                    'Description': 'SSH access from your IP'
                }]
            }]
        )
        group = ec2.describe_security_groups(GroupIds=[group_id])['SecurityGroups'][0]
        if as_json:
            console.print_json(json.dumps(group, default=str))
        else:
            table = Table(title="Created Security Group")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="magenta")
            for k, v in group.items():
                table.add_row(str(k), str(v))
            console.print(table)
        if debug:
            console.print(f"[debug] Created security group: {group}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


@security_groups.command()
@click.argument('group_id')
@click.pass_context
def delete(ctx, group_id):
    """Delete a security group by ID (stub)."""
    click.echo(f"[stub] Delete security group {group_id}: Not yet implemented.")


# Placeholder for security group management commands
# Will be implemented in task 4.6 