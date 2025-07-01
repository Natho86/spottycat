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
from spottycat.utils.launch_template_builder import LaunchTemplateBuilder
import os
import datetime
import requests as pyrequests


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
@click.argument('request_id')
@click.pass_context
def cancel(ctx, request_id):
    """Cancel a spot instance request by ID (stub)."""
    click.echo(f"[stub] Cancel spot request {request_id}: Not yet implemented.")


@requests.command()
@click.option('--instance-type', required=True, help='EC2 instance type (e.g., g4dn.xlarge)')
@click.option('--max-price', type=float, help='Maximum spot price (USD/hour)')
@click.option('--key-name', help='SSH key pair name to use')
@click.option('--max-hours', type=int, help='Maximum time (in hours) to keep the instance running (1-24, default: 4)')
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
@click.pass_context
def submit(ctx, instance_type, max_price, key_name, max_hours, as_json):
    """
    Submit a spot instance request for the given instance type using the appropriate launch template (fields extracted to LaunchSpecification).
    Always uses the 'spottycat-sg' security group, creating it if needed, and adds the user's current public IP for SSH.
    Ensures the instance gets a public IP.
    """
    from spottycat.utils.launch_template_builder import LaunchTemplateBuilder
    import os
    import datetime
    console = Console()
    aws_client = ctx.obj.get('aws_client')
    config = ctx.obj.get('config')
    debug = ctx.obj.get('debug', False)
    if not aws_client:
        console.print('[bold red]Error:[/bold red] AWS client not initialized. Check your credentials and config.')
        return
    print_budget_alerts(ctx)
    try:
        # 1. Resolve key pair
        key_pairs = aws_client.ec2_client.describe_key_pairs().get('KeyPairs', [])
        resolved_key = key_name
        key_source = None
        if not resolved_key:
            if config and config.config_data.get('security', {}).get('key_pair', {}).get('name'):
                resolved_key = config.config_data['security']['key_pair']['name']
                key_source = 'config'
            else:
                spottycat_key = next((k['KeyName'] for k in key_pairs if k['KeyName'] == 'spottycat-key'), None)
                if spottycat_key:
                    resolved_key = spottycat_key
                    key_source = 'spottycat-key'
                elif len(key_pairs) == 1:
                    resolved_key = key_pairs[0].get('KeyName')
                    key_source = 'only-key'
                elif len(key_pairs) > 1:
                    console.print('[bold yellow]Multiple SSH key pairs found in your account:[/bold yellow]')
                    for k in key_pairs:
                        console.print(f"- {k.get('KeyName')}")
                    console.print('[bold red]Please specify the key to use with --key-name.[/bold red]')
                    return
        if not resolved_key:
            console.print('[bold red]No SSH key pair found. Use --key-name or create one with spottycat keys create.[/bold red]')
            return
        console.print(f"[cyan]Using SSH key pair: {resolved_key}[/cyan]")

        # 2. Ensure 'spottycat-sg' exists in the default VPC
        sg_name = 'spottycat-sg'
        try:
            vpcs = aws_client.ec2_client.describe_vpcs(Filters=[{'Name': 'isDefault', 'Values': ['true']}])['Vpcs']
            if not vpcs:
                console.print('[bold red]No default VPC found in this region.[/bold red]')
                return
            default_vpc_id = vpcs[0]['VpcId']
        except Exception as e:
            console.print(f"[bold red]Error finding default VPC:[/bold red] {e}")
            return
        # Check for existing SG
        sgs = aws_client.ec2_client.describe_security_groups(
            Filters=[{'Name': 'group-name', 'Values': [sg_name]}, {'Name': 'vpc-id', 'Values': [default_vpc_id]}]
        )['SecurityGroups']
        if sgs:
            sg_id = sgs[0]['GroupId']
            console.print(f"[green]Using security group '{sg_name}' in default VPC (ID: {sg_id})[/green]")
        else:
            # Create SG
            resp = aws_client.ec2_client.create_security_group(
                GroupName=sg_name,
                Description='SpottyCat managed security group',
                VpcId=default_vpc_id,
                TagSpecifications=[{
                    'ResourceType': 'security-group',
                    'Tags': [{'Key': 'CreatedBy', 'Value': 'spottycat'}]
                }]
            )
            sg_id = resp['GroupId']
            console.print(f"[green]Created security group '{sg_name}' in default VPC (ID: {sg_id})[/green]")
        # 3. Add user's current public IP for SSH
        try:
            user_ip = pyrequests.get('https://api.ipify.org').text
            ip_cidr = f"{user_ip}/32"
            # Check if rule already exists
            perms = aws_client.ec2_client.describe_security_groups(GroupIds=[sg_id])['SecurityGroups'][0]['IpPermissions']
            ssh_rule_exists = any(
                p.get('IpProtocol') == 'tcp' and p.get('FromPort') == 22 and p.get('ToPort') == 22 and any(r.get('CidrIp') == ip_cidr for r in p.get('IpRanges', []))
                for p in perms
            )
            if not ssh_rule_exists:
                aws_client.ec2_client.authorize_security_group_ingress(
                    GroupId=sg_id,
                    IpPermissions=[{
                        'IpProtocol': 'tcp',
                        'FromPort': 22,
                        'ToPort': 22,
                        'IpRanges': [{'CidrIp': ip_cidr}]
                    }]
                )
                console.print(f"[green]Added SSH rule for your IP ({ip_cidr}) to '{sg_name}'.[/green]")
            else:
                console.print(f"[yellow]SSH rule for your IP ({ip_cidr}) already exists in '{sg_name}'.[/yellow]")
        except Exception as e:
            console.print(f"[bold red]Error adding SSH rule for your IP: {e}[/bold red]")
            return
        # 4. Find a public subnet in the default VPC
        subnets = aws_client.ec2_client.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [default_vpc_id]}])['Subnets']
        subnet_id = None
        public_subnets = [s for s in subnets if s.get('MapPublicIpOnLaunch', False)]
        if public_subnets:
            subnet_id = public_subnets[0]['SubnetId']
        elif subnets:
            subnet_id = subnets[0]['SubnetId']
        else:
            console.print(f"[bold red]No subnets found in VPC {default_vpc_id}. Cannot submit spot request.[/bold red]")
            return
        # 5. Find or create launch template for instance type
        template_name = f"spottycat-{instance_type.replace('.', '-')}-template"
        templates = aws_client.ec2_client.describe_launch_templates(
            Filters=[{'Name': 'launch-template-name', 'Values': [template_name]}]
        ).get('LaunchTemplates', [])
        if templates:
            template_id = templates[0]['LaunchTemplateId']
            version = str(templates[0]['LatestVersionNumber'])
        else:
            builder = LaunchTemplateBuilder(aws_client)
            config_obj = ctx.obj.get('config')
            lt_config = builder.build_template(
                instance_type=instance_type,
                key_name=resolved_key,
                config=config_obj,
                region=aws_client.region,
                ami_id=None,
                user_data=None
            )
            req = {
                'LaunchTemplateName': template_name,
                'VersionDescription': 'Created by spottycat requests submit',
                'LaunchTemplateData': lt_config
            }
            resp = aws_client.ec2_client.create_launch_template(**req)
            template_id = resp['LaunchTemplate']['LaunchTemplateId']
            version = str(resp['LaunchTemplate']['LatestVersionNumber'])
            console.print(f"[green]Created launch template '{template_name}' for {instance_type}[/green]")
        # Print template info for user confirmation
        console.print(f"[bold blue]Using launch template:[/bold blue] Name: {template_name}, ID: {template_id}, Version: {version}")
        # 6. Extract fields from launch template for LaunchSpecification
        lt_version = aws_client.ec2_client.describe_launch_template_versions(
            LaunchTemplateId=template_id,
            Versions=[version]
        )['LaunchTemplateVersions'][0]['LaunchTemplateData']
        image_id = lt_version.get('ImageId')
        if not image_id:
            console.print('[bold red]AMI ID (ImageId) missing from launch template. Cannot submit spot request.[/bold red]')
            return
        # Build LaunchSpecification with NetworkInterfaces for public IP
        launch_spec = {
            'ImageId': image_id,
            'InstanceType': instance_type,
            'KeyName': resolved_key,
            'NetworkInterfaces': [{
                'DeviceIndex': 0,
                'SubnetId': subnet_id,
                'AssociatePublicIpAddress': True,
                'Groups': [sg_id]
            }],
        }
        if 'UserData' in lt_version:
            launch_spec['UserData'] = lt_version['UserData']
        if 'BlockDeviceMappings' in lt_version:
            launch_spec['BlockDeviceMappings'] = lt_version['BlockDeviceMappings']
        # 7. Prepare spot request
        spot_cfg = config.config_data.get('spot', {}) if config else {}
        max_price_val = max_price or spot_cfg.get('max_spot_price')
        instance_count = config.config_data.get('instances', {}).get('max_concurrent_instances', 1) if config else 1
        if max_hours is None:
            max_hours = 4
        if not (1 <= max_hours <= 24):
            console.print('[bold red]--max-hours must be between 1 and 24.[/bold red]')
            return
        valid_until = datetime.datetime.utcnow() + datetime.timedelta(hours=max_hours)
        req_args = {
            'InstanceCount': instance_count,
            'LaunchSpecification': launch_spec,
            'Type': 'one-time',
            'ValidUntil': valid_until.strftime('%Y-%m-%dT%H:%M:%SZ'),
        }
        if max_price_val:
            req_args['SpotPrice'] = str(max_price_val)
        # 8. Submit spot request
        try:
            response = aws_client.ec2_client.request_spot_instances(**req_args)
            requests = response.get('SpotInstanceRequests', [])
            if as_json:
                console.print_json(json.dumps(requests, default=str))
            else:
                for req in requests:
                    console.print(f"[bold green]Spot request submitted! ID: {req.get('SpotInstanceRequestId')} Status: {req.get('State')}[/bold green]")
                    if req.get('InstanceId'):
                        console.print(f"[cyan]Instance ID: {req.get('InstanceId')}[/cyan]")
                console.print(f"[yellow]This instance will be terminated at (UTC): {valid_until.strftime('%Y-%m-%d %H:%M:%S')}[/yellow]")
        except Exception as e:
            console.print(f"[bold red]Error submitting spot request:[/bold red] {e}")
        if debug:
            console.print(f"[debug] Spot request args: {req_args}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


# Placeholder for spot request-related commands
# Will be implemented in task 4.2 