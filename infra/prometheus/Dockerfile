# Bakes the live-scrape config into the image so no volume/Azure Files
# mount is needed on Container Apps — same pattern as backend/Dockerfile,
# just for Prometheus instead of the app itself.
FROM prom/prometheus:latest
COPY prometheus.live.yml /etc/prometheus/prometheus.yml
