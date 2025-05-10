#!/bin/bash

# Configuration
REPO_URL="https://github.com/daonin/litgrabber.git"
REPO_DIR="litgrabber"
IMAGE_NAME="litgrabber"
CONTAINER_NAME="litgrabber"
HOST_PATH="/trans500/backup/secondbrain/Inbox"
CONTAINER_PATH="/app/output"

if [ ! -d "$REPO_DIR" ]; then
    echo "🔄 Cloning fresh repository..."
    git clone "$REPO_URL" "$REPO_DIR"
    cp prodconfig.yaml "$REPO_DIR/config.yaml"
    NEED_UPDATE=1
else
    echo "🔄 Checking for updates in master branch..."
    cd "$REPO_DIR"
    git fetch origin
    LOCAL_HASH=$(git rev-parse master)
    REMOTE_HASH=$(git rev-parse origin/master)
    if [ "$LOCAL_HASH" = "$REMOTE_HASH" ]; then
        echo "✅ No updates in master. Exiting."
        exit 0
    else
        echo "⬆️ Updates found. Pulling latest changes..."
        git reset --hard origin/master
        cp ../prodconfig.yaml ./config.yaml
        NEED_UPDATE=1
    fi
    cd ..
fi

if [ "$NEED_UPDATE" = "1" ]; then
    echo "🛑 Stopping and removing existing container..."
    docker stop "$CONTAINER_NAME" 2>/dev/null
    docker rm "$CONTAINER_NAME" 2>/dev/null

    echo "🗑️ Removing old image..."
    docker rmi "$IMAGE_NAME" 2>/dev/null

    echo "🏗️ Building new image..."
    cd "$REPO_DIR"
    docker build -t "$IMAGE_NAME" .

    echo "🚀 Starting new container..."
    docker run -d \
        --name "$CONTAINER_NAME" \
        -v "$HOST_PATH":"$CONTAINER_PATH" \
        "$IMAGE_NAME"

    echo "✅ Done! Container is running."
    docker ps | grep "$CONTAINER_NAME"
fi