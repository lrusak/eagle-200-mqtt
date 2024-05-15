FROM python:3.8-alpine

WORKDIR /usr/src/app

RUN apk add --no-cache --virtual .build-deps gcc libc-dev libxslt-dev && \
    apk add --no-cache libxslt && \
    pip install --no-cache-dir lxml && \
    apk del .build-deps

RUN pip install --no-cache-dir https://github.com/lrusak/py-eagle-200/archive/0.1.tar.gz

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY eagle-200-mqtt.py ./

ENTRYPOINT [ "python", "./eagle-200-mqtt.py" ]
