#!/usr/bin/env python
"""
Setup script for spottycat - AWS GPU Spot Instance Manager
"""

from setuptools import setup, find_packages
import os

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Read version from __init__.py
def get_version():
    import spottycat
    return spottycat.__version__

setup(
    name='spottycat',
    version=get_version(),
    description='AWS GPU Spot Instance Manager CLI',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='spottycat',
    author_email='',
    url='https://github.com/spottycat/spottycat',
    packages=find_packages(),
    python_requires='>=3.8',
    
    # Main dependencies
    install_requires=[
        # CLI Framework
        'click>=8.1.0',
        
        # AWS Integration
        'boto3>=1.26.0',
        'botocore>=1.29.0',
        
        # Configuration Management
        'PyYAML>=6.0',
        
        # Utilities
        'requests>=2.28.0',
        'tabulate>=0.9.0',  # For tabular output formatting
        'colorama>=0.4.0',  # For colored terminal output
        'python-dateutil>=2.8.0',  # For date/time handling
        
        # Validation and Parsing
        'jsonschema>=4.0.0',  # For JSON schema validation
        'packaging>=21.0',  # For version handling
    ],
    
    # Optional dependencies
    extras_require={
        'dev': [
            # Testing
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'pytest-mock>=3.8.0',
            'moto>=4.0.0',  # For mocking AWS services
            
            # Code Quality
            'black>=22.0.0',
            'flake8>=5.0.0',
            'mypy>=0.991',
            'isort>=5.10.0',
            
            # Documentation
            'sphinx>=5.0.0',
            'sphinx-rtd-theme>=1.0.0',
        ],
        'test': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'pytest-mock>=3.8.0',
            'moto>=4.0.0',
        ]
    },
    
    # Console scripts (CLI entry points)
    entry_points={
        'console_scripts': [
            'spottycat=spottycat.cli:main',
        ],
    },
    
    # Package data
    package_data={
        'spottycat': [
            'config/*.yaml',
            'config/*.yml',
        ],
    },
    
    # Include additional files in distribution
    include_package_data=True,
    
    # Classifiers
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: System :: Systems Administration',
        'Topic :: Utilities',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Environment :: Console',
    ],
    
    # Keywords
    keywords='aws ec2 spot instances gpu cli devops cloud computing',
    
    # Project URLs
    project_urls={
        'Bug Reports': 'https://github.com/spottycat/spottycat/issues',
        'Source': 'https://github.com/spottycat/spottycat',
        'Documentation': 'https://github.com/spottycat/spottycat/blob/main/README.md',
    },
    
    # License
    license='MIT',
    
    # Zip safe
    zip_safe=False,
) 