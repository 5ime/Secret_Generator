FROM python:3.7.2-slim

WORKDIR /app

RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

RUN pip install --upgrade pip

RUN pip install --no-cache-dir flask pillow

COPY ./src/ /app
COPY ./service/docker-entrypoint.sh /

ENTRYPOINT ["/bin/bash","/docker-entrypoint.sh"]