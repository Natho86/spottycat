"""
spottycat.commands.quotas - Service quota checking functionality

This module implements commands for checking AWS service quotas,
particularly for GPU instance types and availability.
"""

import click
from rich.console import Console
from rich.table import Table
import json
from . import print_budget_alerts


@click.group()
def quotas():
    """Manage and check AWS service quotas for GPU instances."""
    pass


@quotas.command()
@click.option('--instance-type', default='g4dn.xlarge', show_default=True, help='GPU instance type to check quota for (e.g., g4dn.xlarge, p3.2xlarge)')
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
@click.pass_context
def list(ctx, instance_type, as_json):
    """List AWS GPU instance quota for the given instance type."""
    console = Console()
    aws_client = ctx.obj.get('aws_client')
    debug = ctx.obj.get('debug', False)
    if not aws_client:
        console.print('[bold red]Error:[/bold red] AWS client not initialized. Check your credentials and config.')
        return
    print_budget_alerts(ctx)
    try:
        quota = aws_client.get_gpu_instance_quota(instance_type)
        result = {"instance_type": instance_type, "quota": quota}
        if as_json:
            console.print_json(json.dumps(result))
        else:
            table = Table(title=f"GPU Quota for {instance_type}")
            table.add_column("Instance Type", style="cyan", no_wrap=True)
            table.add_column("Quota", style="magenta")
            table.add_row(instance_type, str(quota))
            console.print(table)
        if debug:
            console.print(f"[debug] Quota raw result: {result}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


# Placeholder for quota-related commands
# Will be implemented in task 4.1 