"""
spottycat.commands - CLI command modules
 
This package contains all the CLI command implementations for spottycat.
""" 

# Utility for printing budget alerts before command output
from rich.console import Console
from spottycat.core.cost_calculator import CostCalculator

def print_budget_alerts(ctx):
    """
    Print a status line with budget alerts if any exist.
    """
    config = ctx.obj.get('config')
    aws_client = ctx.obj.get('aws_client')
    if not config or not aws_client:
        return
    max_per_instance_budget = config.config_data.get('budget', {}).get('max_per_instance_budget', 50.0)
    try:
        calc = CostCalculator(aws_client)
        alerts = calc.check_budget_alerts(max_per_instance_budget)
        if alerts:
            console = Console()
            alert_lines = []
            for alert in alerts:
                pct = int(alert['threshold'] * 100)
                alert_lines.append(f"[bold yellow]⚠️ Instance [cyan]{alert['instance_id']}[/cyan] is at {pct}% of budget (${alert['spend']:.2f})[/bold yellow]")
            console.print("\n" + "\n".join(alert_lines) + "\n")
    except Exception:
        pass  # Don't block command output if alert check fails 