# Task List: spottycat - AWS GPU Spot Instance Manager

## Relevant Files

- `spottycat/cli.py` - Main CLI entry point and command routing
- `spottycat/commands/quotas.py` - Service quota checking functionality
- `spottycat/commands/requests.py` - Spot request management commands
- `spottycat/commands/instances.py` - Instance monitoring and listing
- `spottycat/commands/templates.py` - Launch template management
- `spottycat/commands/keys.py` - SSH key pair management
- `spottycat/commands/security_groups.py` - Security group configuration
- `spottycat/core/aws_client.py` - AWS service client wrapper
- `spottycat/core/cost_calculator.py` - Cost tracking and budget enforcement
- `spottycat/core/config.py` - Configuration management
- `spottycat/utils/launch_template_builder.py` - Launch template configuration builder
- `spottycat/utils/user_data_scripts.py` - User data script generation for instance setup
- `setup.py` - Package setup and dependencies with boto3, click, pyyaml, and testing frameworks
- `requirements.txt` - Python dependencies with pinned versions for reproducible builds
- `requirements-dev.txt` - Development and testing dependencies with pinned versions
- `requirements-test.txt` - Testing-only dependencies with pinned versions
- `README.md` - Basic project documentation
- `config/default_config.yaml` - Comprehensive default configuration template with AWS, budget, instance, security, and monitoring settings
- `config/example_config.yaml` - Example customized configuration showing common use cases
- `iam/spot-manager-policy.json` - Custom IAM policy for required permissions
- `iam/spot-requests-policy.json` - Focused IAM policy for spot instance management with GPU type and price restrictions  
- `iam/launch-template-policy.json` - Focused IAM policy for launch template management with regional restrictions
- `iam/keypair-securitygroup-policy.json` - Focused IAM policy for SSH key and security group management
- `iam/consolidated-spot-manager-policy.json` - Single comprehensive spottycat policy combining all focused policies
- `iam/setup-permissions.md` - Guide for setting up AWS permissions
- `pytest.ini` - Pytest configuration with markers, coverage, and test discovery settings
- `Makefile` - Development and testing automation with targets for testing, linting, and setup
- `tests/__init__.py` - Test package initialization
- `tests/conftest.py` - Shared pytest fixtures for AWS mocking, CLI testing, and configuration
- `tests/unit/__init__.py` - Unit test package initialization  
- `tests/unit/test_cli.py` - Unit tests for CLI functionality with pytest markers and fixtures
- `tests/unit/test_cost_calculator.py` - Unit tests for cost calculation logic with mock AWS services
- `tests/unit/test_aws_client.py` - Unit tests for AWS client wrapper with comprehensive mocking
- `tests/integration/__init__.py` - Integration test package initialization
- `tests/integration/test_config_integration.py` - Integration tests for configuration management
- `tests/data/sample_spot_requests.json` - Test data fixtures for spot instance requests
- `README.md` - Installation and usage documentation

### Notes

- This is a Python CLI application that requires AWS CLI to be installed and configured
- Unit tests use pytest framework
- The application requires specific AWS IAM permissions to function properly
- Configuration supports both YAML files and environment variables

## Tasks

- [x] 1.0 Setup AWS IAM Permissions and Policies
  - [x] 1.1 Create custom IAM policy JSON file with required EC2, Service Quotas, and Pricing API permissions
  - [x] 1.2 Create IAM policy for spot instance requests including `ec2:RequestSpotInstances`, `ec2:CancelSpotInstanceRequests`, `ec2:DescribeSpotInstanceRequests`
  - [x] 1.3 Create IAM policy for launch template management with `ec2:CreateLaunchTemplate`, `ec2:ModifyLaunchTemplate`, `ec2:DescribeLaunchTemplates`
  - [x] 1.4 Create IAM policy for key pair and security group management
  - [x] 1.5 Create consolidated policy document combining all required permissions
  - [x] 1.6 Create setup guide for applying IAM policies to AWS user accounts
  - [x] 1.7 Create AWS CLI configuration validation script to verify permissions

