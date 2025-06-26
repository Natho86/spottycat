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
@click.pass_context
def create(ctx):
    """Create a new security group (stub)."""
    click.echo("[stub] Create security group: Not yet implemented.")


@security_groups.command()
@click.argument('group_id')
@click.pass_context
def delete(ctx, group_id):
    """Delete a security group by ID (stub)."""
    click.echo(f"[stub] Delete security group {group_id}: Not yet implemented.")


# Placeholder for security group management commands
# Will be implemented in task 4.6 