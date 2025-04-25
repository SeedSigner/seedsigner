# Script Documentation

## Overview
This script is a developer utility tool designed to help with environment setup and validation. It provides functionality to check system requirements, validate command arguments, and manage various development processes.

## System Requirements
The script requires the following development packages to be installed on your system:

- **python3-tk**: Python 3 Tkinter interface
- **libzbar0**: Bar code reading library
- **tk**: The Tk GUI toolkit
- **tk-dev**: Tk development files
- **pkg-config**: Helper tool used when compiling applications
- **libssl-dev**: OpenSSL development libraries
- **virtualenv**: Tool to create isolated Python environments

## Usage
```
./dev_setup.sh [MODE] [ARG2] [ARG3]
```

### Arguments
- **MODE**: Specifies the operating mode (Optional)
  - Valid values: `dev`, `test`, `-`
  - Default: `dev`
- **ARG2**: virtual environment name (Optional)
  - Default in dev: `DEV_VENV`
  - Default in test: `TEST_VENV` 
- **ARG3**: python specific version (Optional)
  - Default: `python3.10`
  - fallback: `python` (system)

### Flags
- **--help, -h**: Display the full help information

## Error Handling
The script validates all input arguments and provides clear error messages for invalid inputs.

## Installation
Before running the script, ensure all required development packages are installed on your system. You can install them using your system's package manager.

For Ubuntu/Debian:
```bash
sudo apt-get install python3-tk libzbar0 tk tk-dev pkg-config libssl-dev virtualenv
```

For Red Hat/Fedora:
```bash
sudo dnf install python3-tkinter zbar tk tk-devel pkgconfig openssl-devel python3-virtualenv
```

## Troubleshooting
If you encounter errors, ensure that:
1. All system requirements are properly installed
2. The script has execution permissions (`chmod +x dev_setup.sh`)