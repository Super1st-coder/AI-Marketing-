#!/bin/bash

echo "Starting Fury API in development mode..."

if [ ! -f .env ]; then
    echo "Warning: .env file not found. Copying from env.example..."
    cp env.example .env
    echo "Please edit .env file with your configuration"
    exit 1
fi

mkdir -p logs

python main.py

