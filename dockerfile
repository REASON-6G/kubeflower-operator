FROM python:3.9.8-slim-bullseye
RUN apt-get update && apt-get install -y iputils-ping
WORKDIR /app
RUN /usr/local/bin/python -m pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple
COPY ./src src
RUN mkdir data
CMD ["/bin/sh", "-c", "while sleep 1000; do :; done"]