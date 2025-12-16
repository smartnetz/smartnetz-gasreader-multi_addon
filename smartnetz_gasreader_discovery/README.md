Smartnetz Gasreader Discovery Add-on

Funktion
- Lauscht auf tele/+/json
- Erkennt automatisch Tasmota Topics (z.B. Gaszaehler, Gaszaehler_Ort1, ...)
- Legt per MQTT Discovery ein eigenes Home-Assistant Geraet an
- Erstellt Sensoren aus JSON Feldern:
  gastotal, value, today_m3, today_kwh, yesterday_m3, yesterday_kwh, db_yesterday_m3, db_yesterday_kwh

Voraussetzungen
- MQTT Broker in Home Assistant (z.B. Mosquitto Add-on)
- Tasmota publish:
  tele/<Topic>/json (JSON Payload)

Install
- Repo in Home Assistant Add-on Store als Custom Repository hinzufuegen
- Add-on installieren
- MQTT Broker Zugangsdaten in den Add-on Optionen setzen
- Starten

Topic Wahl in Tasmota
- In Tasmota unter MQTT Topic den gewuenschten Namen setzen
- Add-on erkennt den Topic automatisch, kein YAML pro Geraet notwendig
