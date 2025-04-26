#!/bin/bash

# Set error handling
set -e
echo "🚀 Starting deployment process for Construction Management API..."

# Environment Variables
CONTAINER_NAME="construction-mgmt-api"
IMAGE_NAME="construction-mgmt-api"
HOST_PORT=8002
CONTAINER_PORT=8000
MONGODB_URI=${MONGODB_URI:-"mongodb://localhost:27017/construction_db"}
JWT_SECRET_KEY=${JWT_SECRET_KEY:-"a9ddbcaba8c0ac1a0a812dc0c2f08514f5593b02f0a1a9fdd4da1e28d6391cb7"}

# Check if uploads volume exists (for receipts)
if sudo docker volume ls | grep -q "${CONTAINER_NAME}_uploads"; then
    echo "📦 Found existing ${CONTAINER_NAME}_uploads volume - preserving uploaded files"
else
    echo "📦 Creating ${CONTAINER_NAME}_uploads volume for uploaded files"
    sudo docker volume create ${CONTAINER_NAME}_uploads
fi

# Build new image
echo "🏗️ Building new Docker image..."
sudo docker build --no-cache -t ${IMAGE_NAME}:new .

# Stop and remove existing container
echo "🛑 Stopping existing container (if running)..."
sudo docker stop ${CONTAINER_NAME} 2>/dev/null || true
echo "🗑️ Removing existing container (if present)..."
sudo docker rm ${CONTAINER_NAME} 2>/dev/null || true

# Tag the new image and clean up
echo "🔄 Switching to new image..."
sudo docker tag ${IMAGE_NAME}:new ${IMAGE_NAME}:latest
sudo docker rmi ${IMAGE_NAME}:new 2>/dev/null || true

# Remove any old untagged images to save space
echo "🧹 Cleaning up unused images..."
sudo docker image prune -f

# Run new container
echo "▶️ Starting new container on port ${HOST_PORT}..."
sudo docker run -d \
    --name ${CONTAINER_NAME} \
    -p ${HOST_PORT}:${CONTAINER_PORT} \
    -v ${CONTAINER_NAME}_uploads:/app/uploads:rw \
    -e MONGODB_URI="${MONGODB_URI}" \
    -e JWT_SECRET_KEY="${JWT_SECRET_KEY}" \
    --restart unless-stopped \
    ${IMAGE_NAME}:latest

# Check if container is running
if sudo docker ps | grep -q "${CONTAINER_NAME}"; then
    echo "✅ Deployment successful! Container is running."
    echo "📝 Container logs:"
    sudo docker logs ${CONTAINER_NAME} --tail 20
else
    echo "❌ Deployment failed! Container is not running."
    echo "📝 Failed container logs:"
    sudo docker logs ${CONTAINER_NAME} --tail 50
    exit 1
fi

# Print container info
echo -e "\nℹ️ Container information:"
sudo docker inspect ${CONTAINER_NAME} | grep "IPAddress\|Status\|StartedAt"

echo -e "\n🌟 Deployment complete!"
echo "🔗 API is accessible at http://localhost:${HOST_PORT}"
echo "📚 Documentation at http://localhost:${HOST_PORT}/docs"
echo "🔐 Secured with JWT authentication"
echo "📊 Construction Management API is ready for use" 