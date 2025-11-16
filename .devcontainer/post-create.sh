#!/bin/bash

# Install backend dependencies
if [ -f /workspace/backend/requirements.txt ]; then
    pip install -r /workspace/backend/requirements.txt
fi

# Install frontend dependencies
if [ -f /workspace/frontend/package.json ]; then
    cd /workspace/frontend && npm install
fi

echo "Development environment ready!"
