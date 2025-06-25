# SpottyCat - AWS IAM Permissions Setup Guide

This guide walks you through setting up the necessary AWS IAM permissions for the SpottyCat AWS GPU Spot Instance Manager application.

## Prerequisites

- AWS CLI installed and configured with credentials that have IAM administrative privileges
- AWS account with appropriate permissions to create and manage IAM policies and users
- Basic understanding of AWS IAM concepts

## Overview

SpottyCat requires specific AWS permissions to manage GPU spot instances, launch templates, key pairs, and security groups. This guide provides two approaches:

1. **Modular Approach**: Use separate, focused policies for granular control
2. **Consolidated Approach**: Use a single comprehensive policy for simplicity

Both approaches follow the principle of least privilege and include strict security controls.

## Policy Options

### Option 1: Modular Policies (Recommended for Production)

This approach uses separate policies for different functionality areas:

- `spot-requests-policy.json` - GPU spot instance management with type and price restrictions
- `launch-template-policy.json` - Launch template management with regional restrictions  
- `keypair-securitygroup-policy.json` - SSH key and security group management
- `spot-manager-policy.json` - General EC2, Service Quotas, and Pricing API access

### Option 2: Consolidated Policy (Recommended for Simplicity)

This approach uses a single policy file:

- `consolidated-spot-manager-policy.json` - All permissions in one policy

## Step-by-Step Setup

### Step 1: Validate Policy Documents

Before applying policies, validate them using AWS Access Analyzer:

```bash
# Validate the consolidated policy
aws accessanalyzer validate-policy \
    --policy-document file://iam/consolidated-spot-manager-policy.json \
    --policy-type IDENTITY_POLICY

# Or validate individual policies
aws accessanalyzer validate-policy \
    --policy-document file://iam/spot-requests-policy.json \
    --policy-type IDENTITY_POLICY
```

### Step 2: Create Custom Managed Policies

#### Option A: Create Consolidated Policy

```bash
# Create the consolidated SpottyCat policy
aws iam create-policy \
    --policy-name SpottyCatGPUSpotManagerPolicy \
    --policy-document file://iam/consolidated-spot-manager-policy.json \
    --description "Comprehensive policy for SpottyCat GPU spot instance management with security restrictions"
```

#### Option B: Create Modular Policies

```bash
# Create spot instance request policy
aws iam create-policy \
    --policy-name SpottyCatSpotRequestsPolicy \
    --policy-document file://iam/spot-requests-policy.json \
    --description "SpottyCat policy for GPU spot instance requests with type and price restrictions"

# Create launch template policy
aws iam create-policy \
    --policy-name SpottyCatLaunchTemplatePolicy \
    --policy-document file://iam/launch-template-policy.json \
    --description "SpottyCat policy for launch template management with regional restrictions"

# Create key pair and security group policy
aws iam create-policy \
    --policy-name SpottyCatKeyPairSecurityGroupPolicy \
    --policy-document file://iam/keypair-securitygroup-policy.json \
    --description "SpottyCat policy for SSH key pair and security group management"

# Create general EC2 and service access policy
aws iam create-policy \
    --policy-name SpottyCatGeneralAccessPolicy \
    --policy-document file://iam/spot-manager-policy.json \
    --description "SpottyCat policy for general EC2, Service Quotas, and Pricing API access"
```

### Step 3: Create Dedicated IAM User (Recommended)

Create a dedicated IAM user for SpottyCat operations:

```bash
# Create the SpottyCat user
aws iam create-user \
    --user-name spottycat-manager \
    --tags '{"Key": "Purpose", "Value": "SpottyCat-GPU-Manager"}' '{"Key": "Application", "Value": "SpottyCat"}'
```

### Step 4: Attach Policies to User

#### Option A: Attach Consolidated Policy

```bash
# Get your AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Attach the consolidated policy
aws iam attach-user-policy \
    --user-name spottycat-manager \
    --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/SpottyCatGPUSpotManagerPolicy
```

#### Option B: Attach Modular Policies

```bash
# Get your AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Attach all modular policies
aws iam attach-user-policy \
    --user-name spottycat-manager \
    --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/SpottyCatSpotRequestsPolicy

aws iam attach-user-policy \
    --user-name spottycat-manager \
    --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/SpottyCatLaunchTemplatePolicy

aws iam attach-user-policy \
    --user-name spottycat-manager \
    --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/SpottyCatKeyPairSecurityGroupPolicy

aws iam attach-user-policy \
    --user-name spottycat-manager \
    --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/SpottyCatGeneralAccessPolicy
```

