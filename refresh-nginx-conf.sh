#!/bin/bash

set -e

CONFIG_NAME="com.nginx.sync-endpoint-locations.conf"
CONFIG_PATH="./config/nginx/sync-endpoint-locations.conf"
STACK_NAME="syncldap"
SERVICE_NAME="syncldap_nginx"

echo "🔄 Re-creating Docker config: $CONFIG_NAME"
docker config rm $CONFIG_NAME || true
docker config create $CONFIG_NAME $CONFIG_PATH

echo "📦 Updating nginx service to use updated config..."
docker service update --force \
  --config-rm $CONFIG_NAME \
  --config-add source=$CONFIG_NAME,target=/etc/nginx/conf/sync-endpoint-locations.conf \
  $SERVICE_NAME

echo "✅ nginx config updated and service redeployed."

