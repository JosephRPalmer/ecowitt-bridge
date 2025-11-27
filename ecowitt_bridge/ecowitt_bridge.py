from prometheus_client import MetricsHandler, Gauge
import asyncio
import logging
import os
import socket
import threading
from http.server import HTTPServer
from pydantic_settings import BaseSettings, SettingsConfigDict


from utils import fahrenheit_to_celsius, in_to_hpa, parse_string_to_dict
from gauge_definitions import GaugeDefinitions

version = "0.9.4"
gauges = {}
skip_list = ["PASSKEY", "stationtype", "dateutc", "freq", "runtime", "model"]

class Settings(BaseSettings):
    model_config = SettingsConfigDict()
    resend_dest: str = ""
    resend_port: int = 8080
    resending: bool = True
    prom_port: int = 9110
    listen_port: int = 8082
    loglevel: str = 'INFO'

settings = Settings()

logging.basicConfig(level=logging.WARN,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class PrometheusEndpointServer(threading.Thread):
    def __init__(self, httpd, *args, **kwargs):
        self.httpd = httpd
        super(PrometheusEndpointServer, self).__init__(*args, **kwargs)

    def run(self):
        self.httpd.serve_forever()


def start_prometheus_server():
    try:
        httpd = HTTPServer(("0.0.0.0", settings.prom_port), MetricsHandler)
    except (OSError, socket.error) as e:
        logging.error("Failed to start Prometheus server: %s", str(e))
        return

    thread = PrometheusEndpointServer(httpd)
    thread.daemon = True
    thread.start()
    logging.info("Exporting Prometheus /metrics/ on port %s", settings.prom_port)


def listen_and_relay(resend_dest, resend_port, listen_port):
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_socket.bind(('0.0.0.0', listen_port))
    listen_socket.listen(1)

    logging.info("Listening on port {} and resending to {}:{}".format(
        listen_port, resend_dest, resend_port))

    while True:
        client_socket, client_address = listen_socket.accept()
        logging.info("Socket open on {}".format(client_socket))
        logging.info("Accepted connection from %s:%s",
                     client_address[0], client_address[1])

        received_data = client_socket.recv(4096)

        received_data_str = received_data.decode('utf-8')

        parsed_data = received_data_str.split('\n')

        logging.debug("Parsed data:")
        for line in parsed_data:
            logging.debug(line)

        for key, value in parse_string_to_dict(str(parsed_data[6:])).items():
            logging.debug("{}:{}".format(key, value))
            if key.startswith("temp") and key.endswith("f"):
                celsius = fahrenheit_to_celsius(float(value))
                key = key[:-1] + 'c'
                update_gauge(key, celsius)
            elif key.startswith("barom") and key.endswith("in"):
                hpa = in_to_hpa(float(value))
                key = key[:-2] + 'hpa'
                update_gauge(key, hpa)
            elif key in skip_list:
                continue
            else:
                update_gauge(key, float(value))

        if settings.resending:
            logging.info("Resending to: {}:{}".format(
                resend_dest, resend_port))
            asyncio.run(resending_async(resend_dest, resend_port, received_data))

        client_socket.close()

async def resending_async(resend_dest, resend_port, received_data):
    try:
        send_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        send_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        send_socket.connect((resend_dest, resend_port))
        logging.info("Sending received data to %s:%s", resend_dest, resend_port)

        send_socket.sendall(received_data)

    except socket.error as e:
        logging.error("Socket error: %s", str(e))

    except Exception as e:
        logging.error("An unexpected error occurred: %s", str(e))

    finally:
        if send_socket:
            send_socket.close()
            logging.info("Socket closed")


def update_gauge(key, value):
    key = "ecowitt_{}".format(key)
    if key not in gauges:
        if key in GaugeDefinitions:
            description = GaugeDefinitions[key].value
        else:
            logging.debug(f"Key '{key}' not found in GaugeDefinitions, using default description.")
            description = 'ECOWITT data gauge'
        gauges[key] = Gauge(key, description)
    gauges[key].set(value)


if __name__ == '__main__':
    logging.info("Ecowitt Eventbridge by JRP - Version {}".format(version))
    logging.info("Log level set to: {}".format(getattr(settings, 'loglevel', 'INFO')))
    logging.debug("Debug logging is enabled.")
    start_prometheus_server()
    listen_and_relay(settings.resend_dest, settings.resend_port, settings.listen_port)
