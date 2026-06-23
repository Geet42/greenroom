FROM --platform=linux/amd64 ghcr.io/engineer-man/piston:latest

COPY install-packages.sh /usr/local/bin/install-packages.sh
RUN chmod +x /usr/local/bin/install-packages.sh

EXPOSE 2000

# install-packages.sh installs runtimes on first boot then re-execs piston
CMD ["/usr/local/bin/install-packages.sh"]
