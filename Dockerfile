FROM python:3.7.3-alpine

RUN apk add --no-cache --virtual .build-deps gcc musl-dev

WORKDIR /env/init_ceremony
ADD ./init_ceremony/requirements.txt .
RUN pip install -r ./requirements.txt
RUN apk del .build-deps gcc musl-dev
COPY ./init_ceremony /init_ceremony

ENTRYPOINT ["/init_ceremony/main.py"]
CMD []

