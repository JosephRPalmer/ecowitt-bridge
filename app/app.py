from prometheus_client import MetricsHandler, Gauge
import logging
import os
import socket
import threading
from datetime import datetime
from http.server import HTTPServer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

version = "0.7.1.2"
gauges = {}
skip_list = ["PASSKEY", "stationtype", "dateutc", "freq", "runtime", "model"]

resend_endpoint = os.environ.get('RESEND_DEST')
resend_bool = os.getenv("RESENDING", 'False').lower() in ('true', '1', 't')

prom_port = int(os.environ.get('PROM_PORT', 9110))


class PrometheusEndpointServer(threading.Thread):
    def __init__(self, httpd, *args, **kwargs):
        self.httpd = httpd
        super(PrometheusEndpointServer, self).__init__(*args, **kwargs)

    def run(self):
        self.httpd.serve_forever()


def start_prometheus_server():
    try:
        httpd = HTTPServer(("0.0.0.0", prom_port), MetricsHandler)
    except (OSError, socket.error) as e:
        logging.error("Failed to start Prometheus server: %s", str(e))
        return

    thread = PrometheusEndpointServer(httpd)
    thread.daemon = True
    thread.start()
    logging.info("Exporting Prometheus /metrics/ on port %s", prom_port)


def listen_and_relay(resend_dest, resend_port):
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_socket.bind(('0.0.0.0', int(os.environ.get('LISTEN_PORT', 8082))))
    listen_socket.listen(1)

    logging.info("Listening on port 8082 and resending to %s:%s", resend_dest, resend_port)

    while True:
        client_socket, client_address = listen_socket.accept()
        logging.info("Socket open on {}".format(client_socket))
        logging.info("Accepted connection from %s:%s", client_address[0], client_address[1])

        received_data = client_socket.recv(4096)

        received_data_str = received_data.decode('utf-8')

        parsed_data = received_data_str.split('\n')

        logging.info("Parsed data:")
        for line in parsed_data:
            logging.info(line)

        for key, value in parse_string_to_dict(str(parsed_data[6:])).items():
            logging.info("{}:{}".format(key,value))
            if key.startswith("temp") and key.endswith("f"):
                celsius = fahrenheit_to_celsius(float(value))
                key = key[:-1] + 'c'
                update_gauge("ecowitt_{}".format(key), celsius)
            elif key.startswith("barom") and key.endswith("in"):
                hpa = in_to_hpa(float(value))
                key = key[:-2] + 'hpa'
                update_gauge("ecowitt_{}".format(key), hpa)
            elif key in skip_list:
                continue
            else:
                update_gauge("ecowitt_{}".format(key), float(value))

        if resend_bool:
            logging.info("Resending to: {}:{}".format(resend_dest, resend_port))
            send_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            send_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            send_socket.connect((resend_dest, resend_port))
            logging.info("Sending received data to %s:%s", resend_dest, resend_port)

            send_socket.sendall(received_data)

            send_socket.close()

        client_socket.close()


def parse_string_to_dict(input_string):
    datapoints = {}
    pairs = input_string.replace("[","").replace("'","").replace("]","").split('&')

    for pair in pairs:
        key, value = pair.split('=')
        datapoints[key] = value

    return datapoints


def update_gauge(key, value):
    if key not in gauges:
        gauges[key] = Gauge(key, 'ECOWITT data gauge')
    gauges[key].set(value)


def fahrenheit_to_celsius(fahrenheit):
    celsius = (fahrenheit - 32) * 5 / 9
    return celsius

def in_to_hpa(ins):
    hpa = ins * 33.6585
    return hpa

if __name__ == '__main__':
    logging.info("Ecowitt Eventbridge by JRP - Version {}".format(version))
    start_prometheus_server()
    listen_and_relay(str(os.environ.get("RESEND_DEST")), int(os.environ.get("RESEND_PORT", 8080)))

