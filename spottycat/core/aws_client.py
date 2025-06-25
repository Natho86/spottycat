"""
spottycat.core.aws_client - AWS service client wrapper

This module implements the AWSClient wrapper class with automatic region
detection and credential handling.
"""

import os
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from botocore.config import Config as BotoConfig

class AWSClient:
    """
    AWS service client wrapper with automatic region detection
    and credential handling. Initializes EC2, STS, and S3 clients.

    Note: This class is NOT thread-safe. For multi-threaded use, create a separate
    AWSClient instance per thread.
    """
    def __init__(self, profile=None, region=None):
        """
        Initialize AWS client wrapper.
        Args:
            profile: AWS profile name to use
            region: AWS region to use
        """
        self.profile = profile or os.environ.get('AWS_PROFILE')
        self.region = (
            region or
            os.environ.get('AWS_REGION') or
            os.environ.get('AWS_DEFAULT_REGION') or
            self._get_default_region_from_config() or
            'eu-west-2'
        )
        self.session = self._create_boto3_session()
        self._retry_config = BotoConfig(retries={'max_attempts': 5, 'mode': 'standard'})
        self.ec2_client = self.session.client('ec2', region_name=self.region, config=self._retry_config)
        self.sts_client = self.session.client('sts', region_name=self.region, config=self._retry_config)
        self.s3_client = self.session.client('s3', region_name=self.region, config=self._retry_config)
        self.service_quotas_client = self.session.client('service-quotas', region_name=self.region, config=self._retry_config)
        self.pricing_client = self.session.client('pricing', region_name='us-east-1', config=self._retry_config)  # Pricing API is only in us-east-1

    def _create_boto3_session(self):
        if self.profile:
            return boto3.Session(profile_name=self.profile, region_name=self.region)
        return boto3.Session(region_name=self.region)

    def _get_default_region_from_config(self):
        # Try to read from ~/.aws/config
        config_path = os.path.expanduser('~/.aws/config')
        if not os.path.exists(config_path):
            return None
        try:
            import configparser
            config = configparser.ConfigParser()
            config.read(config_path)
            section = f'profile {self.profile}' if self.profile else 'default'
            if section in config and 'region' in config[section]:
                return config[section]['region']
        except Exception:
            pass
        return None

    def get_current_user(self):
        """
        Return the current AWS user identity (dict with Arn, UserId, etc).
        Raises if credentials are invalid.
        """
        try:
            return self.sts_client.get_caller_identity()
        except (NoCredentialsError, ClientError) as e:
            raise RuntimeError(f"Unable to get current AWS user: {e}")

    def describe_instances(self, **kwargs):
        """
        Describe EC2 instances using optional filters/params.
        Returns the response from boto3 describe_instances.
        """
        try:
            return self.ec2_client.describe_instances(**kwargs)
        except (NoCredentialsError, ClientError) as e:
            raise RuntimeError(f"Unable to describe EC2 instances: {e}")

    def describe_spot_instance_requests(self, **kwargs):
        """
        Describe EC2 spot instance requests using optional filters/params.
        Returns the response from boto3 describe_spot_instance_requests.
        """
        try:
            return self.ec2_client.describe_spot_instance_requests(**kwargs)
        except (NoCredentialsError, ClientError) as e:
            raise RuntimeError(f"Unable to describe spot instance requests: {e}")

    def describe_instances_paginated(self, **kwargs):
        """
        Paginate through all EC2 instances using describe_instances.
        Returns a generator of reservations (same as describe_instances['Reservations']).
        """
        paginator = self.ec2_client.get_paginator('describe_instances')
        for page in paginator.paginate(**kwargs):
            for reservation in page.get('Reservations', []):
                yield reservation

    def describe_spot_instance_requests_paginated(self, **kwargs):
        """
        Paginate through all EC2 spot instance requests.
        Returns a generator of spot instance requests (same as describe_spot_instance_requests['SpotInstanceRequests']).
        """
        paginator = self.ec2_client.get_paginator('describe_spot_instance_requests')
        for page in paginator.paginate(**kwargs):
            for req in page.get('SpotInstanceRequests', []):
                yield req

    # Mapping of GPU instance families to their EC2 quota codes
    _GPU_QUOTA_CODES = {
        # These are example codes; update as needed for your use case
        'g4dn': 'L-1216C47A',  # All G4 instance types
        'p3': 'L-417A185B',    # All P3 instance types
        'p4d': 'L-DB2E81BA',   # All P4d instance types
        'g5': 'L-3819A6DF',    # All G5 instance types
        'g3': 'L-0E3CB2D2',    # All G3 instance types
        # Add more as needed
    }

    def get_gpu_instance_quota(self, instance_type):
        """
        Get the running On-Demand/Spot instance quota for a GPU instance type family.
        Args:
            instance_type: e.g. 'g4dn.xlarge', 'p3.2xlarge'
        Returns:
            Quota value (float) for the instance family in this region/account
        Raises:
            RuntimeError if quota cannot be determined
        """
        # Extract family prefix (e.g., 'g4dn' from 'g4dn.xlarge')
        family = instance_type.split('.')[0]
        quota_code = self._GPU_QUOTA_CODES.get(family)
        if not quota_code:
            raise RuntimeError(f"No quota code mapping for GPU family '{family}' (from '{instance_type}')")
        try:
            resp = self.service_quotas_client.get_service_quota(
                ServiceCode='ec2',
                QuotaCode=quota_code
            )
            return resp['Quota']['Value']
        except (NoCredentialsError, ClientError) as e:
            raise RuntimeError(f"Unable to fetch GPU quota for {instance_type}: {e}")

    def get_spot_price(self, instance_type, region=None):
        """
        Get the latest spot price for a given instance type in the specified region.
        Args:
            instance_type: e.g. 'g4dn.xlarge'
            region: AWS region code (defaults to self.region)
        Returns:
            Price per hour (float) or raises RuntimeError
        """
        region = region or self.region
        try:
            # The Pricing API uses region names, not codes
            region_name_map = {
                'us-east-1': 'US East (N. Virginia)',
                'us-west-2': 'US West (Oregon)',
                'us-west-1': 'US West (N. California)',
                'eu-west-1': 'EU (Ireland)',
                'eu-central-1': 'EU (Frankfurt)',
                # Add more as needed
            }
            aws_region_name = region_name_map.get(region, region)
            resp = self.pricing_client.get_products(
                ServiceCode='AmazonEC2',
                Filters=[
                    {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                    {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': aws_region_name},
                    {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw', 'Value': 'NA'},
                    {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': 'Linux'},
                    {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': 'Shared'},
                    {'Type': 'TERM_MATCH', 'Field': 'capacitystatus', 'Value': 'Used'},
                    {'Type': 'TERM_MATCH', 'Field': 'marketoption', 'Value': 'Spot'},
                ],
                MaxResults=1
            )
            products = resp.get('PriceList', [])
            if not products:
                raise RuntimeError(f"No spot price found for {instance_type} in {region}")
            import json
            price_item = json.loads(products[0])
            # Navigate the JSON to find the price per hour
            for term in price_item['terms']['OnDemand'].values():
                for price_dim in term['priceDimensions'].values():
                    return float(price_dim['pricePerUnit']['USD'])
            for term in price_item['terms']['Spot'].values():
                for price_dim in term['priceDimensions'].values():
                    return float(price_dim['pricePerUnit']['USD'])
            raise RuntimeError(f"Could not parse spot price for {instance_type} in {region}")
        except (NoCredentialsError, ClientError, KeyError, ValueError) as e:
            raise RuntimeError(f"Unable to fetch spot price for {instance_type} in {region}: {e}")

    # Placeholder for AWS client implementation
    # Will be implemented in task 3.1 