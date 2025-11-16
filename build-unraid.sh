#!/bin/bash
# Build script for Unraid Docker image

set -e

echo "Building Curio for Unraid..."

# Build the Docker image
docker build -f Dockerfile.unraid -t curio:latest .

echo "Build complete!"
echo ""
echo "To save the image for Unraid:"
echo "  docker save curio:latest | gzip > curio-unraid.tar.gz"
echo ""
echo "Or push to Docker Hub:"
echo "  docker tag curio:latest yourusername/curio:latest"
echo "  docker push yourusername/curio:latest"
