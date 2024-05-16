FROM python:3.12-alpine

RUN apk add --no-cache git

WORKDIR /usr/src/app

RUN pip install --no-cache-dir poetry

COPY pyproject.toml /usr/src/app/
COPY README.md /usr/src/app/
COPY src /usr/src/app/src

RUN poetry install

ENTRYPOINT [ "poetry", "run", "eagle-200-mqtt" ]
