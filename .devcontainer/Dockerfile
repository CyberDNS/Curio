FROM mcr.microsoft.com/devcontainers/python:1-3.12-bullseye

# Install Node.js for frontend development
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get update \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --upgrade pip

# Install common Python tools
RUN pip install black pylint pytest httpx

USER vscode
