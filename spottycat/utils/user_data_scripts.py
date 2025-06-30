"""
spottycat.utils.user_data_scripts - User data script generation

This module implements user data script generation for instance setup,
including NVIDIA driver installation, CUDA toolkit, and hashcat installation.
"""

from typing import List, Dict, Any


class UserDataScriptGenerator:
    """
    User data script generation for instance setup.
    """
    
    def __init__(self):
        """Initialize user data script generator."""
        pass
    
    def generate_nvidia_driver_script(self) -> str:
        """
        Generate user data script for NVIDIA driver installation (Ubuntu 22.04, latest stable).
        
        Returns:
            Shell script for NVIDIA driver installation
        """
        return """#!/bin/bash
set -euxo pipefail
# Log output to /var/log/nvidia-driver-install.log
exec > >(tee -a /var/log/nvidia-driver-install.log|logger -t nvidia-driver-install) 2>&1

# Update package list and install ubuntu-drivers-common
apt-get update
apt-get install -y ubuntu-drivers-common

# Install the recommended NVIDIA driver
ubuntu-drivers autoinstall

# Optionally, reboot if a driver was installed (uncomment if desired)
# reboot
"""
    
    def generate_cuda_toolkit_script(self) -> str:
        """
        Generate user data script for CUDA toolkit installation (Ubuntu 22.04, latest version, robust method).
        Returns:
            Shell script for CUDA toolkit installation
        """
        return """#!/bin/bash
set -euxo pipefail
# Log output to /var/log/cuda-toolkit-install.log
exec > >(tee -a /var/log/cuda-toolkit-install.log|logger -t cuda-toolkit-install) 2>&1

# Add NVIDIA package repositories
apt-get update
apt-get install -y wget gnupg lsb-release
CUDA_KEY_URL="https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/3bf863cc.pub"
CUDA_KEYRING="/usr/share/keyrings/cuda-archive-keyring.gpg"
wget -O /tmp/cuda-key.pub "$CUDA_KEY_URL"
install -m 644 /tmp/cuda-key.pub "$CUDA_KEYRING"
rm /tmp/cuda-key.pub

echo "deb [signed-by=$CUDA_KEYRING] https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/ /" > /etc/apt/sources.list.d/cuda.list
apt-get update
apt-get install -y cuda-toolkit-12-3

echo 'export PATH=/usr/local/cuda/bin:$PATH' > /etc/profile.d/cuda.sh
echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> /etc/profile.d/cuda.sh
"""
    
    def generate_hashcat_script(self) -> str:
        """
        Generate user data script for hashcat installation (latest from official sources).
        Returns:
            Shell script for hashcat installation
        """
        return """#!/bin/bash
set -euxo pipefail
# Log output to /var/log/hashcat-install.log
exec > >(tee -a /var/log/hashcat-install.log|logger -t hashcat-install) 2>&1

# Install dependencies
apt-get update
apt-get install -y wget unzip ocl-icd-libopencl1

# Download and install latest hashcat release
HASHCAT_URL=$(wget -qO- https://api.github.com/repos/hashcat/hashcat/releases/latest | grep browser_download_url | grep 'hashcat-.*.7z' | cut -d '"' -f 4)
if [ -z "$HASHCAT_URL" ]; then
  echo "Could not find latest hashcat release URL" >&2
  exit 1
fi
cd /opt
wget -O hashcat-latest.7z "$HASHCAT_URL"
apt-get install -y p7zip-full
7z x hashcat-latest.7z
HASHCAT_DIR=$(find . -maxdepth 1 -type d -name 'hashcat-*' | head -n1)
ln -sf /opt/$HASHCAT_DIR/hashcat.bin /usr/local/bin/hashcat

# Optionally, verify installation
hashcat --version
"""
    
    def generate_wordlist_sync_script(self) -> str:
        """
        Generate user data script to sync wordlists from a fixed S3 bucket to /mnt/wordlists.
        Returns:
            Shell script snippet for wordlist sync (template only; not used if no bucket is set)
        """
        return """
# (Template only) S3 sync for wordlists. This should not be used if no bucket is set.
# Install AWS CLI if not present
apt-get install -y awscli

# Create mount point
mkdir -p /mnt/wordlists

# Sync wordlists from S3 (update bucket/path as needed)
aws s3 sync s3://FIXME-YOUR-BUCKET/wordlists/ /mnt/wordlists/
"""
    
    def generate_cracked_sync_script(self, bucket: str, prefix: str) -> str:
        """
        Generate a script to sync non-empty cracked potfiles to S3 every 2 minutes and on shutdown.
        Args:
            bucket: S3 bucket name
            prefix: S3 prefix/folder for cracked files
        Returns:
            Shell script snippet for cracked file sync
        """
        return f'''
# Create cracked output directory
mkdir -p /mnt/cracked

# Function to sync non-empty potfiles
sync_cracked() {{
  for file in /mnt/cracked/*; do
    [ -e "$file" ] || continue
    if [ -s "$file" ]; then
      echo "Uploading $file to s3://{bucket}/{prefix}" | tee -a /var/log/cracked-upload.log
      if ! aws s3 cp "$file" "s3://{bucket}/{prefix}" 2>>/var/log/cracked-upload.log; then
        echo "Failed to upload $file to S3" | tee -a /var/log/cracked-upload.log
      fi
    fi
  done
}}

# Periodic background sync every 2 minutes
while true; do
  sync_cracked
  sleep 60
done &

# Shutdown/termination trap
cleanup() {{
  echo "Syncing cracked files to S3 before shutdown..." | tee -a /var/log/cracked-upload.log
  sync_cracked
}}
trap cleanup EXIT
'''
    
    def generate_7z_decompression_script(self, target_dir: str, cleanup: bool = True) -> str:
        """
        Generate a script to install 7z and decompress all .7z files in the target directory.
        Args:
            target_dir: Directory containing .7z archives
            cleanup: If True, delete .7z files after extraction
        Returns:
            Shell script snippet for decompression
        """
        cleanup_cmd = f"rm -f {target_dir}/*.7z" if cleanup else ""
        return f'''
# Install 7z if not present
apt-get update
apt-get install -y p7zip-full

# Decompress all .7z files in {target_dir}
for archive in {target_dir}/*.7z; do
  [ -e "$archive" ] || continue
  echo "Decompressing $archive ..."
  7z x "$archive" -o{target_dir} || echo "Failed to decompress $archive" >&2
  {cleanup_cmd}
done
'''
    
    def combine_scripts(self, scripts: List[str]) -> str:
        """
        Combine multiple user data scripts into one.
        
        Args:
            scripts: List of shell scripts to combine
            
        Returns:
            Combined shell script
        """
        return "\n".join(scripts) 