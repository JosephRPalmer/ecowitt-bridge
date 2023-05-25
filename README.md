# Ecowitt Event Bridge

This python app creates an endpoint from which you can resend Ecowitt stats to Homebridge for use in Homekit but also presents you a Prometheus exporter endpoint. 

## Working Items
- Prometheus Exporter
- Homebridge Forwarder

## Future Items
- Graphite Support

## How To Use

- This has been tesed to work with this plugin for Homebridge - https://github.com/spatialdude/homebridge-ecowitt
- Setup the plugin as expected, with the stations mac address and port 8080
- Run the docker container and expose no ports (this is due to using python sockets) 
- Set the following environment vars:       
      - LISTEN_PORT=8082 (incoming port)
      - PROM_PORT=9110 (prometheus endpoint port)
      - RESEND_DEST (forwarding destination)
      - RESEND_PORT (forwarding port)
      - RESENDING=1 (to make forwarding turn on

## Docker Compose Example

    ecowitt-eventbridge:
      image: josephrpalmer/ecowitt-eventbridge
      container_name: ecowitt-eventbridge
      network_mode: host
      restart: always
      environment:
        - LISTEN_PORT=8082
        - PROM_PORT=9110
        - RESEND_DEST=XXX.XXX.XXX.XXX
        - RESEND_PORT=8080
        - RESENDING=1

