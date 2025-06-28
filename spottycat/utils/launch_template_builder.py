"""
spottycat.utils.launch_template_builder - Launch template configuration builder

This module implements launch template configuration builder functionality
for GPU instances with Ubuntu 22.04 AMI selection logic.
"""

from typing import Dict, Any
import base64
import json


class LaunchTemplateBuilder:
    """
    Launch template builder with Ubuntu 22.04 AMI selection logic.
    """
    
    def __init__(self, aws_client):
        """
        Initialize launch template builder.
        
        Args:
            aws_client: AWSClient instance
        """
        self.aws_client = aws_client
    
    def build_template(self, instance_type: str, **kwargs) -> Dict[str, Any]:
        """
        Build launch template configuration with Ubuntu 22.04 AMI selection logic and optional user data.
        Args:
            instance_type: EC2 instance type
            **kwargs: Additional configuration options (e.g., ami_id, architecture, user_data)
        Returns:
            Launch template configuration dictionary
        """
        import boto3
        config = kwargs.get('config')  # Ensure config is always defined
        region = kwargs.get('region', self.aws_client.region)
        architecture = kwargs.get('architecture', 'x86_64')
        ami_id = kwargs.get('ami_id')
        user_data = kwargs.get('user_data')
        ec2_client = self.aws_client.ec2_client
        # 1. Use custom AMI if provided
        if ami_id:
            selected_ami = ami_id
        else:
            # 2. Try SSM Parameter Store for official Ubuntu 22.04 AMI
            ssm = self.aws_client.session.client('ssm', region_name=region)
            ssm_param = f"/aws/service/canonical/ubuntu/server/22.04/stable/current/{architecture}/hvm/ebs-gp2/ami-id"
            try:
                resp = ssm.get_parameter(Name=ssm_param)
                selected_ami = resp['Parameter']['Value']
            except Exception:
                # 3. Fallback: Use describe_images
                filters = [
                    {'Name': 'name', 'Values': ['ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*']},
                    {'Name': 'state', 'Values': ['available']}
                ]
                images = ec2_client.describe_images(
                    Owners=['099720109477'],  # Canonical
                    Filters=filters
                )['Images']
                if not images:
                    raise RuntimeError('No Ubuntu 22.04 AMI found for this region.')
                # Sort by CreationDate descending
                images.sort(key=lambda x: x['CreationDate'], reverse=True)
                selected_ami = images[0]['ImageId']
        # Determine S3 bucket and instance profile from config
        s3_bucket = None
        instance_profile = None
        if config:
            s3_bucket_cfg = config.config_data.get('s3_bucket', {})
            s3_bucket = s3_bucket_cfg.get('name')
            instance_profile = s3_bucket_cfg.get('instance_profile')
        wordlists_prefix = "wordlists/"
        rules_prefix = "rules/"
        cracked_prefix = "cracked/"

        # IAM automation: create/check instance profile and role if not set
        if s3_bucket and not instance_profile:
            iam = self.aws_client.session.client('iam')
            profile_name = f"spottycat-s3-profile-{s3_bucket}"
            role_name = f"spottycat-s3-role-{s3_bucket}"
            assume_role_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "ec2.amazonaws.com"},
                        "Action": "sts:AssumeRole"
                    }
                ]
            }
            s3_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": ["s3:GetObject", "s3:ListBucket"],
                        "Resource": [
                            f"arn:aws:s3:::{s3_bucket}",
                            f"arn:aws:s3:::{s3_bucket}/{wordlists_prefix}*",
                            f"arn:aws:s3:::{s3_bucket}/{rules_prefix}*",
                            f"arn:aws:s3:::{s3_bucket}/{cracked_prefix}*"
                        ]
                    },
                    {
                        "Effect": "Allow",
                        "Action": ["s3:PutObject"],
                        "Resource": [
                            f"arn:aws:s3:::{s3_bucket}/{cracked_prefix}*"
                        ]
                    }
                ]
            }
            # Create or get role
            try:
                iam.get_role(RoleName=role_name)
            except iam.exceptions.NoSuchEntityException:
                iam.create_role(
                    RoleName=role_name,
                    AssumeRolePolicyDocument=json.dumps(assume_role_policy)
                )
            # Attach S3 policy
            policy_name = f"spottycat-s3-policy-{s3_bucket}"
            try:
                iam.get_policy(PolicyArn=f"arn:aws:iam::{self.aws_client.sts_client.get_caller_identity()['Account']}:policy/{policy_name}")
            except iam.exceptions.NoSuchEntityException:
                iam.create_policy(
                    PolicyName=policy_name,
                    PolicyDocument=json.dumps(s3_policy)
                )
            iam.attach_role_policy(
                RoleName=role_name,
                PolicyArn=f"arn:aws:iam::{self.aws_client.sts_client.get_caller_identity()['Account']}:policy/{policy_name}"
            )
            # Create or get instance profile
            try:
                iam.get_instance_profile(InstanceProfileName=profile_name)
            except iam.exceptions.NoSuchEntityException:
                iam.create_instance_profile(InstanceProfileName=profile_name)
            # Add role to instance profile
            try:
                iam.add_role_to_instance_profile(
                    InstanceProfileName=profile_name,
                    RoleName=role_name
                )
            except iam.exceptions.LimitExceededException:
                pass  # Already attached
            instance_profile = profile_name

        # Handle user data (custom script or built-in)
        user_data_b64 = None
        if user_data:
            if user_data.endswith('.sh') or user_data.endswith('.txt') or '\n' not in user_data:
                # Treat as file path
                try:
                    with open(user_data, 'r') as f:
                        user_data_content = f.read()
                except Exception as e:
                    raise RuntimeError(f"Failed to read user data file: {e}")
            else:
                user_data_content = user_data
            user_data_b64 = base64.b64encode(user_data_content.encode('utf-8')).decode('utf-8')
        else:
            from spottycat.utils.user_data_scripts import UserDataScriptGenerator
            gen = UserDataScriptGenerator()
            scripts = [
                gen.generate_nvidia_driver_script(),
                gen.generate_cuda_toolkit_script(),
                gen.generate_hashcat_script()
            ]
            # Add wordlist and rules sync scripts if bucket is set
            if s3_bucket:
                scripts.append(f"""
# Install AWS CLI if not present
apt-get install -y awscli

# Create mount points
mkdir -p /mnt/wordlists
mkdir -p /mnt/rules

# Sync wordlists and rules from S3 bucket
aws s3 sync s3://{s3_bucket}/{wordlists_prefix} /mnt/wordlists/
aws s3 sync s3://{s3_bucket}/{rules_prefix} /mnt/rules/
""")
                # Add decompression for wordlists and rules
                scripts.append(gen.generate_7z_decompression_script("/mnt/wordlists", cleanup=True))
                scripts.append(gen.generate_7z_decompression_script("/mnt/rules", cleanup=True))
                # Add cracked potfile sync script
                scripts.append(gen.generate_cracked_sync_script(s3_bucket, cracked_prefix))
            else:
                scripts.append(gen.generate_wordlist_sync_script())
            user_data_content = gen.combine_scripts(scripts)
            user_data_b64 = base64.b64encode(user_data_content.encode('utf-8')).decode('utf-8')
        # Determine root volume size from config or default
        root_volume_size = 100  # default
        root_volume_type = 'gp3'
        root_volume_encrypted = True
        root_volume_delete_on_termination = True
        if config:
            launch_template_cfg = config.config_data.get('launch_template', {})
            root_vol_cfg = launch_template_cfg.get('root_volume', {})
            # Fallback to top-level root_volume if not set under launch_template
            if not root_vol_cfg:
                root_vol_cfg = config.config_data.get('root_volume', {})
            root_volume_size = root_vol_cfg.get('size', root_volume_size)
            root_volume_type = root_vol_cfg.get('type', root_volume_type)
            root_volume_encrypted = root_vol_cfg.get('encrypted', root_volume_encrypted)
            root_volume_delete_on_termination = root_vol_cfg.get('delete_on_termination', root_volume_delete_on_termination)
        # Build the launch template config dict
        template = {
            'ImageId': selected_ami,
            'InstanceType': instance_type,
            'BlockDeviceMappings': [
                {
                    'DeviceName': '/dev/xvda',
                    'Ebs': {
                        'VolumeSize': root_volume_size,
                        'VolumeType': root_volume_type,
                        'Encrypted': root_volume_encrypted,
                        'DeleteOnTermination': root_volume_delete_on_termination
                    }
                }
            ],
            # Add more fields as needed (KeyName, SecurityGroupIds, etc.)
        }
        if user_data_b64:
            template['UserData'] = user_data_b64
        if instance_profile:
            template['IamInstanceProfile'] = {'Name': instance_profile}
        return template 

    def validate_template(self, template: Dict[str, Any]) -> (bool, list):
        """
        Validate the launch template configuration.
        Checks that the AMI exists and required fields are present.
        Returns:
            (is_valid, errors): Tuple of validation result and list of error messages.
        """
        errors = []
        ec2_client = self.aws_client.ec2_client
        # Check required fields
        if 'ImageId' not in template or not template['ImageId']:
            errors.append('Missing required field: ImageId (AMI)')
        if 'InstanceType' not in template or not template['InstanceType']:
            errors.append('Missing required field: InstanceType')
        # Check AMI exists
        if 'ImageId' in template and template['ImageId']:
            try:
                resp = ec2_client.describe_images(ImageIds=[template['ImageId']])
                images = resp.get('Images', [])
                if not images:
                    errors.append(f"AMI {template['ImageId']} does not exist or is not available in this region.")
            except Exception as e:
                errors.append(f"Error checking AMI: {e}")
        # Optionally, add more checks (security groups, key pairs, etc.)
        return (len(errors) == 0, errors) 