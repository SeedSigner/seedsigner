# !/bin/bash

# ==================== HELP FUNCTIONS ====================
color() {
    word=$1
    color=$2

    if [ "$color" == "g" ]; then
        echo -e "\e[32m$word\e[0m" # Passes [green]
    elif [ "$color" == "r" ]; then
        echo -e "\e[31m$word\e[0m" # error [red]
    elif [ "$color" == "y" ]; then
        echo -e "\e[33m$word\e[0m" # warning [yellow]
    else
        echo "$word"
    fi
}

# Brief usage function - shows just the command syntax
show_usage() {
    local script_name="$(basename "$1")"
    echo "Usage: $script_name [MODE] [VENV_NAME] [PYTHON_PATH]"
    echo "Try '$script_name --help' for more information."
}

# Full help function - comprehensive documentation
show_full_help() {
    local script_name="$(basename "$1")"

    echo "SeedSigner Development Environment Setup Script"
    echo "==============================================="
    echo
    echo "USAGE:"
    echo "  $script_name [MODE] [VENV_NAME] [PYTHON_PATH]"
    echo "  $script_name --help"
    echo
    echo "PARAMETERS:"
    echo "  MODE        Optional. Can be 'dev' (default), 'test', or '-' (same as 'dev')"
    echo "              - dev: Sets up environment for development with emulator"
    echo "              - test: Sets up environment for running tests"
    echo
    echo "  VENV_NAME   Optional. Name for the virtual environment."
    echo "              If omitted, uses the mode name (DEV_VENV or TEST_VENV)"
    echo
    echo "  PYTHON_PATH Optional. Path or command for specific Python version."
    echo "              Example: python3.10"
    echo "              If omitted, uses the system default Python"
    echo
    echo "EXAMPLES:"
    echo "  $script_name                   # Setup dev environment with default settings"
    echo "  $script_name dev my_venv       # Setup dev environment with custom venv name"
    echo "  $script_name test - python3.10 # Setup test environment with Python 3.10"
    echo
    echo "WHAT THIS SCRIPT DOES:"
    echo "  1. Checks your environment meets the requirements"
    echo "  2. Creates a virtual environment"
    echo "  3. Installs required packages"
    echo "  4. For dev mode: Sets up the SeedSigner emulator"
    echo "  5. Opens a new terminal in the appropriate directory"
    echo
}

# Function to validate arguments and show appropriate messages
validate_args() {
    local script_path="$1"
    local arg1="$2"
    local arg2="$3"
    local arg3="$4"

    # Check for help flag
    if [[ "$arg1" == "--help" || "$arg1" == "-h" ]]; then
        show_full_help "$script_path"
        exit 0
    fi

    # Check for too many arguments
    if [ -n "$5" ]; then
        echo -e "$(color "Error" "r") Too many arguments provided. Maximum is 3 arguments."
        show_usage "$script_path"
        exit 1
    fi

    if [ -n "$arg1" ] && [ "$arg1" != "-" ] && [ "$arg1" != "dev" ] && [ "$arg1" != "test" ]; then
        echo -e "$(color "Error" "r") Invalid MODE '$arg1'. Must be 'dev', 'test', or '-'."
        show_usage "$script_path"
        exit 1
    fi

    # Return success
    return 0
}

# Function to check Python version and warn if not 3.10
check_python_version() {
    local python_cmd=$1
    local version_info=$($python_cmd --version 2>&1)
    local version_num=$(echo $version_info | grep -o '(?<=Python )\d+\.\d+\.\d+')
    local major_minor=$(echo $version_num | cut -d. -f1,2)

    if [[ "$major_minor" != "3.10" ]]; then
        echo -e "$(color "[WARNING]" "y") Python $version_num detected. SeedSigner recommends Python 3.10.x"

        # Show installation instructions if checking system Python
        if [ "$2" = "system" ]; then
            echo -e "\nYou can install Python 3.10 with the following commands:"
            echo -e "  sudo apt update"
            echo -e "  sudo apt install python3.10 python3.10-venv python3.10-dev"
        fi

        read -p "$(color "Do you want to continue with Python $version_num anyway? [y/N]: " "y")" continue_anyway
        if [[ ! "$continue_anyway" =~ ^[Yy]$ ]]; then
            echo "Exiting."
            exit 1
        fi
    else
        echo -e "$(color "[INFO]" "g") Python 3.10 at $PYTHON310_PATH (recommended by SeedSigner)"
    fi
}

# Function to check for Python 3.10 and fall back to system Python if needed
find_python() {
    # Try to find Python 3.10
    PYTHON310_PATH=$(which python3.10 2>/dev/null)
    if [ -n "$PYTHON310_PATH" ]; then
        echo -e "$(color "[INFO]" "g") Found Python 3.10 at $PYTHON310_PATH (recommended by SeedSigner)"
        PYTHON_CMD="python3.10"
    else
        # Fall back to system Python
        echo -e "$(color "[WARNING]" "y") Using default system $(python --version)"
        check_python_version "python" "system"
    fi
}

