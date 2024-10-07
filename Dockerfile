FROM python:3.10.13-alpine3.17
LABEL maintainer="Walexero"

ENV PYTHONUNBUFFERED 1

COPY ./requirements.txt /tmp/requirements.txt
COPY ./requirements.dev.txt /tmp/requirements.dev.txt
COPY ./scripts /scripts

ARG DEV=false
RUN \
    python -m venv /py && \
    /py/bin/python -m pip install --upgrade pip && \
    apk add --update --no-cache postgresql-client jpeg-dev python3-dev pcre-dev && \
    apk add --update --no-cache --virtual .tmp-build-deps \
    build-base postgresql-dev  musl-dev zlib zlib-dev linux-headers
RUN \
    /py/bin/pip install -r /tmp/requirements.txt && \
    if [ $DEV = "true" ] ; \
    then /py/bin/pip install -r /tmp/requirements.dev.txt ; \
    fi && \
    rm -rf /tmp && \
    apk del .tmp-build-deps && \
    adduser \
    --disabled-password \
    --no-create-home \
    django-user && \
    mkdir -p /vol/journalweb/media && \
    mkdir -p /vol/journalweb/static

COPY ./app /app

RUN chown -R django-user:django-user /vol && \
    chown -R django-user:django-user /app && \
    chown -R django-user:django-user /var && \
    chmod -R 755 /vol && \
    chmod -R 755 /app && \
    chmod -R 755 /var && \
    chmod -R +x /scripts && \
    chown django-user:django-user /scripts/run.sh && \
    chmod +x /scripts/run.sh

WORKDIR /app
EXPOSE 9008

ENV PATH="/scripts:/py/bin:$PATH"

USER django-user

CMD ["run.sh"]
