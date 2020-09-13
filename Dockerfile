ARG BASE_IMAGE
FROM ${BASE_IMAGE}

WORKDIR /fyf

COPY requirements.txt /fyf
RUN pip --no-cache-dir install -r requirements.txt

COPY fyf /fyf

CMD ["python", "server.py"]