#!/bin/bash

# Function to check if venv exists and create one if needed
check_and_create_venv() {
    if [ ! -d "venv" ]; then
        echo "Virtual environment not found. Creating one..."
        python3 -m venv venv
    fi
}

# Function to handle graceful shutdown
graceful_shutdown() {
    echo "Gracefully shutting down..."
    pkill -f python
    exit 0
}

# Trap termination signals and call graceful_shutdown
trap graceful_shutdown SIGINT SIGTERM

# Check and create venv if needed
check_and_create_venv

# Activate the virtual environment
source venv/bin/activate

# Install the requirements
pip install -r requirements.txt

# Start main.py and pass all command-line arguments
python main.py "$@"