import os
import json
import ssl
import time
from typing import Dict, Any, Set, Optional

import paho.mqtt.client as mqtt

MQTT_HOST = os.getenv("MQTT_HOST", "core-mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
MQTT_TLS = os.getenv("MQTT_TLS", "false").lower() == "true"

DISCOVERY_PREFIX = os.getenv("DISCOVERY_PREFIX", "homeassistant")
TELE_PREFIX = os.getenv("TELE_PREFIX", "tele").strip("/")
JSON_SUFFIX = os.getenv("JSON_SUFFIX", "json").strip("/")

SUB_JSON = f"{TELE_PREFIX}/+/{JSON_SUFFIX}"
SUB_LWT = f"{TELE_PREFIX}/+/LWT"

DISCOVERED: Set[str] = set()

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

def parse_device_topic(full_topic: str) -> str:
    # tele/<dev>/json
    parts = full_topic.split("/")
    if len(parts) >= 3 and parts[0] == TELE_PREFIX and parts[2] == JSON_SUFFIX:
        return parts[1]
    return ""

def _json_value_template(key: str) -> str:
    # robust if Tasmota publishes strings: "5132.63"
    return "{{ (value_json.%s | default('0') | string | replace(',', '.') ) | float }}" % key

def publish_discovery_for_device(client: mqtt.Client, dev: str) -> None:
    node_id = f"smartnetz_gasreader_{dev}"
    device_obj = {
        "identifiers": [node_id],
        "name": f"Smartnetz Gasreader {dev}",
        "manufacturer": "Smartnetz",
        "model": "Gasreader",
    }

    availability = [
        {
            "topic": f"{TELE_PREFIX}/{dev}/LWT",
            "payload_available": "Online",
            "payload_not_available": "Offline",
        }
    ]

    state_topic = f"{TELE_PREFIX}/{dev}/{JSON_SUFFIX}"

    for key, suffix, unit, dev_class, st_class in SENSOR_DEFS:
        discovery_topic = f"{DISCOVERY_PREFIX}/sensor/{node_id}/{key}/config"
        payload: Dict[str, Any] = {
            "name": suffix,
            "unique_id": f"{node_id}_{key}",
            "state_topic": state_topic,
            "value_template": _json_value_template(key),
            "unit_of_measurement": unit,
            "state_class": st_class,
            "device": device_obj,
            "availability": availability,
        }
        if dev_class:
            payload["device_class"] = dev_class

        client.publish(discovery_topic, json.dumps(payload), retain=True)

def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code != 0:
        return
    client.subscribe(SUB_JSON)
    client.subscribe(SUB_LWT)
    for dev in list(DISCOVERED):
        publish_discovery_for_device(client, dev)


def on_message(client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
    topic = msg.topic
    if topic.startswith(f"{TELE_PREFIX}/") and topic.endswith(f"/{JSON_SUFFIX}"):
        dev = parse_device_topic(topic)
        if not dev:
            return

        try:
            payload = msg.payload.decode("utf-8", errors="ignore").strip()
            data = json.loads(payload)
        except Exception:
            return

        # Discover only if it looks like a Smartnetz gasreader payload
        if "gastotal" not in data or "value" not in data:
            return

        if dev not in DISCOVERED:
            DISCOVERED.add(dev)
            publish_discovery_for_device(client, dev)

def main() -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if MQTT_USERNAME:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    if MQTT_TLS:
        ctx = ssl.create_default_context()
        client.tls_set_context(ctx)

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()

    try:
        while True:
            time.sleep(5)
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
