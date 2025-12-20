import os
import json
import ssl
import time
from typing import Dict, Any, Set

import paho.mqtt.client as mqtt

# ------------------------------------------------------------
# Konfiguration (aus Add-on ENV)
# ------------------------------------------------------------
MQTT_HOST = os.getenv("MQTT_HOST", "core-mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
MQTT_TLS = os.getenv("MQTT_TLS", "false").lower() == "true"

DISCOVERY_PREFIX = "homeassistant"
TELE_PREFIX = "tele"

# ------------------------------------------------------------
# Logging
# ------------------------------------------------------------
def log(msg: str):
    print(f"[SMARTNETZ] {msg}", flush=True)

# ------------------------------------------------------------
# MQTT Topics (JSON ONLY)
# ------------------------------------------------------------
SUB_JSON = f"{TELE_PREFIX}/+/json"
SUB_LWT  = f"{TELE_PREFIX}/+/LWT"

# ------------------------------------------------------------
# Runtime State
# ------------------------------------------------------------
DISCOVERED: Set[str] = set()

# ------------------------------------------------------------
# Sensor Definitionen
# key, name, unit, device_class, state_class
# ------------------------------------------------------------
SENSOR_DEFS = [
    ("gastotal", "Zaehlerstand", "m³", "gas", "total_increasing"),
    ("value", "Zaehlung seit Nullung", "m³", None, "measurement"),
    ("today_m3", "Verbrauch Volumen heute", "m³", None, "measurement"),
    ("today_kwh", "Verbrauch Energie heute", "kWh", "energy", "measurement"),
    ("yesterday_m3", "Verbrauch Volumen gestern", "m³", None, "measurement"),
    ("yesterday_kwh", "Verbrauch Energie gestern", "kWh", "energy", "measurement"),
    ("db_yesterday_m3", "Verbrauch Volumen vorgestern", "m³", None, "measurement"),
    ("db_yesterday_kwh", "Verbrauch Energie vorgestern", "kWh", "energy", "measurement"),
]

# ------------------------------------------------------------
# Discovery Publisher (JSON only)
# ------------------------------------------------------------
def publish_discovery(client: mqtt.Client, dev: str) -> None:
    log(f"Publishing JSON discovery for {dev}")

    node_id = f"smartnetz_gasreader_{dev}"

    device = {
        "identifiers": [node_id],
        "name": f"Smartnetz Gasreader {dev}",
        "manufacturer": "Smartnetz",
        "model": "Gasreader",
    }

    availability = [{
        "topic": f"{TELE_PREFIX}/{dev}/LWT",
        "payload_available": "Online",
        "payload_not_available": "Offline",
    }]

    for key, name, unit, dev_class, state_class in SENSOR_DEFS:
        discovery_topic = f"{DISCOVERY_PREFIX}/sensor/{node_id}/{key}/config"

        payload: Dict[str, Any] = {
            "name": name,
            "unique_id": f"{node_id}_{key}",
            "state_topic": f"{TELE_PREFIX}/{dev}/json",
            "unit_of_measurement": unit,
            "state_class": state_class,
            "device": device,
            "availability": availability,
            "value_template": (
                "{{ (value_json.%s | default('0') | string "
                "| replace(',', '.') ) | float }}" % key
            ),
        }

        if dev_class:
            payload["device_class"] = dev_class

        client.publish(discovery_topic, json.dumps(payload), retain=True)

# ------------------------------------------------------------
# MQTT Callbacks
# ------------------------------------------------------------
def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code != 0:
        log(f"MQTT connect failed: {reason_code}")
        return

    log("MQTT connected (JSON only)")
    client.subscribe(SUB_JSON)
    client.subscribe(SUB_LWT)

def on_message(client, userdata, msg):
    topic = msg.topic
    parts = topic.split("/")

    # --------------------------------------------------------
    # tele/<device>/json
    # --------------------------------------------------------
    if len(parts) == 3 and parts[0] == TELE_PREFIX and parts[2] == "json":
        dev = parts[1]

        try:
            data = json.loads(msg.payload.decode())
        except Exception as e:
            log(f"JSON parse error from {dev}: {e}")
            return

        # Minimal-Check: Pflichtfelder vorhanden?
        if "gastotal" in data and "value" in data:
            log(f"Valid JSON from {dev}")

            # Discovery immer neu publishen (überschreibt retained sauber)
            publish_discovery(client, dev)
            DISCOVERED.add(dev)

        return

# ------------------------------------------------------------
# Main Loop
# ------------------------------------------------------------
def main():
    log("Starting Smartnetz Gasreader Discovery (JSON only)")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    if MQTT_USERNAME:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    if MQTT_TLS:
        ctx = ssl.create_default_context()
        client.tls_set_context(ctx)

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()

    try:
        while True:
            time.sleep(10)
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