# ==================== END OF HELP FUNCTIONS ====================

# Validate arguments
validate_args "$0" "$@"

# === WARNING: Script Assumptions ===
echo -e "$(color "[Warning]" "y") This script assumes the following:"
echo -e " - You are NOT running inside a virtual environment"
echo -e " - You are inside the (official/fork) '*/seedsigner.git' Git repository"
echo -e " - Recommended by SeedSigner: You have Python 3.10.x installed"
echo

read -p $"continue? [y/N]: " continue

if [[ ! "$continue" =~ ^[Yy]$ ]]; then
    echo "Exiting. Please install the list packages."
    exit 1
fi

# v0.1.0
# Check that there are no active environments
if [ -n "$VIRTUAL_ENV" ]; then
    echo 'Please run without an active VENV (run: deactivate).'
    exit 1
fi

# Check that you are in the correct repository (or fork repository)
REPO_URL=$(sh -c "git config --get remote.origin.url | tr '[:upper:]' '[:lower:]'")

# Use regex to match both the original repo and forks
if [[ ! $REPO_URL =~ github\.com.*/seedsigner(\.git)?$ ]]; then
    echo -e "$(color "[ERROR]" "r") This script must be run within the SeedSigner repository or a fork."
    echo "Current repository: $REPO_URL"
    echo "Expected repository pattern: github.com/*/seedsigner.git"
    exit 1
fi

# If it's a fork, inform the user
if [[ $REPO_URL != "https://github.com/seedsigner/seedsigner.git" ]]; then
    echo -e "$(color "[INFO]" "y") Running in a forked repository: $REPO_URL"
fi

### SCRIPT PARAMETERS

# Check if the first argument is passed or omitted (dev/test/"-"/None allowed)
if [ -z "$1" ] || [ "$1" = "-" ] || [ "$1" = "dev" ]; then
    echo "VENV Mode: dev"
    VENV_MODE="DEV_VENV"
elif
    [ "$1" = "test" ]
then

    if uname -a | grep -qE 'aarch64|raspberry'; then
        echo "Tests are not for ARM or Raspberry Pi!"
        exit 1
    fi
    echo "VENV Mode: test"
    VENV_MODE="TEST_VENV"
fi

# Check if the second argument is passed or omitted (any/"-"/None)
if [ -z "$2" ] || [ "$2" = "-" ]; then
    echo "Assuming venv directory = chosen venv mode"
    VENV_NAME=$VENV_MODE
else
    VENV_NAME=$2
fi

# Python version handling
PYTHON_CMD="python"

# Check if there is a third parameter or it is omitted (pythonN.M/"-"/None)
if [ -z "$3" ] || [ "$3" = "-" ]; then
    # No specific Python version provided - use automatic detection
    find_python
else
    # User specified a Python version
    PYTHON_PATH=$(which $3 2>/dev/null)
    if [ -n "$PYTHON_PATH" ]; then
        # Use the specified Python version
        PYTHON_CMD=$3
        check_python_version "$PYTHON_CMD" "specified"
    else
        echo "Python $3 not found in your PATH. Falling back to automatic detection."
        # Fall back to automatic detection
        find_python
    fi
fi

### NECESSARY DEPENDENCIES (Section under review/debug)


# Rebuild the virtual environment activation path
# Setting actual directory to /src or /tests on repo
REPO_PATH=$(sh -c 'git rev-parse --show-toplevel')

if [ "$VENV_MODE" = "DEV_VENV" ]; then
    # DEV Mode
    ABSOLUTE_VENV_DEST_PATH=$(cd "$REPO_PATH" && pwd)/src
else
    # TEST Mode
    ABSOLUTE_VENV_DEST_PATH=$(cd "$REPO_PATH" && pwd)/tests
fi

echo $ABSOLUTE_VENV_DEST_PATH
cd "$ABSOLUTE_VENV_DEST_PATH"

VENV_ACTIVATE="$VENV_NAME/bin/activate"
VENV_ACTIVATE_PATH=$(pwd)/$VENV_ACTIVATE
echo
# echo $VENV_ACTIVATE
# echo $VENV_ACTIVATE_PATH

# Create VENV

if [ -f $VENV_ACTIVATE_PATH ]; then # check if the venv already exists to avoid overwriting
    echo "$(color "Error" r) Venv '$VENV_ACTIVATE_PATH' $(color 'already exists' 'y'). Delete or define another name."
    exit 1
fi

