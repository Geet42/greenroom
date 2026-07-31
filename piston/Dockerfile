FROM --platform=linux/amd64 ghcr.io/engineer-man/piston:latest

RUN mkdir -p /piston/packages && \
    apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

COPY install-packages.sh /usr/local/bin/install-packages.sh
COPY piston-entrypoint.sh /usr/local/bin/piston-entrypoint.sh
RUN chmod +x /usr/local/bin/install-packages.sh /usr/local/bin/piston-entrypoint.sh

EXPOSE 2000

# piston-entrypoint.sh applies resource caps then delegates to install-packages.sh
CMD ["/usr/local/bin/piston-entrypoint.sh"]
