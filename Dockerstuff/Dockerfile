#FROM python:3.7.0a2-alpine3.6
FROM python:3.8.1-slim-buster

RUN pip install pulp pyomo ortools boto3

COPY task.py /tmp

#Dummy main py, real one is downloaded at runtime from s3 as source.zip
COPY main.py /tmp
CMD python /tmp/task.py