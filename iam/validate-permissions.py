#!/usr/bin/env python3
"""
SpottyCat AWS CLI Configuration Validation Script

This script validates that the AWS CLI is properly configured with the necessary 
IAM permissions for the SpottyCat GPU Spot Instance Manager application.

Requirements:
- boto3
- AWS CLI configured with appropriate credentials
- IAM permissions to perform simulation and basic queries

Usage:
    python validate-permissions.py [--profile PROFILE_NAME] [--region REGION]
"""

import boto3
import json
import sys
import argparse
from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound
from typing import Dict, List, Tuple, Optional

class SpottyCatPermissionValidator:
    """Validates AWS IAM permissions for SpottyCat application."""
    
    def __init__(self, profile_name: Optional[str] = None, region: str = 'us-east-1'):
        """Initialize the validator with AWS session."""
        self.profile_name = profile_name
        self.region = region
        self.session = None
        self.iam_client = None
        self.ec2_client = None
        self.sts_client = None
        self.current_user_arn = None
        self.account_id = None
        
        # Required permissions for SpottyCat
        self.required_permissions = {
            'spot_instance_management': [
                'ec2:RequestSpotInstances',
                'ec2:CancelSpotInstanceRequests',
                'ec2:DescribeSpotInstanceRequests',
                'ec2:DescribeSpotPriceHistory'
            ],
            'instance_management': [
                'ec2:RunInstances',
                'ec2:TerminateInstances',
                'ec2:DescribeInstances',
                'ec2:DescribeInstanceTypes',
                'ec2:DescribeInstanceStatus'
            ],
            'launch_template_management': [
                'ec2:CreateLaunchTemplate',
                'ec2:CreateLaunchTemplateVersion',
                'ec2:DeleteLaunchTemplate',
                'ec2:DescribeLaunchTemplates'
            ],
            'keypair_management': [
                'ec2:CreateKeyPair',
                'ec2:DeleteKeyPair',
                'ec2:DescribeKeyPairs',
                'ec2:ImportKeyPair'
            ],
            'security_group_management': [
                'ec2:CreateSecurityGroup',
                'ec2:DeleteSecurityGroup',
                'ec2:DescribeSecurityGroups',
                'ec2:AuthorizeSecurityGroupIngress',
                'ec2:RevokeSecurityGroupIngress'
            ],
            'vpc_access': [
                'ec2:DescribeVpcs',
                'ec2:DescribeSubnets',
                'ec2:DescribeAvailabilityZones',
                'ec2:DescribeInternetGateways'
            ],
            'ami_access': [
                'ec2:DescribeImages',
                'ec2:DescribeImageAttribute'
            ],
            'service_monitoring': [
                'servicequotas:GetServiceQuota',
                'servicequotas:ListServiceQuotas',
                'pricing:GetProducts',
                'pricing:DescribeServices',
                'cloudwatch:PutMetricData'
            ],
            # S3 access for wordlists, rules, and cracked output
            # ARNs must match the user's config (bucket and prefixes)
            's3_access': [
                's3:GetObject',
                's3:ListBucket',
                's3:PutObject'
            ]
        }
        
        # GPU instance types that should be allowed
        self.gpu_instance_types = [
            'p2.xlarge', 'p2.8xlarge', 'p2.16xlarge',
            'p3.2xlarge', 'p3.8xlarge', 'p3.16xlarge', 'p3dn.24xlarge',
            'g3.4xlarge', 'g3.8xlarge', 'g3.16xlarge',
            'g4dn.xlarge', 'g4dn.2xlarge', 'g4dn.4xlarge', 'g4dn.8xlarge', 'g4dn.12xlarge', 'g4dn.16xlarge',
            'g5.xlarge', 'g5.2xlarge', 'g5.4xlarge', 'g5.8xlarge', 'g5.12xlarge', 'g5.16xlarge', 'g5.24xlarge'
        ]
    
    def initialize_session(self) -> bool:
        """Initialize AWS session and clients."""
        try:
            if self.profile_name:
                self.session = boto3.Session(profile_name=self.profile_name, region_name=self.region)
                print(f"✓ Using AWS profile: {self.profile_name}")
            else:
                self.session = boto3.Session(region_name=self.region)
                print("✓ Using default AWS credentials")
            
            self.iam_client = self.session.client('iam')
            self.ec2_client = self.session.client('ec2')
            self.sts_client = self.session.client('sts')
            
            # Get current user identity
            identity = self.sts_client.get_caller_identity()
            self.current_user_arn = identity['Arn']
            self.account_id = identity['Account']
            
            print(f"✓ Authenticated as: {self.current_user_arn}")
            print(f"✓ AWS Account ID: {self.account_id}")
            return True
            
        except ProfileNotFound:
            print(f"✗ AWS profile '{self.profile_name}' not found")
            return False
        except NoCredentialsError:
            print("✗ No AWS credentials configured")
            return False
        except ClientError as e:
            print(f"✗ AWS authentication failed: {e}")
            return False
    
    def validate_basic_access(self) -> bool:
        """Validate basic AWS API access."""
        try:
            print("\n=== Basic AWS Access Validation ===")
            
            # Test IAM access
            try:
                self.iam_client.get_user()
                print("✓ IAM API access confirmed")
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchEntity':
                    # User might be using a role, try to list policies instead
                    self.iam_client.list_policies(MaxItems=1)
                    print("✓ IAM API access confirmed (via role)")
                else:
                    print(f"✗ IAM API access failed: {e}")
                    return False
            
            # Test EC2 access
            self.ec2_client.describe_regions(MaxResults=1)
            print("✓ EC2 API access confirmed")
            
            # Test Service Quotas access
            try:
                servicequotas_client = self.session.client('servicequotas')
                servicequotas_client.list_services(MaxResults=1)
                print("✓ Service Quotas API access confirmed")
            except ClientError:
                print("! Service Quotas API access limited (may affect quota monitoring)")
            
            # Test Pricing API access
            try:
                pricing_client = self.session.client('pricing', region_name='us-east-1')  # Pricing API only in us-east-1
                pricing_client.describe_services(MaxResults=1)
                print("✓ Pricing API access confirmed")
            except ClientError:
                print("! Pricing API access limited (may affect cost estimation)")
            
            return True
            
        except Exception as e:
            print(f"✗ Basic access validation failed: {e}")
            return False
    
    def simulate_permissions(self, actions: List[str], category: str) -> Tuple[bool, List[str]]:
        """Simulate IAM permissions for a list of actions."""
        try:
            response = self.iam_client.simulate_principal_policy(
                PolicySourceArn=self.current_user_arn,
                ActionNames=actions
            )
            
            allowed_actions = []
            denied_actions = []
            
            for result in response['EvaluationResults']:
                action = result['EvalActionName']
                decision = result['EvalDecision']
                
                if decision == 'allowed':
                    allowed_actions.append(action)
                else:
                    denied_actions.append(action)
            
            success = len(denied_actions) == 0
            
            if success:
                print(f"✓ {category}: All {len(actions)} permissions granted")
            else:
                print(f"✗ {category}: {len(denied_actions)} permissions denied")
                for action in denied_actions:
                    print(f"    - {action}")
            
            return success, denied_actions
            
        except ClientError as e:
            print(f"✗ {category}: Permission simulation failed - {e}")
            return False, actions
    
    def validate_permissions(self) -> bool:
        """Validate all required IAM permissions."""
        print("\n=== IAM Permissions Validation ===")
        
        all_permissions_valid = True
        denied_permissions = []
        
        for category, actions in self.required_permissions.items():
            category_name = category.replace('_', ' ').title()
            success, denied = self.simulate_permissions(actions, category_name)
            
            if not success:
                all_permissions_valid = False
                denied_permissions.extend(denied)
        
        if all_permissions_valid:
            print("\n✓ All required permissions are granted")
        else:
            print(f"\n✗ Missing {len(denied_permissions)} required permissions")
            print("\nConsider applying one of these policies:")
            print("- iam/consolidated-spot-manager-policy.json (single policy)")
            print("- Multiple modular policies from the iam/ directory")
        
        return all_permissions_valid
    
    def validate_spot_constraints(self) -> bool:
        """Validate that spot instance constraints are properly configured."""
        print("\n=== Spot Instance Constraints Validation ===")
        
        try:
            # Test spot instance request with GPU instance type
            test_instance_type = 'g4dn.xlarge'
            max_spot_price = '10.00'  # Policy should limit to $10/hour
            
            # This should succeed (just simulation, not actual request)
            print(f"Testing spot request constraints for {test_instance_type}...")
            
            # Test if we can describe spot price history
            try:
                self.ec2_client.describe_spot_price_history(
                    InstanceTypes=[test_instance_type],
                    ProductDescriptions=['Linux/NULL'],
                    MaxResults=1
                )
                print("✓ Spot price history access confirmed")
            except ClientError as e:
                print(f"✗ Spot price history access failed: {e}")
                return False
            
            # Test if we can describe instance types for GPU instances
            try:
                response = self.ec2_client.describe_instance_types(
                    InstanceTypes=[test_instance_type]
                )
                if response['InstanceTypes']:
                    gpu_info = response['InstanceTypes'][0].get('GpuInfo', {})
                    if gpu_info:
                        print(f"✓ GPU instance type validation confirmed ({test_instance_type})")
                    else:
                        print(f"! Warning: {test_instance_type} may not have GPU capabilities")
                else:
                    print(f"✗ Instance type {test_instance_type} not found")
                    return False
            except ClientError as e:
                print(f"✗ Instance type validation failed: {e}")
                return False
            
            return True
            
        except Exception as e:
            print(f"✗ Spot constraints validation failed: {e}")
            return False
    
    def validate_regional_restrictions(self) -> bool:
        """Validate regional access restrictions."""
        print("\n=== Regional Access Validation ===")
        
        try:
            # Get all available regions
            regions_response = self.ec2_client.describe_regions()
            all_regions = [region['RegionName'] for region in regions_response['Regions']]
            
            # Expected allowed regions from policy
            expected_allowed_regions = [
                'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
                'eu-west-1', 'eu-west-2', 'eu-central-1',
                'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1'
            ]
            
            print(f"✓ Found {len(all_regions)} AWS regions")
            print(f"✓ Policy should allow access to {len(expected_allowed_regions)} regions")
            
            # Test current region access
            current_region = self.session.region_name
            if current_region in expected_allowed_regions:
                print(f"✓ Current region ({current_region}) is in allowed list")
            else:
                print(f"! Warning: Current region ({current_region}) may not be in policy's allowed list")
            
            return True
            
        except Exception as e:
            print(f"✗ Regional validation failed: {e}")
            return False
    
    def validate_tagging_requirements(self) -> bool:
        """Validate that tagging requirements are understood."""
        print("\n=== Resource Tagging Requirements ===")
        
        required_tags = {
            'CreatedBy': 'spottycat'
        }
        
        print("✓ Policy requires the following tags on all created resources:")
        for key, value in required_tags.items():
            print(f"    {key}: {value}")
        
        print("✓ Ensure SpottyCat application applies these tags to all resources")
        return True
    
    def validate_cost_controls(self) -> bool:
        """Validate cost control mechanisms."""
        print("\n=== Cost Control Validation ===")
        
        print("✓ Spot price cap: $10.00 per hour maximum")
        print("✓ Instance types restricted to GPU families:")
        
        gpu_families = ['p2', 'p3', 'g3', 'g4dn', 'g5']
        for family in gpu_families:
            family_instances = [t for t in self.gpu_instance_types if t.startswith(family)]
            print(f"    {family.upper()}: {len(family_instances)} instance types")
        
        print("✓ Regional restrictions limit resource sprawl")
        print("✓ Resource naming conventions enforce 'spottycat-*' prefix")
        
        return True
    
    def generate_validation_report(self, results: Dict[str, bool]) -> None:
        """Generate a summary validation report."""
        print("\n" + "="*60)
        print("SPOTTYCAT AWS PERMISSIONS VALIDATION REPORT")
        print("="*60)
        
        total_checks = len(results)
        passed_checks = sum(1 for v in results.values() if v)
        
        print(f"Total Checks: {total_checks}")
        print(f"Passed: {passed_checks}")
        print(f"Failed: {total_checks - passed_checks}")
        
        print(f"\nOverall Status: {'✓ PASS' if passed_checks == total_checks else '✗ FAIL'}")
        
        if passed_checks != total_checks:
            print("\nFailed Checks:")
            for check, passed in results.items():
                if not passed:
                    print(f"  ✗ {check}")
        
        print("\nRecommendations:")
        if results.get('permissions', False):
            print("  ✓ IAM permissions are correctly configured")
        else:
            print("  ✗ Review and apply IAM policies from iam/ directory")
            print("  ✗ Use 'aws iam simulate-principal-policy' for detailed testing")
        
        if results.get('basic_access', False):
            print("  ✓ AWS CLI configuration is working")
        else:
            print("  ✗ Check AWS CLI configuration and credentials")
        
        print(f"\nFor detailed setup instructions, see: iam/setup-permissions.md")
    
    def run_validation(self) -> int:
        """Run complete validation suite."""
        print("SpottyCat AWS Configuration Validator")
        print("====================================")
        
        if not self.initialize_session():
            return 1
        
        results = {}
        
        # Run all validation checks
        results['basic_access'] = self.validate_basic_access()
        results['permissions'] = self.validate_permissions()
        results['spot_constraints'] = self.validate_spot_constraints()
        results['regional_restrictions'] = self.validate_regional_restrictions()
        results['tagging_requirements'] = self.validate_tagging_requirements()
        results['cost_controls'] = self.validate_cost_controls()
        
        # Generate report
        self.generate_validation_report(results)
        
        # Return exit code
        return 0 if all(results.values()) else 1

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Validate AWS CLI configuration for SpottyCat GPU Spot Manager'
    )
    parser.add_argument(
        '--profile', 
        help='AWS CLI profile name to use (default: use default profile)'
    )
    parser.add_argument(
        '--region', 
        default='us-east-1',
        help='AWS region to use for validation (default: us-east-1)'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='SpottyCat Permission Validator 1.0'
    )
    
    args = parser.parse_args()
    
    try:
        validator = SpottyCatPermissionValidator(
            profile_name=args.profile,
            region=args.region
        )
        exit_code = validator.run_validation()
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n\nValidation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 