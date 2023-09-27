FROM python:3.11-slim

RUN apt update && apt upgrade -y
COPY docker-requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

WORKDIR /app
CMD python -m hpath.restful.server
