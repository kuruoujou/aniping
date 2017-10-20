FROM python:3.5-alpine
MAINTAINER Spencer Julian <helloThere@spencerjulian.com>

COPY . /tmp

RUN apk add --no-cache --update nginx supervisor python3-dev build-base \
                                linux-headers pcre-dev curl && \
    rm -rf /var/cache/apk/* && \
    chown -R nginx:www-data /var/lib/nginx && \
    (while true; do pip install --no-cache-dir --disable-pip-version-check --verbose uwsgi && break; done) && \
    pip install -r /tmp/requirements.txt && \
    mkdir -p /etc/uwsgi/apps-enabled && \
    mkdir -p /etc/supervisor/ && \
    cp -r /tmp/aniping /app && \
    cp /tmp/docker-config/nginx.conf /etc/nginx/nginx.conf && \
    cp /tmp/docker-config/nginx-default.conf /etc/nginx/conf.d/default.conf && \
    cp /tmp/docker-config/uwsgi.ini /etc/uwsgi/apps-enabled/uwsgi.ini && \
    cp /tmp/docker-config/supervisord.conf /etc/supervisor/supervisord.conf && \
    mkdir -p /app/db && \
    mkdir -p /app/static/images/cache && \
    chown -R nginx:www-data /app

VOLUME ["/app/config", "/app/db", "/app/static/images/cache"]

EXPOSE 80

CMD ["supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
