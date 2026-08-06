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

DISCOVERED_GAS: Set[str] = set()
DISCOVERED_WATER: Set[str] = set()
DISCOVERED_VISION: Set[str] = set()

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

VISION_SENSOR_DEFS: List[Tuple[str, str, str, Optional[str], Optional[str]]] = [
    ("value", "Wasserzählerstand", "m³", "water", "total_increasing"),
    ("flow_l_min", "Durchfluss", "L/min", "water", "measurement"),
    ("flow_l_h", "Durchfluss pro Stunde", "L/h", "water", "measurement"),
    ("today_l", "Wasserverbrauch heute", "L", "water", "measurement"),
    ("yesterday_l", "Wasserverbrauch gestern", "L", "water", "measurement"),
    ("week_l", "Wasserverbrauch Woche", "L", "water", "measurement"),
    ("month_l", "Wasserverbrauch Monat", "L", "water", "measurement"),
    ("month_m3", "Wasserverbrauch Monat", "m³", "water", "measurement"),
    ("year_l", "Wasserverbrauch Jahr", "L", "water", "measurement"),
    ("year_m3", "Wasserverbrauch Jahr", "m³", "water", "measurement"),
    ("last_hour_l", "Wasserverbrauch letzte Stunde", "L", "water", "measurement"),
    ("last_24h_l", "Wasserverbrauch letzte 24 Stunden", "L", "water", "measurement"),
    ("avg_7d_l", "Durchschnitt 7 Tage", "L", "water", "measurement"),
    ("rssi", "WLAN-Signal", "dBm", "signal_strength", "measurement"),
    ("uptime", "Laufzeit", "s", "duration", "measurement"),
    ("image_bytes", "Bildgröße", "B", "data_size", "measurement"),
    ("flash", "Blitzstärke", "%", None, "measurement"),
    ("flash_ms", "Blitz-Vorlauf", "ms", "duration", "measurement"),
    ("config_version", "Config-Version", "", None, None),
]


def log(msg: str) -> None:
    print(f"[SMARTNETZ] {msg}", flush=True)


def build_availability(dev: str) -> list:
    return [{
        "topic": f"{TELE_PREFIX}/{dev}/LWT",
        "payload_available": "Online",
        "payload_not_available": "Offline",
    }]


def make_value_template(key: str) -> str:
    return "{{ (value_json.%s | default('0') | string | replace(',', '.')) | float }}" % key


def make_text_template(key: str) -> str:
    return "{{ value_json.%s | default('') }}" % key


def safe_id(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value)
    return "_".join(part for part in cleaned.split("_") if part)


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
    node_id = f"smartnetz_gasreader_{safe_id(dev)}"

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
    node_id = f"smartnetz_wasserreader_{safe_id(dev)}"

    publish_sensor_configs(
        client=client,
        dev=dev,
        node_id=node_id,
        device_name=f"Smartnetz Wasserreader {dev}",
        model="Wasserreader",
        sensor_defs=WATER_SENSOR_DEFS,
    )

    log(f"Wasserreader discovery published for {dev}")


def publish_vision_discovery(
    client: mqtt.Client,
    dev: str,
    data: Dict[str, Any],
) -> None:
    did = str(data.get("did", "")).strip()
    suffix = safe_id(did or dev)
    node_id = f"smartnetz_ki_vision_{suffix}"
    device_name = f"Smartnetz KI Vision {did}" if did else f"Smartnetz KI Vision {dev}"
    state_topic = f"{TELE_PREFIX}/{dev}/json"

    device = {
        "identifiers": [node_id],
        "name": device_name,
        "manufacturer": "Smartnetz",
        "model": "KI Vision",
        "sw_version": str(data.get("config_version", "")),
    }

    availability = build_availability(dev)

    for key, name, unit, dev_class, state_class in VISION_SENSOR_DEFS:
        discovery_topic = f"{DISCOVERY_PREFIX}/sensor/{node_id}/{key}/config"

        payload: Dict[str, Any] = {
            "name": name,
            "unique_id": f"{node_id}_{key}",
            "state_topic": state_topic,
            "device": device,
            "availability": availability,
            "value_template": make_value_template(key),
        }

        if unit:
            payload["unit_of_measurement"] = unit
        if dev_class:
            payload["device_class"] = dev_class
        if state_class:
            payload["state_class"] = state_class

        client.publish(discovery_topic, json.dumps(payload), retain=True)

    text_sensors = [
        ("status", "Erkennungsstatus"),
        ("raw", "Rohwert"),
        ("job_id", "Job-ID"),
        ("last_read_at", "Letzte Ablesung"),
        ("framesize", "Kameraauflösung"),
    ]

    for key, name in text_sensors:
        discovery_topic = f"{DISCOVERY_PREFIX}/sensor/{node_id}/{key}/config"
        payload = {
            "name": name,
            "unique_id": f"{node_id}_{key}",
            "state_topic": state_topic,
            "device": device,
            "availability": availability,
            "value_template": make_text_template(key),
        }
        client.publish(discovery_topic, json.dumps(payload), retain=True)

    leak_topic = f"{DISCOVERY_PREFIX}/binary_sensor/{node_id}/leak/config"
    leak_payload = {
        "name": "Leck erkannt",
        "unique_id": f"{node_id}_leak",
        "state_topic": state_topic,
        "device": device,
        "availability": availability,
        "device_class": "moisture",
        "value_template": "{{ 'ON' if value_json.leak | default(false) else 'OFF' }}",
        "payload_on": "ON",
        "payload_off": "OFF",
    }
    client.publish(leak_topic, json.dumps(leak_payload), retain=True)

    log(f"KI Vision discovery published for {dev} (DID {did or 'unbekannt'})")


def is_gasreader_json(data: Dict[str, Any]) -> bool:
    return "gastotal" in data and "value" in data


def is_waterreader_json(data: Dict[str, Any]) -> bool:
    return "zaehlerstand" in data and "value_m3" in data


def is_vision_json(data: Dict[str, Any]) -> bool:
    return (
        str(data.get("device", "")).strip().lower() == "smartnetz ki vision"
        and "did" in data
        and "value" in data
        and "flow_l_min" in data
    )


def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code != 0:
        log(f"MQTT connect failed: {reason_code} ({mqtt.connack_string(reason_code)})")
        return

    log(f"MQTT connected -> {MQTT_HOST}:{MQTT_PORT} tls={MQTT_TLS}")
    client.subscribe(SUB_JSON)
    client.subscribe(SUB_LWT)


def on_message(client, userdata, msg):
    parts = msg.topic.split("/")

    if len(parts) != 3 or parts[0] != TELE_PREFIX or parts[2] != "json":
        return

    dev = parts[1]

    try:
        payload_text = msg.payload.decode("utf-8", errors="ignore")
        data = json.loads(payload_text)
    except Exception as exc:
        log(f"JSON parse error from {dev}: {exc}")
        return

    if not isinstance(data, dict):
        log(f"Invalid JSON payload from {dev}: expected object")
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

    elif is_vision_json(data):
        did = str(data.get("did", "")).strip()
        discovery_key = f"{dev}:{did}"

        if discovery_key not in DISCOVERED_VISION:
            log(f"Valid KI Vision JSON from {dev} (DID {did}) -> publish discovery")
            publish_vision_discovery(client, dev, data)
            DISCOVERED_VISION.add(discovery_key)

    else:
        log(f"Unknown JSON structure from {dev}: keys={list(data.keys())}")


def main():
    log("Starting Smartnetz Discovery (Gasreader + Wasserreader + KI Vision)")
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
