Smartnetz Gasreader MQTT Discovery Add-on (Für ein oder mehrere Smartnetz Gasreader)


-##################  INSTALLATION  ############################
1) Repository in Home Assistant Add-on Store  hinzufuegen
2) Add-on installieren
3) MQTT Broker Zugangsdaten in den Add-on Optionen setzen (Reiter Konfiguration)
4) Addon Starten

Bei Problemen hilft dir der Smartnetz Support unter: +43 676 555 666 1 (per Whatsapp)

Funktion:
- Lauscht auf tele/+/json
- Erkennt automatisch Tasmota Topics (z.B. Gaszaehler, Gaszaehler_Ort1, ...)
- Legt per MQTT Discovery ein eigenes Home-Assistant Geraet an
- Erstellt Sensoren aus JSON Feldern:
  gastotal, value, today_m3, today_kwh, yesterday_m3, yesterday_kwh, db_yesterday_m3, db_yesterday_kwh

Voraussetzungen
- MQTT Broker in Home Assistant (z.B. Mosquitto Add-on)
- Tasmota publish:
  tele/<Topic>/json (JSON Payload) - wird automatisch bereitgestellt.


Topic Wahl in Tasmota
- In Tasmota unter MQTT Topic den gewuenschten Namen setzen
- Add-on erkennt den Topic automatisch, kein YAML pro Geraet notwendig
