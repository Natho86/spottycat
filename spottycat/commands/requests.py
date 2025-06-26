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
@click.pass_context
def create(ctx):
    """Create a new spot instance request (stub)."""
    click.echo("[stub] Create spot request: Not yet implemented.")


@requests.command()
@click.argument('request_id')
@click.pass_context
def cancel(ctx, request_id):
    """Cancel a spot instance request by ID (stub)."""
    click.echo(f"[stub] Cancel spot request {request_id}: Not yet implemented.")


# Placeholder for spot request-related commands
# Will be implemented in task 4.2 