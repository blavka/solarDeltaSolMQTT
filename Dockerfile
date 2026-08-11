FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY solarDeltaSolMQTT ./solarDeltaSolMQTT
RUN pip install --no-cache-dir . \
    && groupadd --gid 10002 deltasol \
    && useradd --uid 10002 --gid 10002 --create-home deltasol

USER deltasol
ENTRYPOINT ["solarDeltaSolMQTT"]
