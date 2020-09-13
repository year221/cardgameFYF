ARG BASE_IMAGE
FROM ${BASE_IMAGE}

WORKDIR /fyf
COPY fyf /fyf
COPY requirements.txt /fyf

RUN pip --no-cache-dir install -r requirements.txt

CMD ["python", "server.py"]