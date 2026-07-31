FROM --platform=linux/amd64 ghcr.io/engineer-man/piston:latest

RUN mkdir -p /piston/packages && \
    sed -i 's|deb.debian.org|archive.debian.org|g' /etc/apt/sources.list && \
    sed -i 's|security.debian.org|archive.debian.org/debian-security|g' /etc/apt/sources.list && \
    sed -i '/buster-updates/d' /etc/apt/sources.list && \
    apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

COPY install-packages.sh /usr/local/bin/install-packages.sh
COPY piston-entrypoint.sh /usr/local/bin/piston-entrypoint.sh
RUN chmod +x /usr/local/bin/install-packages.sh /usr/local/bin/piston-entrypoint.sh

EXPOSE 2000

# piston-entrypoint.sh applies resource caps then delegates to install-packages.sh
CMD ["/usr/local/bin/piston-entrypoint.sh"]
