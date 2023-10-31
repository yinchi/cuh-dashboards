FROM python:3.11-slim

RUN apt update && apt upgrade -y
COPY hpath/requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

COPY /hpath /app/hpath

WORKDIR /app
CMD python -m hpath.restful.server
