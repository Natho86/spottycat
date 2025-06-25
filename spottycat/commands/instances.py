"""
spottycat.commands.instances - Instance monitoring and listing

This module implements commands for monitoring running instances 
and their costs.
"""

import click
from rich.console import Console
from rich.table import Table
import json


@click.group()
def instances():
    """Monitor and list running instances."""
    pass


@instances.command()
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
@click.pass_context
def list(ctx, as_json):
    """List running EC2 instances."""
    console = Console()
    aws_client = ctx.obj.get('aws_client')
    debug = ctx.obj.get('debug', False)
    if not aws_client:
        console.print('[bold red]Error:[/bold red] AWS client not initialized. Check your credentials and config.')
        return
    try:
        running_instances = []
        for reservation in aws_client.describe_instances_paginated():
            for inst in reservation.get('Instances', []):
                state = inst.get('State', {}).get('Name', '')
                if state == 'running':
                    running_instances.append(inst)
        if as_json:
            console.print_json(json.dumps(running_instances, default=str))
        else:
            table = Table(title="Running EC2 Instances")
            table.add_column("Instance ID", style="cyan", no_wrap=True)
            table.add_column("Type", style="magenta")
            table.add_column("State", style="green")
            table.add_column("Launch Time", style="yellow")
            found = False
            for inst in running_instances:
                found = True
                table.add_row(
                    inst.get('InstanceId', ''),
                    inst.get('InstanceType', ''),
                    inst.get('State', {}).get('Name', ''),
                    str(inst.get('LaunchTime', '')),
                )
            if found:
                console.print(table)
            else:
                console.print('[bold yellow]No running EC2 instances found.[/bold yellow]')
        if debug:
            console.print(f"[debug] Running instances raw result: {running_instances}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


@instances.command()
@click.pass_context
def cost(ctx):
    """Show cost per instance (stub)."""
    click.echo("[stub] Instance cost reporting: Not yet implemented.")


# Placeholder for instance monitoring commands
# Will be implemented in task 4.3 