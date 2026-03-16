import os
import json
import ssl
from typing import Dict, Any, Set, List, Tuple, Optional
import paho.mqtt.client as mqtt

MQTT_HOST = os.getenv("MQTT_HOST", "core-mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
MQTT_TLS = os.getenv("MQTT_TLS", "false").lower() == "true"

DISCOVERY_PREFIX = os.getenv("DISCOVERY_PREFIX", "homeassistant")
TELE_PREFIX = "tele"

SUB_JSON = f"{TELE_PREFIX}/+/json"
SUB_LWT = f"{TELE_PREFIX}/+/LWT"

DISCOVERED_GAS: Set[str] = set()
DISCOVERED_WATER: Set[str] = set()

# (json_key, Anzeigename, Einheit, device_class, state_class)
GAS_SENSOR_DEFS: List[Tuple[str, str, str, Optional[str], str]] = [
    ("gastotal", "Zählerstand", "m³", "gas", "total_increasing"),
    ("value", "Zählung seit Nullung", "m³", None, "measurement"),
    ("today_m3", "Verbrauch Volumen heute", "m³", None, "measurement"),
    ("today_kwh", "Verbrauch Energie heute", "kWh", "energy", "measurement"),
    ("yesterday_m3", "Verbrauch Volumen gestern", "m³", None, "measurement"),
    ("yesterday_kwh", "Verbrauch Energie gestern", "kWh", "energy", "measurement"),
    ("db_yesterday_m3", "Verbrauch Volumen vorgestern", "m³", None, "measurement"),
    ("db_yesterday_kwh", "Verbrauch Energie vorgestern", "kWh", "energy", "measurement"),
]

WATER_SENSOR_DEFS: List[Tuple[str, str, str, Optional[str], str]] = [
    ("zaehlerstand", "Wasserzählerstand", "m³", "water", "total_increasing"),
    ("value_m3", "Zählung seit Nullung", "m³", "water", "measurement"),
    ("today_l", "Wasserverbrauch heute", "L", "water", "measurement"),
    ("yesterday_l", "Wasserverbrauch gestern", "L", "water", "measurement"),
    ("dbyesterday_l", "Wasserverbrauch vorgestern", "L", "water", "measurement"),
]

def log(msg: str):
    print(f"[SMARTNETZ] {msg}", flush=True)

def build_availability(dev: str) -> list:
    return [{
        "topic": f"{TELE_PREFIX}/{dev}/LWT",
        "payload_available": "Online",
        "payload_not_available": "Offline",
    }]

def make_value_template(key: str) -> str:
    return "{{ (value_json.%s | default('0') | string | replace(',', '.')) | float }}" % key

def publish_sensor_configs(
    client: mqtt.Client,
    dev: str,
    node_id: str,
    device_name: str,
    model: str,
    sensor_defs: List[Tuple[str, str, str, Optional[str], str]],
) -> None:
    device = {
        "identifiers": [node_id],
        "name": device_name,
        "manufacturer": "Smartnetz",
        "model": model,
    }

    availability = build_availability(dev)

    for key, name, unit, dev_class, state_class in sensor_defs:
        discovery_topic = f"{DISCOVERY_PREFIX}/sensor/{node_id}/{key}/config"

        payload: Dict[str, Any] = {
            "name": name,
            "unique_id": f"{node_id}_{key}",
            "state_topic": f"{TELE_PREFIX}/{dev}/json",
            "unit_of_measurement": unit,
            "state_class": state_class,
            "device": device,
            "availability": availability,
            "value_template": make_value_template(key),
        }

        if dev_class:
            payload["device_class"] = dev_class

        client.publish(discovery_topic, json.dumps(payload), retain=True)

def publish_gas_discovery(client: mqtt.Client, dev: str) -> None:
    node_id = f"smartnetz_gasreader_{dev}"

    publish_sensor_configs(
        client=client,
        dev=dev,
        node_id=node_id,
        device_name=f"Smartnetz Gasreader {dev}",
        model="Gasreader",
        sensor_defs=GAS_SENSOR_DEFS,
    )

    log(f"Gasreader discovery published for {dev}")

def publish_water_discovery(client: mqtt.Client, dev: str) -> None:
    node_id = f"smartnetz_wasserreader_{dev}"

    publish_sensor_configs(
        client=client,
        dev=dev,
        node_id=node_id,
        device_name=f"Smartnetz Wasserreader {dev}",
        model="Wasserreader",
        sensor_defs=WATER_SENSOR_DEFS,
    )

    log(f"Wasserreader discovery published for {dev}")

def is_gasreader_json(data: Dict[str, Any]) -> bool:
    return "gastotal" in data and "value" in data

def is_waterreader_json(data: Dict[str, Any]) -> bool:
    return "zaehlerstand" in data and "value_m3" in data

def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code != 0:
        log(f"MQTT connect failed: {reason_code} ({mqtt.connack_string(reason_code)})")
        return

    log(f"MQTT connected -> {MQTT_HOST}:{MQTT_PORT} tls={MQTT_TLS}")
    client.subscribe(SUB_JSON)
    client.subscribe(SUB_LWT)

def on_message(client, userdata, msg):
    parts = msg.topic.split("/")

    if len(parts) == 3 and parts[0] == TELE_PREFIX and parts[2] == "json":
        dev = parts[1]

        try:
            payload_text = msg.payload.decode("utf-8", errors="ignore")
            data = json.loads(payload_text)
        except Exception as e:
            log(f"JSON parse error from {dev}: {e}")
            return

        if is_gasreader_json(data):
            if dev not in DISCOVERED_GAS:
                log(f"Valid Gasreader JSON from {dev} -> publish discovery")
                publish_gas_discovery(client, dev)
                DISCOVERED_GAS.add(dev)

        elif is_waterreader_json(data):
            if dev not in DISCOVERED_WATER:
                log(f"Valid Wasserreader JSON from {dev} -> publish discovery")
                publish_water_discovery(client, dev)
                DISCOVERED_WATER.add(dev)

        else:
            log(f"Unknown JSON structure from {dev}: keys={list(data.keys())}")

def main():
    log("Starting Smartnetz Discovery (Gasreader + Wasserreader)")
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    if MQTT_USERNAME:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    if MQTT_TLS:
        ctx = ssl.create_default_context()
        client.tls_set_context(ctx)

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_forever()

if __name__ == "__main__":
    main()