### Step 5: Create Access Keys

Create programmatic access credentials for the SpottyCat user:

```bash
# Create access keys
aws iam create-access-key --user-name spottycat-manager
```

**Important**: Save the `AccessKeyId` and `SecretAccessKey` securely. The secret key is only shown once.

### Step 6: Configure AWS CLI Profile

Create a dedicated AWS CLI profile for SpottyCat:

```bash
# Configure a new profile
aws configure --profile spottycat
# Enter the Access Key ID and Secret Access Key when prompted
# Choose your preferred region (e.g., us-east-1)
# Choose output format (json recommended)
```

## Security Best Practices

### 1. Resource Tagging Requirements

All resources created by SpottyCat must include the tag `CreatedBy: spottycat` for the security policies to work correctly.

### 2. Regional Restrictions

The policies limit operations to specific AWS regions. Modify the region lists in the policy files to match your requirements:

- `us-east-1`, `us-east-2`, `us-west-1`, `us-west-2`
- `eu-west-1`, `eu-west-2`, `eu-central-1`
- `ap-southeast-1`, `ap-southeast-2`, `ap-northeast-1`

### 3. Cost Protection

- **GPU Instance Types**: Limited to P2, P3, G3, G4, and G5 families only
- **Spot Price Cap**: Maximum bid price limited to $10.00 per hour
- **Naming Conventions**: Resources must follow `spottycat-*` naming pattern

### 4. Network Security

- **SSH Access Only**: Security groups can only authorize TCP port 22 (SSH)
- **VPC Integration**: Works with existing VPCs and security groups
- **No Internet Gateway Management**: Read-only access to network components

## Verification

### Verify Policy Attachment

```bash
# List attached policies for the user
aws iam list-attached-user-policies --user-name spottycat-manager

# Verify policy details
aws iam get-policy \
    --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/SpottyCatGPUSpotManagerPolicy
```

### Test Permissions

Use the IAM policy simulator to test permissions:

```bash
# Test spot instance request permission
aws iam simulate-principal-policy \
    --policy-source-arn arn:aws:iam::${ACCOUNT_ID}:user/spottycat-manager \
    --action-names ec2:RequestSpotInstances

# Test launch template creation permission
aws iam simulate-principal-policy \
    --policy-source-arn arn:aws:iam::${ACCOUNT_ID}:user/spottycat-manager \
    --action-names ec2:CreateLaunchTemplate
```

## Troubleshooting

### Common Issues

1. **Policy Validation Errors**: Use `aws accessanalyzer validate-policy` to check for syntax issues
2. **Permission Denied**: Ensure all required policies are attached and the user has the correct ARN
3. **Resource Creation Fails**: Verify resources are tagged with `CreatedBy: spottycat`
4. **Regional Access Issues**: Check that your target region is included in the policy's region list

### Useful Commands

```bash
# List all policies attached to a user
aws iam list-user-policies --user-name spottycat-manager
aws iam list-attached-user-policies --user-name spottycat-manager

# Get detailed policy information
aws iam get-user-policy \
    --user-name spottycat-manager \
    --policy-name PolicyName

# Check user details
aws iam get-user --user-name spottycat-manager
```

## Cleanup

To remove SpottyCat IAM resources:

```bash
# Detach policies from user
aws iam detach-user-policy \
    --user-name spottycat-manager \
    --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/SpottyCatGPUSpotManagerPolicy

# Delete access keys (list them first)
aws iam list-access-keys --user-name spottycat-manager
aws iam delete-access-key \
    --user-name spottycat-manager \
    --access-key-id AKIA...

# Delete user
aws iam delete-user --user-name spottycat-manager

# Delete policies
aws iam delete-policy \
    --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/SpottyCatGPUSpotManagerPolicy
```

## Next Steps

After completing this setup:

1. Test the configuration using the validation script (`validate-permissions.py`)
2. Configure SpottyCat application with the new AWS profile
3. Review and adjust regional restrictions as needed
4. Monitor AWS costs and usage through CloudWatch and AWS Cost Explorer

## Support

For additional help:
- Review AWS IAM documentation: https://docs.aws.amazon.com/iam/
- Check AWS CLI reference: https://docs.aws.amazon.com/cli/
- Consult SpottyCat documentation for application-specific configuration 