FROM python:3.9

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app /app

ENV LISTEN_PORT=8082
ENV PROM_PORT=9110

EXPOSE $LISTEN_PORT
EXPOSE $PROM_PORT

CMD python -m flask run --host=0.0.0.0 --port=$LISTEN_PORT