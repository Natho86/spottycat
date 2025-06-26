# spottycat - AWS GPU Spot Instance Manager

A CLI tool for managing AWS GPU spot instances with cost control and automation.

## Installation

```bash
pip install spottycat
```

## Usage

```bash
spottycat --help
```

## Features

- Manage AWS GPU spot instances
- Cost tracking and budget enforcement  
- Launch template management (with Ubuntu 22.04, NVIDIA driver, CUDA, hashcat, and wordlist preload)
- SSH key pair management
- Security group configuration (with SSH access from your IP)
- Service quota checking

## Launch Templates & User Data

- By default, launch templates use the latest Ubuntu 22.04 AMI and inject a user data script that:
  - Installs the latest NVIDIA driver
  - Installs the latest CUDA toolkit
  - Installs hashcat from official sources
  - Installs AWS CLI and syncs wordlists from a fixed S3 bucket to `/mnt/wordlists` (update the bucket name in code as needed)
- The root EBS volume is set to 100GB to ensure enough space for wordlists and data.
- You can provide your own user data script with `--user-data-file` when creating a template.

## Example: Create a Launch Template

```bash
spottycat templates create --instance-type g4dn.xlarge --validate
```

## Requirements

- Python 3.8+
- AWS CLI configured with appropriate permissions
- AWS account with GPU instance quotas

## Documentation

Coming soon...

## License

MIT License 