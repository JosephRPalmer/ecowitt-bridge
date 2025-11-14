FROM python:3.14-alpine

WORKDIR /ecowitt-bridge

COPY pyproject.toml .

RUN pip install --no-cache-dir .

COPY ecowitt-bridge /ecowitt-bridge

CMD python ecowitt-bridge.py
