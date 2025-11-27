# Ecowitt Bridge

This python app creates an endpoint from which you can resend Ecowitt stats to Homebridge for use in Homekit but also presents you a Prometheus exporter endpoint.

## Working Items
- Prometheus Exporter
- Homebridge Forwarder

## How To Use

- This has been tesed to work with this plugin for Homebridge - https://github.com/rhockenbury/homebridge-ecowitt-weather-sensors
- Setup the plugin as expected, with the stations mac address and port 8080
- Make use of the docker compose example below or the example in the repo and customise for your use case
- Set the following environment vars:
      - LISTEN_PORT=8082 (incoming port)
      - PROM_PORT=9110 (prometheus endpoint port)
      - RESEND_DEST (forwarding destination)
      - RESEND_PORT (forwarding port)
      - RESENDING=1 (to make forwarding turn on
      - LOGLEVEL=DEBUG
- Ensure the ports exposed in the docker compose match the ports referenced under LISTEN_PORT and PROM_PORT

## Docker Compose Example

```
services:
  ecowitt-eventbridge:
    image: josephrpalmer/ecowitt-eventbridge
    container_name: ecowitt-eventbridge
    network_mode: bridge
    restart: always
    environment:
      - LISTEN_PORT=8082
      - PROM_PORT=9110
      - RESEND_DEST=10.10.1.233
      - RESEND_PORT=8080
      - RESENDING=1
      - LISTEN_ADDR=10.10.1.233
      - LOGLEVEL=DEBUG
    ports:
      - "8082:8082"
      - "9110:9110"
```

