FROM bitnami/spark:3.5.5

USER root
WORKDIR /opt/spark/app

COPY src/job.py /opt/spark/app/job.py
COPY data/orders.csv /opt/spark/app/data/orders.csv

RUN mkdir -p /opt/spark/app/data && chmod -R 755 /opt/spark/app

USER 1001
