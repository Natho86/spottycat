"""
spottycat.commands.keys - SSH key pair management

This module implements commands for SSH key pair management
using create_key_pair and describe_key_pairs.
"""

import click
from rich.console import Console
from rich.table import Table
import json
from . import print_budget_alerts


@click.group()
def keys():
    """Manage SSH key pairs."""
    pass


@keys.command()
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
@click.pass_context
def list(ctx, as_json):
    """List available SSH key pairs."""
    console = Console()
    aws_client = ctx.obj.get('aws_client')
    debug = ctx.obj.get('debug', False)
    if not aws_client:
        console.print('[bold red]Error:[/bold red] AWS client not initialized. Check your credentials and config.')
        return
    print_budget_alerts(ctx)
    try:
        resp = aws_client.ec2_client.describe_key_pairs()
        keys = resp.get('KeyPairs', [])
        if as_json:
            console.print_json(json.dumps(keys, default=str))
            return
        if not keys:
            console.print('[bold yellow]No SSH key pairs found.[/bold yellow]')
            return
        table = Table(title="SSH Key Pairs")
        table.add_column("Key Name", style="cyan", no_wrap=True)
        table.add_column("Fingerprint", style="magenta")
        table.add_column("Type", style="green")
        for key in keys:
            table.add_row(
                key.get('KeyName', ''),
                key.get('KeyFingerprint', ''),
                key.get('KeyType', '')
            )
        console.print(table)
        if debug:
            console.print(f"[debug] Key pairs raw result: {keys}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


@keys.command()
@click.argument('key_name')
@click.option('--key-type', type=click.Choice(['rsa', 'ed25519']), default='rsa', help='Type of key pair (rsa or ed25519)')
@click.option('--output', '-o', type=click.Path(), help='Path to save the downloaded private key')
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
@click.pass_context
def create(ctx, key_name, key_type, output, as_json):
    """Create a new SSH key pair."""
    console = Console()
    aws_client = ctx.obj.get('aws_client')
    debug = ctx.obj.get('debug', False)
    if not aws_client:
        console.print('[bold red]Error:[/bold red] AWS client not initialized. Check your credentials and config.')
        return
    print_budget_alerts(ctx)
    try:
        response = aws_client.ec2_client.create_key_pair(KeyName=key_name, KeyType=key_type)
        private_key = response.get('KeyMaterial')
        if not private_key:
            console.print('[bold red]Error:[/bold red] No private key material returned.')
            return
        # Save private key to file
        key_path = output or f"{key_name}.pem"
        with open(key_path, 'w') as f:
            f.write(private_key)
        # Set permissions to 0o400
        import os
        os.chmod(key_path, 0o400)
        if as_json:
            out = dict(response)
            out['PrivateKeyPath'] = key_path
            console.print_json(json.dumps(out, default=str))
        else:
            console.print(f"[bold green]Key pair '{key_name}' created and private key saved to {key_path}[/bold green]")
            table = Table(title="Created SSH Key Pair")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="magenta")
            for k, v in response.items():
                if k != 'KeyMaterial':
                    table.add_row(str(k), str(v))
            table.add_row('PrivateKeyPath', key_path)
            console.print(table)
        if debug:
            console.print(f"[debug] Key pair create response: {response}")
    except Exception as e:
        console.print(f"[bold red]Error creating key pair:[/bold red] {e}")


@keys.command()
@click.argument('key_name')
@click.pass_context
def delete(ctx, key_name):
    """Delete an SSH key pair by name (stub)."""
    click.echo(f"[stub] Delete SSH key pair {key_name}: Not yet implemented.")


@keys.command()
@click.argument('key_name')
@click.option('--output', '-o', type=click.Path(), help='Path to save the downloaded private key')
@click.pass_context
def download(ctx, key_name, output):
    """Download the private key for a key pair (stub)."""
    click.echo(f"[stub] Download SSH key pair {key_name} to {output or '[stdout]'}: Not yet implemented.")


# Placeholder for SSH key management commands
# Will be implemented in task 4.5 