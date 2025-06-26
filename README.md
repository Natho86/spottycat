# spottycat - AWS GPU Spot Instance Manager

A CLI tool for managing AWS GPU spot instances with cost control and automation.

## Installation

You can install spottycat in a virtual environment or system-wide:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -U pip
pip install -r requirements.txt
pip install .
```
Or install directly from PyPI (if available):
```bash
pip install spottycat
```

## Configuration

- Copy `config/default_config.yaml` to your working directory or `~/.spottycat/config.yaml` and edit as needed.
- You can override config values with environment variables (see config.py for mappings).
- AWS credentials must be configured (via `aws configure`, environment, or IAM role).

## Quick Start

```bash
# List GPU quotas
spottycat quotas list --instance-type g4dn.xlarge

# List spot requests
spottycat requests list

# List running instances
spottycat instances list

# Create a launch template (with built-in user data)
spottycat templates create --instance-type g4dn.xlarge --validate

# Create a launch template with custom user data
spottycat templates create --instance-type g4dn.xlarge --user-data-file my_userdata.sh --validate

# Create a security group with SSH from your IP
spottycat security-groups create
```

## Command Reference

- `quotas`: Check GPU instance quotas
- `requests`: Manage spot instance requests
- `instances`: List and monitor running instances, show cost reports
- `templates`: Manage launch templates (with Ubuntu 22.04, NVIDIA, CUDA, hashcat, wordlist preload)
- `keys`: Manage SSH key pairs
- `security-groups`: Create/manage security groups (with SSH ingress from your IP)

## Wordlist Preload

- By default, instances will sync wordlists from a fixed S3 bucket to `/mnt/wordlists` on boot.
- The root EBS volume is set to 100GB to ensure enough space.
- Update the S3 bucket name in the code as needed.

## Troubleshooting

- Ensure your AWS credentials and region are set (`aws configure` or env vars).
- Check IAM permissions for EC2, S3, Service Quotas, and Pricing APIs.
- If you see permission errors, verify your user/role has the required policies (see `iam/` directory).
- For debugging, use the `--debug` flag on any command.

## Security Notes

- SSH access is restricted to your public IP by default.
- Do not hardcode AWS credentials in user data or config files.
- Use IAM roles for EC2 for best security when running in AWS.

## License

MIT License 