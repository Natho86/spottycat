"""
spottycat.core.cost_calculator - Cost tracking and budget enforcement

This module implements cost tracking and budget management functionality
using AWS Pricing API for real-time cost calculations.
"""


class CostCalculator:
    """
    Cost calculator class using AWS Pricing API for real-time spot pricing.
    """
    
    def __init__(self, aws_client):
        """
        Initialize cost calculator.
        
        Args:
            aws_client: AWSClient instance
        """
        self.aws_client = aws_client
    
    # Placeholder for cost calculation implementation
    # Will be implemented in task 5.1 

    def estimate_spot_request_cost(self, instance_type, region=None, availability_zone=None):
        """
        Estimate the current spot price for a given instance type in the specified region/AZ.

        Args:
            instance_type (str): EC2 instance type (e.g., 'g4dn.xlarge')
            region (str, optional): AWS region code (e.g., 'us-east-1'). Defaults to AWSClient's region.
            availability_zone (str, optional): Specific AZ (e.g., 'us-east-1a'). If not provided, uses all AZs in region.
        Returns:
            float: Latest spot price per hour for the instance type.
        Raises:
            RuntimeError: If no spot price data is found or AWS API fails.
        """
        ec2_client = self.aws_client.ec2_client
        region = region or self.aws_client.region
        filters = {
            'InstanceTypes': [instance_type],
            'ProductDescriptions': ['Linux/UNIX'],
            'MaxResults': 1,
        }
        if availability_zone:
            filters['AvailabilityZone'] = availability_zone
        try:
            response = ec2_client.describe_spot_price_history(**filters)
            history = response.get('SpotPriceHistory', [])
            if not history:
                raise RuntimeError(f"No spot price history found for {instance_type} in {region}{'/' + availability_zone if availability_zone else ''}")
            # Return the most recent price as float
            return float(history[0]['SpotPrice'])
        except Exception as e:
            raise RuntimeError(f"Failed to estimate spot price for {instance_type} in {region}: {e}") 

    def estimate_spot_request_total_cost(self, instance_type, hours, region=None, availability_zone=None):
        """
        Estimate the total cost for a spot request before submission.
        Args:
            instance_type (str): EC2 instance type (e.g., 'g4dn.xlarge')
            hours (float): Expected duration in hours
            region (str, optional): AWS region code
            availability_zone (str, optional): Specific AZ
        Returns:
            float: Estimated total cost in USD
        Raises:
            RuntimeError: If spot price cannot be determined
        """
        price = self.estimate_spot_request_cost(instance_type, region=region, availability_zone=availability_zone)
        return round(price * hours, 4)

    def get_instance_spend(self, instance_id):
        """
        Calculate the cumulative spend for a given running spot instance.
        Args:
            instance_id (str): The EC2 instance ID.
        Returns:
            float: The estimated spend in USD.
        Raises:
            RuntimeError: If instance or price data is missing.
        """
        import datetime
        # Find the instance details
        reservations = self.aws_client.describe_instances(
            InstanceIds=[instance_id]
        ).get('Reservations', [])
        for reservation in reservations:
            for instance in reservation.get('Instances', []):
                if instance.get('InstanceId') == instance_id:
                    launch_time = instance['LaunchTime']
                    instance_type = instance['InstanceType']
                    az = instance['Placement']['AvailabilityZone']
                    # Get spot price at launch (fallback to current)
                    try:
                        price = self.estimate_spot_request_cost(instance_type, region=self.aws_client.region, availability_zone=az)
                    except Exception:
                        price = 0.0
                    now = datetime.datetime.utcnow().replace(tzinfo=launch_time.tzinfo)
                    hours = (now - launch_time).total_seconds() / 3600.0
                    return round(hours * price, 4)
        raise RuntimeError(f"Instance {instance_id} not found or missing data.")

    def get_all_instance_spend(self):
        """
        Get cumulative spend for all running spot instances.
        Returns:
            dict: Mapping of instance_id to spend (USD).
        """
        import datetime
        spends = {}
        reservations = self.aws_client.describe_instances(
            Filters=[{'Name': 'instance-lifecycle', 'Values': ['spot']}, {'Name': 'instance-state-name', 'Values': ['running']}]
        ).get('Reservations', [])
        for reservation in reservations:
            for instance in reservation.get('Instances', []):
                instance_id = instance['InstanceId']
                launch_time = instance['LaunchTime']
                instance_type = instance['InstanceType']
                az = instance['Placement']['AvailabilityZone']
                try:
                    price = self.estimate_spot_request_cost(instance_type, region=self.aws_client.region, availability_zone=az)
                except Exception:
                    price = 0.0
                now = datetime.datetime.utcnow().replace(tzinfo=launch_time.tzinfo)
                hours = (now - launch_time).total_seconds() / 3600.0
                spends[instance_id] = round(hours * price, 4)
        return spends

    def is_over_budget(self, instance_id, max_budget):
        """
        Check if the instance spend exceeds the given budget.
        Args:
            instance_id (str): The EC2 instance ID.
            max_budget (float): The max allowed spend in USD.
        Returns:
            bool: True if spend exceeds budget, else False.
        """
        spend = self.get_instance_spend(instance_id)
        return spend > max_budget 

    def terminate_instance(self, instance_id):
        """
        Terminate the given EC2 instance using AWSClient's ec2_client.
        Args:
            instance_id (str): The EC2 instance ID to terminate.
        Raises:
            RuntimeError: If termination fails.
        """
        try:
            self.aws_client.ec2_client.terminate_instances(InstanceIds=[instance_id])
        except Exception as e:
            raise RuntimeError(f"Failed to terminate instance {instance_id}: {e}")

    def enforce_instance_budgets(self, max_budget, threshold=1.0):
        """
        Check all running spot instances and terminate those over (or at) the budget threshold.
        Args:
            max_budget (float): The max allowed spend in USD per instance.
            threshold (float): Fraction of budget at which to terminate (default 1.0 = 100%).
        Returns:
            list: List of terminated instance IDs.
        """
        terminated = []
        spends = self.get_all_instance_spend()
        for instance_id, spend in spends.items():
            if spend >= max_budget * threshold:
                self.terminate_instance(instance_id)
                terminated.append(instance_id)
        return terminated 

    def check_budget_alerts(self, max_budget, thresholds=(0.75, 0.9)):
        """
        Check all running spot instances and return alerts for those crossing budget thresholds.
        Args:
            max_budget (float): The max allowed spend in USD per instance.
            thresholds (tuple): Budget thresholds as fractions (default: (0.75, 0.9)).
        Returns:
            list: List of alert dicts: {'instance_id', 'spend', 'threshold'}
        """
        alerts = []
        spends = self.get_all_instance_spend()
        for instance_id, spend in spends.items():
            for threshold in sorted(thresholds):
                if spend >= max_budget * threshold:
                    alerts.append({
                        'instance_id': instance_id,
                        'spend': spend,
                        'threshold': threshold
                    })
        return alerts 

    def get_region_spend(self):
        """
        Get cumulative spend for all running spot instances, grouped by region.
        Returns:
            dict: Mapping of region code (e.g., 'us-east-1') to total spend (USD).
        """
        import re
        spends = {}
        reservations = self.aws_client.describe_instances(
            Filters=[{'Name': 'instance-lifecycle', 'Values': ['spot']}, {'Name': 'instance-state-name', 'Values': ['running']}]
        ).get('Reservations', [])
        for reservation in reservations:
            for instance in reservation.get('Instances', []):
                az = instance['Placement']['AvailabilityZone']
                # Region is AZ minus last character
                region = re.sub(r'[a-z]$', '', az)
                launch_time = instance['LaunchTime']
                instance_type = instance['InstanceType']
                try:
                    price = self.estimate_spot_request_cost(instance_type, region=region, availability_zone=az)
                except Exception:
                    price = 0.0
                import datetime
                now = datetime.datetime.utcnow().replace(tzinfo=launch_time.tzinfo)
                hours = (now - launch_time).total_seconds() / 3600.0
                spend = round(hours * price, 4)
                spends[region] = spends.get(region, 0.0) + spend
        return spends 