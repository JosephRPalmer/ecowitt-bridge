FROM python:3.9

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app /app

ENV LISTEN_PORT=8082
ENV PROM_PORT=9110
ENV RESEND_PORT=8080

EXPOSE $PROM_PORT
EXPOSE 8082

CMD python app.py