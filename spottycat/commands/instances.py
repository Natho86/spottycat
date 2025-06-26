"""
spottycat.commands.instances - Instance monitoring and listing

This module implements commands for monitoring running instances 
and their costs.
"""

import click
from rich.console import Console
from rich.table import Table
import json
from . import print_budget_alerts


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
    print_budget_alerts(ctx)
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
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
@click.option('--by-region', is_flag=True, help='Show spend summary by region')
@click.pass_context
def cost(ctx, as_json, by_region):
    """Show cost per instance (running and, if possible, terminated), or by region."""
    console = Console()
    aws_client = ctx.obj.get('aws_client')
    debug = ctx.obj.get('debug', False)
    if not aws_client:
        console.print('[bold red]Error:[/bold red] AWS client not initialized. Check your credentials and config.')
        return
    print_budget_alerts(ctx)
    from spottycat.core.cost_calculator import CostCalculator
    import datetime
    calc = CostCalculator(aws_client)
    try:
        if by_region:
            region_spends = calc.get_region_spend()
            rows = [{'Region': region, 'Spend': spend} for region, spend in region_spends.items()]
            if as_json:
                console.print_json(json.dumps(rows, default=str))
            else:
                table = Table(title="Region Cost Summary")
                table.add_column("Region", style="cyan", no_wrap=True)
                table.add_column("Spend (USD)", style="bold")
                for row in rows:
                    table.add_row(row['Region'], f"${row['Spend']:.2f}")
                console.print(table)
            if debug:
                console.print(f"[debug] Region cost rows: {rows}")
            return
        # Gather all instances (running and terminated)
        all_instances = []
        for reservation in aws_client.describe_instances_paginated():
            for inst in reservation.get('Instances', []):
                all_instances.append(inst)
        # Get spend for running instances
        spends = calc.get_all_instance_spend()
        rows = []
        for inst in all_instances:
            instance_id = inst.get('InstanceId', '')
            instance_type = inst.get('InstanceType', '')
            state = inst.get('State', {}).get('Name', '')
            launch_time = inst.get('LaunchTime', '')
            term_time = inst.get('StateTransitionReason', '')
            spend = None
            if state == 'running':
                spend = spends.get(instance_id, None)
            else:
                # For terminated, estimate spend if launch/termination time available
                if launch_time and 'terminated' in state:
                    # If termination time is available, use it; else, skip
                    # AWS does not always provide termination time directly
                    # For now, skip terminated instance spend unless we have both times
                    pass
            rows.append({
                'InstanceId': instance_id,
                'InstanceType': instance_type,
                'State': state,
                'LaunchTime': str(launch_time),
                'Spend': spend
            })
        if as_json:
            console.print_json(json.dumps(rows, default=str))
        else:
            table = Table(title="Instance Cost Report")
            table.add_column("Instance ID", style="cyan", no_wrap=True)
            table.add_column("Type", style="magenta")
            table.add_column("State", style="green")
            table.add_column("Launch Time", style="yellow")
            table.add_column("Spend (USD)", style="bold")
            for row in rows:
                table.add_row(
                    row['InstanceId'],
                    row['InstanceType'],
                    row['State'],
                    row['LaunchTime'],
                    f"${row['Spend']:.2f}" if row['Spend'] is not None else "-"
                )
            console.print(table)
        if debug:
            console.print(f"[debug] Instance cost rows: {rows}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


# Placeholder for instance monitoring commands
# Will be implemented in task 4.3 