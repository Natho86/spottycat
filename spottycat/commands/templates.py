"""
spottycat.commands.templates - Launch template management

This module implements commands for managing AWS launch templates
for GPU instances.
"""

import click
from rich.console import Console
from rich.table import Table
import json


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
@click.pass_context
def create(ctx):
    """Create a new launch template (stub)."""
    click.echo("[stub] Create launch template: Not yet implemented.")


@templates.command()
@click.argument('template_id')
@click.pass_context
def delete(ctx, template_id):
    """Delete a launch template by ID (stub)."""
    click.echo(f"[stub] Delete launch template {template_id}: Not yet implemented.")


# Placeholder for launch template commands
# Will be implemented in task 4.4 