FROM python:3.11-slim

RUN apt update && apt upgrade -y
COPY sensors/requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

WORKDIR /app/sensors
CMD python -m main