- [ ] 2.0 Initialize Project Structure and Core Infrastructure
  - [x] 2.1 Create Python package structure with `spottycat` main package
  - [x] 2.2 Setup `setup.py` with boto3, click, pyyaml, and other dependencies
  - [x] 2.3 Create requirements.txt with pinned versions
  - [x] 2.4 Initialize `__init__.py` files for all package modules
  - [x] 2.5 Create default configuration YAML template with region, budget, and instance preferences
  - [x] 2.6 Setup pytest configuration and test directory structure
  - [x] 2.7 Create base CLI entry point using Click framework

- [x] 3.0 Implement AWS Service Integration Layer
  - [x] 3.1 Create `AWSClient` wrapper class with automatic region detection and credential handling
  - [x] 3.2 Implement EC2 service client with methods for `describe_instances`, `describe_spot_instance_requests`
  - [x] 3.3 Implement Service Quotas client integration for GPU instance quota checking
  - [x] 3.4 Create AWS Pricing API client for real-time cost calculations
  - [x] 3.5 Add error handling and retry logic for AWS API calls using botocore exceptions
  - [x] 3.6 Implement AWS resource pagination handling for large result sets
  - [x] 3.7 Create session management for thread-safe AWS operations

- [ ] 4.0 Develop CLI Commands and User Interface
  - [x] 4.1 Implement `quotas` command group with subcommands for listing GPU instance quotas and availability
  - [x] 4.2 Implement `requests` command group for creating, listing, and canceling spot requests
  - [x] 4.3 Implement `instances` command group for monitoring running instances and their costs
  - [x] 4.4 Implement `templates` command group for managing launch templates
  - [x] 4.5 Implement `keys` command group for SSH key pair management using `create_key_pair` and `describe_key_pairs`
  - [x] 4.6 Implement `security-groups` command group for security group creation and management
  - [x] 4.7 Add tabular output formatting using Click's table utilities
  - [x] 4.8 Add JSON output option for programmatic use
  - [x] 4.9 Implement verbose logging and debugging options

- [x] 5.0 Implement Cost Tracking and Budget Management
  - [x] 5.1 Create cost calculator class using AWS Pricing API for real-time spot pricing
  - [x] 5.2 Implement budget tracking system that monitors cumulative spend per instance
  - [x] 5.3 Create automatic instance termination logic when approaching budget limits
  - [x] 5.4 Implement cost estimation for spot requests before submission
  - [x] 5.5 Add cost alerting system that warns users at 75% and 90% of budget
  - [x] 5.6 Create cost reporting functionality showing spend history and projections
  - [x] 5.7 Implement per-region cost tracking for multi-region deployments

- [x] 6.0 Create Launch Template and Instance Configuration System
  - [x] 6.1 Create launch template builder with Ubuntu 22.04 AMI selection logic
  - [x] 6.2 Generate user data scripts for NVIDIA driver installation (latest stable version)
  - [x] 6.3 Generate user data scripts for CUDA toolkit installation
  - [x] 6.4 Generate user data scripts for hashcat installation from official sources
  - [x] 6.5 Implement security group creation with SSH access (port 22) from user's IP
  - [x] 6.6 Create launch template versioning system for different GPU instance types
  - [x] 6.7 Add support for custom user data script injection
  - [x] 6.8 Implement launch template validation before spot request submission

- [x] 7.0 Add Testing, Documentation, and Deployment
  - [x] 7.1 Create unit tests for AWS client wrapper with mocked boto3 responses
  - [x] 7.2 Create unit tests for cost calculation logic with various pricing scenarios
  - [x] 7.3 Create integration tests for CLI commands (excluding AWS API calls)
  - [x] 7.4 Add mock AWS response fixtures for consistent testing
  - [x] 7.5 Create comprehensive README with installation, configuration, and usage examples
  - [~] 7.6 Add troubleshooting guide for common AWS permission and configuration issues
  - [~] 7.7 Create example configuration files for different use cases
  - [~] 7.8 Setup automated testing pipeline using GitHub Actions or similar CI/CD
  - [~] 7.9 Create release packaging and distribution setup for PyPI 
