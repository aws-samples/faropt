#FROM python:3.7.0a2-alpine3.6
FROM python:3.8.1-slim-buster

RUN pip install pulp pyomo ortools boto3 deap numpy pandas

COPY task.py /tmp

#Dummy main py, real one is downloaded at runtime from s3 as source.zip
COPY main.py /tmp

#common utils
COPY utils.py /tmp

RUN apt-get update && apt-get install -y libaio1 wget unzip

# Install Julia and JUMP
# COPY jill.sh /tmp

# RUN chmod +x /tmp/jill.sh

# RUN bash /tmp/jill.sh -y

# RUN julia -e 'using Pkg; Pkg.add(["JuMP","GLPKMathProgInterface","SCS","LinearAlgebra","Test"])'

# RUN julia --version

CMD python /tmp/task.py