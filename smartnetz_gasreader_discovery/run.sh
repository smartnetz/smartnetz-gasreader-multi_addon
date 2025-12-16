#!/usr/bin/with-contenv bashio
set -e

export MQTT_HOST="$(bashio::config 'mqtt_host')"
export MQTT_PORT="$(bashio::config 'mqtt_port')"
export MQTT_USERNAME="$(bashio::config 'mqtt_username')"
export MQTT_PASSWORD="$(bashio::config 'mqtt_password')"
export MQTT_TLS="$(bashio::config 'mqtt_tls')"

export DISCOVERY_PREFIX="$(bashio::config 'discovery_prefix')"
export TELE_PREFIX="$(bashio::config 'tele_prefix')"
export JSON_SUFFIX="$(bashio::config 'json_suffix')"

python3 /app.py
