from prometheus_client import MetricsHandler, Gauge
import logging
import os
import platform
import socket
import threading
import uuid
from datetime import datetime
from flask import Flask, request, Response
import requests
from http.server import HTTPServer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

version = "0.6.25"
gauges = {}
skip_list = ["PASSKEY", "stationtype", "dateutc", "freq", "runtime", "model"]

resend_endpoint = os.environ.get('RESEND_DEST')
resend_bool = os.getenv("RESENDING", 'False').lower() in ('true', '1', 't')

prom_port = os.environ.get('PROM_PORT', 9110)


class PrometheusEndpointServer(threading.Thread):
    def __init__(self, httpd, *args, **kwargs):
        self.httpd = httpd
        super(PrometheusEndpointServer, self).__init__(*args, **kwargs)

    def run(self):
        self.httpd.serve_forever()


def start_prometheus_server():
    try:
        httpd = HTTPServer(("0.0.0.0", int(prom_port)), MetricsHandler)
    except (OSError, socket.error):
        return

    thread = PrometheusEndpointServer(httpd)
    thread.daemon = True
    thread.start()
    logging.info("Exporting Prometheus /metrics/ on port %s", prom_port)


start_prometheus_server()


@app.route('/version')
def versioning():
    return f'Ecowitt Eventbridge Version: {version}\n'


@app.route('/')
def system_status():
    flask_status = get_flask_status()
    # Add more status checks or information here
    return f'System Status\nFlask Status: {flask_status}\n'


@app.route('/data/report/', methods=['POST'])
def ecowitt_listener():
    logging.info("Data Received from device")
    if resend_bool:
        resend_data(str(request.get_data()))

    for key, value in request.form.items():
        if key.startswith("temp") and key.endswith("f"):
            celsius = fahrenheit_to_celsius(float(value))
            key = key[:-1] + 'c'
            update_gauge("ecowitt_{}".format(key), celsius)
        elif key in skip_list:
            continue
        else:
            update_gauge("ecowitt_{}".format(key), float(value))

    return 'OK'


def update_gauge(key, value):
    if key not in gauges:
        gauges[key] = Gauge(key, 'ECOWITT data gauge')
    gauges[key].set(value)


def get_mac_address():
    mac = uuid.getnode()
    mac_address = ':'.join(("%012X" % mac)[i:i+2] for i in range(0, 12, 2))
    return mac_address


def get_flask_status():
    python_version = platform.python_version()  # Python version
    flask_mode = 'Development mode' if app.debug else 'Production mode'  # Flask mode (debug or production)
    host = request.host  # Host address
    port = request.host.split(':')[1]  # Port number

    # Return a dictionary with the status information
    return {
        'Python Version': python_version,
        'Flask Mode': flask_mode,
        'Host': host,
        'Port': port,
        'MAC': get_mac_address()
    }


def fahrenheit_to_celsius(fahrenheit):
    celsius = (fahrenheit - 32) * 5 / 9
    return celsius


def resend_data(data):
    # Send a POST request to the resend endpoint with the data

    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    response = requests.post(f"http://{resend_endpoint}:{os.environ.get('RESEND_PORT', '8080')}/data/report/", data=data, headers=headers)
    if response.status_code == 200 or response.status_code == 201:
        logging.info('Data successfully resent to the destination endpoint - {}'.format(response.status_code))
    else:
        logging.info('Failed to resend data to the destination endpoint - {} - {}'.format(response.status_code, response.content))
    response.close()


if __name__ == '__main__':
    app.run(port=os.environ.get('LISTEN_PORT'))