echo "Creating venv (with $PYTHON_CMD -m venv) '$VENV_NAME'..."
$PYTHON_CMD -m venv $VENV_NAME        # first alternative
if [ ! -f $VENV_ACTIVATE_PATH ]; then # If the venv was not generated, try with 'virtualenv' command

    echo "Creating venv (with virtualenv) '$VENV_NAME'..."
    virtualenv -p $PYTHON_CMD $VENV_NAME
    if [ ! -f $VENV_ACTIVATE_PATH ]; then

        echo "Could not create venv '$VENV_NAME'..."
        exit 1
    fi
fi
echo

### Installation of necessary packages according to the CHOSEN MODE

if [ "$VENV_MODE" = "DEV_VENV" ]; then
    # DEV Mode

    # Installation of necessary packagess
    echo "Installing necessary packages ..."

    # Installing EMULATOR
    echo "Cloning seedsigner-emulator repo ..."
    DEFAULT_EMULATOR="https://github.com/enteropositivo/seedsigner-emulator"
    read -p "provide your fork (default: ${DEFAULT_EMULATOR}):" REPO_URL

    if [ "$REPO_URL" == "" ]; then
        REPO_URL=$DEFAULT_EMULATOR # default emulator
        echo "Using default: ${REPO_URL}"
    fi

    if [[ ! "$REPO_URL" =~ https://github\.com/.+/seedsigner-emulator$ ]]; then
        echo "Please ensure you forked 'seedsigner-emulator'"
        exit 1
    fi

    #git clone http://github.com/enteropositivo/seedsigner-emulator.git
    echo "git clone $REPO_URL"
    git clone ${REPO_URL}
    rsync -a seedsigner-emulator/seedsigner/emulator ./seedsigner
    rsync -a seedsigner-emulator/seedsigner/resources ./seedsigner
    echo

    # Check if the file seedsigner-emulator/requirements.txt exists
    if [ -f "seedsigner-emulator/requirements.txt" ]; then
        bash -c "source $VENV_ACTIVATE && echo 'Virtual environment activated at: "$VENV_ACTIVATE_PATH"' && echo && python3 -m pip install --upgrade pip --require-virtualenv && python3 -m pip install --upgrade Pillow --require-virtualenv && python3 -m pip install --upgrade setuptools --require-virtualenv && pip3 install -r seedsigner-emulator/requirements.txt --require-virtualenv && echo 'Packages have been successfully installed in the virtual environment from requirements.txt' && deactivate"
    else
        bash -c "source $VENV_ACTIVATE && echo 'Virtual environment activated at: "$VENV_ACTIVATE_PATH"' && echo && python3 -m pip install --upgrade pip --require-virtualenv && python3 -m pip install --upgrade Pillow --require-virtualenv && python3 -m pip install --upgrade setuptools --require-virtualenv && pip3 install git+https://github.com/jreesun/urtypes.git@e0d0db277ec2339650343eaf7b220fffb9233241 --require-virtualenv && pip3 install git+https://github.com/enteropositivo/pyzbar.git@a52ff0b2e8ff714ba53bbf6461c89d672a304411#egg=pyzbar --require-virtualenv && pip3 install embit dataclasses qrcode tk opencv-python --require-virtualenv && echo 'Packages have been successfully installed in the virtual environment.' && deactivate"
    fi

    ### CODE TO AUTOMATE IN BIN/ACTIVATE-DEACTIVATE WITHIN THE VENV (ONLY IN DEV Mode)

    # Activate function to insert
    ACTIVATE_CODE=$(
        cat <<'END'
# INSERTED CODE FOR SEEDSIGNER-EMULATOR INTEGRATION ##############################################################################################################
activate () {
    # Get the base directory of the virtual environment
    SRC_DIR=$(cd "$(dirname "$VIRTUAL_ENV")" && pwd)

    # Export SRC_DIR to be available in deactivate
    export SRC_DIR

    # Print the value of SRC_DIR for debugging
    echo "SRC_DIR: $SRC_DIR"

    # Rename original files and create temporary symbolic links
    echo "Creating symbolic links..."

    files=("gui/renderer.py" "hardware/buttons.py" "hardware/camera.py" "hardware/pivideostream.py")

    for file in "${files[@]}"; do
        if [ -f "$SRC_DIR/seedsigner/$file" ] && [ ! -L "$SRC_DIR/seedsigner/$file" ]; then
            mv "$SRC_DIR/seedsigner/$file" "$SRC_DIR/seedsigner/.${file##*/}"
            ln -s "$SRC_DIR/seedsigner-emulator/seedsigner/$file" "$SRC_DIR/seedsigner/$file"
        fi
    done

    # Verify if the symbolic links have been created
    for file in "${files[@]}"; do
        ls -l "$SRC_DIR/seedsigner/$file"
    done

    # Set control variable
    export ACTIVATING_VENV=TRUE
    echo
    echo "ACTIVATING_VENV: '$ACTIVATING_VENV'"
}
##################################################################################################################################################################
END
    )

    # Clear_links function to insert
    CLEAR_LINKS_CODE=$(
        cat <<'END'
# INSERTED CODE FOR SEEDSIGNER-EMULATOR INTEGRATION ##############################################################################################################
clear_links () {
    # Check if we are activating the environment to skip the additional portion
    if [ -z "${ACTIVATING_VENV:-}" ]; then
        echo "ACTIVATING_VENV: '$ACTIVATING_VENV' or NONE (DEACTIVATING)"
        echo
        # Print the value of VENV_DIR for debugging
        echo "SRC_DIR: $SRC_DIR"

        # Remove symbolic links when deactivating the virtual environment and restore original files
        echo "Removing symbolic links..."
        files=("gui/renderer.py" "hardware/buttons.py" "hardware/camera.py" "hardware/pivideostream.py")

        for file in "${files[@]}"; do
            if [ -L "$SRC_DIR/seedsigner/$file" ];then
                echo "Unlinking $SRC_DIR/seedsigner/$file"
                unlink "$SRC_DIR/seedsigner/$file"
                if [ -f "$SRC_DIR/seedsigner/.${file##*/}" ];then
                    echo "Restoring $SRC_DIR/seedsigner/.${file##*/}"
                    mv "$SRC_DIR/seedsigner/.${file##*/}" "$SRC_DIR/seedsigner/$file"
                else
                    echo "Temporary file not found: $SRC_DIR/seedsigner/.${file##*/}"
                fi
            else
                echo "Not a symbolic link: $SRC_DIR/seedsigner/$file"
            fi
        done

        # Verify if SRC_DIR is defined and then deactivate it
        if [ -n "${SRC_DIR:-}" ];then
            unset SRC_DIR
        fi
    else
        # Unset the ACTIVATING_VENV variable after activation
        unset ACTIVATING_VENV
    fi  
}
##################################################################################################################################################################
END
    )

    # Checking that bin/activate has not been patched previously
    if grep -q "# INSERTED CODE FOR SEEDSIGNER-EMULATOR INTEGRATION #" "$VENV_ACTIVATE_PATH"; then
        echo "$VENV_ACTIVATE_PATH has already been patched!"

    else
        echo "Patching $VENV_ACTIVATE ...($VENV_ACTIVATE_PATH)"
        echo

        # Create the activation file with the inserted functions at the beginning
        {
            echo "$ACTIVATE_CODE"
            echo "$CLEAR_LINKS_CODE"
            cat "$VENV_ACTIVATE_PATH"
        } >"${VENV_ACTIVATE_PATH}.aux" && mv "${VENV_ACTIVATE_PATH}.aux" "$VENV_ACTIVATE_PATH"

        # Insert the call to activate just before deactivate nondestructive
        sed -i '/^deactivate nondestructive/i activate # INSERTED LINE FOR SEEDSIGNER-EMULATOR INTEGRATION ########################################' "$VENV_ACTIVATE_PATH"

        # Insert the call to clear_links within deactivate
        sed -i '/^deactivate () {/a \    clear_links # INSERTED LINE FOR SEEDSIGNER-EMULATOR INTEGRATION ########################################' "$VENV_ACTIVATE_PATH"
    fi

else
    # TEST Mode (assumes requirements are present because they come from the repo)
    bash -c ". $VENV_ACTIVATE && cd .. && echo 'Virtual environment activated at: "$VENV_ACTIVATE_PATH"' && echo && python3 -m pip install --upgrade pip && python3 -m pip install --upgrade setuptools && pip install -r requirements.txt -r tests/requirements.txt --require-virtualenv && echo 'Packages have been successfully installed in the virtual environment from requirements.txt' && echo && echo 'Installing seedsigner module...' && pip install -e . && deactivate"
    echo

fi

echo "You can now activate your VENV with: source '$VENV_ACTIVATE'"

# Clean up variables
unset ACTIVATE_CODE CLEAR_LINKS_CODE VENV_ACTIVATE VENV_ACTIVATE_PATH VENV_NAME
unset PYTHON_CMD DEFAULT_EMULATOR REPO_PATH PYTHON_PATH PYTHON_CMD PYTHON310_PATH

# Open a new terminal instance to set in the corresponding directory
if [ "$VENV_MODE" = "DEV_VENV" ]; then
    # DEV Mode
    ABSOLUTE_DEST_PATH=$ABSOLUTE_VENV_DEST_PATH
else
    # TEST Mode
    ABSOLUTE_DEST_PATH=$(cd "$REPO_PATH" && pwd)
fi

bash -c "
    # Change to the desired directory
    cd $ABSOLUTE_DEST_PATH || exit 1

    # Execute the shell configuration script
    if [ -f ~/.bashrc ]; then
        . ~/.bashrc
    fi

    # Keep the terminal open
    exec bash
"