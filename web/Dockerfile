FROM tutum/hello-world
MAINTAINER Chris Chandler <chris.chandler18@t-mobile.com>

ENV CONSUL_VERSION=1.2.1

RUN apk add --update python py-pip curl util-linux && \
    curl -sSLo /tmp/consul.zip https://releases.hashicorp.com/consul/{$CONSUL_VERSION}/consul_${CONSUL_VERSION}_linux_amd64.zip && \
    unzip -d /bin /tmp/consul.zip && \
    rm /tmp/consul.zip && \
    apk del curl && \
    addgroup consul && \
    adduser -D -g "" -s /bin/sh -G consul consul && \
    mkdir -p /data/consul && \
    chown -R consul:consul /data/consul && \
    rm -rf /var/cache/apk/*

RUN pip install supervisor

COPY supervisord.conf /etc/supervisord.conf

RUN mkdir -p /etc/consul.d/client

COPY consul-services.json /etc/consul.d/client/consul-service.json

VOLUME ["/data/consul"]

ENTRYPOINT ["supervisord", "--nodaemon", "--configuration", "/etc/supervisord.conf"]