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

version = "0.9.5"
gauges = {}
skip_list = ["PASSKEY", "stationtype", "dateutc", "freq", "runtime", "model"]

class Settings(BaseSettings):
    model_config = SettingsConfigDict()
    resend_dest: str = ""
    resend_port: int = 8080
    resend_path: str = "/data"
    resending: bool = True
    prom_port: int = 9110
    listen_port: int = 8082
    loglevel: str = 'INFO'

settings = Settings()

logging.basicConfig(level=settings.loglevel if settings.loglevel in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] else 'INFO',
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


def listen_and_relay(resend_dest, resend_port, resend_path, listen_port):
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_socket.bind(('0.0.0.0', listen_port))
    listen_socket.listen(1)

    logging.info("Listening on port {} and resending to {}:{}{}".format(
        listen_port, resend_dest, resend_port, resend_path))

    while True:
        client_socket, client_address = listen_socket.accept()
        logging.info("Socket open on {}".format(client_socket))
        logging.info("Accepted connection from %s:%s",
                     client_address[0], client_address[1])

        received_data = client_socket.recv(4096)

        logging.debug(received_data)

        received_data_str = received_data.decode('utf-8')

        parsed_data = received_data_str.split('\n')

        logging.debug("Parsed data:")
        for line in parsed_data:
            logging.debug(line)

        for key, value in parse_string_to_dict(str(parsed_data[6:]), logging).items():
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
            logging.info("Resending to: {}:{}{}".format(
                resend_dest, resend_port, resend_path))
            asyncio.run(resending_async(resend_dest, resend_port, resend_path, received_data, received_data_str))

        client_socket.close()

def extract_http_headers(received_data_str):
    """Extract HTTP headers from incoming request data"""
    lines = received_data_str.split('\r\n')
    headers = {}
    
    for line in lines:
        if ':' in line and not line.startswith('POST') and not line.startswith('GET'):
            key, value = line.split(':', 1)
            headers[key.strip()] = value.strip()
        elif line == '':  # End of headers
            break
    
    return headers

def extract_http_body(received_data_str):
    """Extract the HTTP body (form data) from the incoming request"""
    parts = received_data_str.split('\r\n\r\n', 1)
    if len(parts) > 1:
        # Remove any trailing newlines/carriage returns from the body
        body = parts[1].strip()
        return body.encode('utf-8')
    return b''

async def resending_async(resend_dest, resend_port, resend_path, received_data, received_data_str):
    try:
        send_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        send_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        send_socket.connect((resend_dest, resend_port))
        
        # Extract headers and body from incoming request
        incoming_headers = extract_http_headers(received_data_str)
        http_body = extract_http_body(received_data_str)
        
        # Build HTTP request with copied headers
        content_length = len(http_body)
        http_request_lines = [
            f"POST {resend_path} HTTP/1.1",
            f"Host: {resend_dest}:{resend_port}",
        ]
        
        # Copy relevant headers from incoming request
        for header_name, header_value in incoming_headers.items():
            if header_name.lower() not in ['host', 'content-length', 'connection']:
                http_request_lines.append(f"{header_name}: {header_value}")
        
        # Add required headers
        http_request_lines.extend([
            f"Content-Length: {content_length}",
            f"Connection: close"
        ])
        
        # Join headers and add double CRLF before body
        http_headers = "\r\n".join(http_request_lines) + "\r\n\r\n"
        http_request = http_headers.encode('utf-8')
        
        logging.info("Sending HTTP POST to %s:%s%s", resend_dest, resend_port, resend_path)
        logging.debug("Copied headers: %s", list(incoming_headers.keys()))
        logging.debug("Body length: %d", len(http_body))
        logging.debug("Body content: %s", http_body.decode('utf-8')[:100] + "..." if len(http_body) > 100 else http_body.decode('utf-8'))
        
        # Send HTTP headers and body
        send_socket.sendall(http_request + http_body)
        
        # Read response (optional, for logging)
        response = send_socket.recv(1024).decode('utf-8', errors='ignore')
        if "200 OK" in response:
            logging.info("Data successfully sent via HTTP POST")
        else:
            logging.warning("Received response: %s", response.split('\r\n')[0])

    except socket.error as e:
        logging.error("Socket error: %s", str(e))
    except Exception as e:
        logging.error("An unexpected error occurred: %s", str(e))
    finally:
        if 'send_socket' in locals():
            send_socket.close()
            logging.debug("Socket closed")


def update_gauge(key, value):
    final_key = "ecowitt_{}".format(key)
    if final_key not in gauges:
        description = GaugeDefinitions.get(key, 'ECOWITT data gauge')
        gauges[final_key] = Gauge(final_key, description)
    gauges[final_key].set(value)


if __name__ == '__main__':
    logging.info("Ecowitt Eventbridge by JRP - Version {}".format(version))
    logging.info("Log level set to: {}".format(getattr(settings, 'loglevel', 'INFO')))
    start_prometheus_server()
    listen_and_relay(settings.resend_dest, settings.resend_port, settings.resend_path, settings.listen_port)
