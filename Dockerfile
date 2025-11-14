FROM python:3.14-alpine

WORKDIR /ecowitt_bridge

COPY pyproject.toml .

RUN pip install --no-cache-dir .

COPY ecowitt_bridge /ecowitt_bridge

CMD python ecowitt_bridge.py
