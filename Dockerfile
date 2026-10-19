FROM cgr.dev/chainguard/wolfi-base:latest AS runtime

ARG TZ=Europe/Berlin
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=${TZ} \
    PATH="/app/venv/bin:${PATH}"

# Keep Python's major/minor version stable and install only runtime libraries.
# Retain APK metadata so scanners can inventory every OS package.
RUN apk add --no-cache python-3.12 libstdc++ tzdata \
    && addgroup -S app \
    && adduser -S -G app -h /app app

WORKDIR /app

FROM runtime AS dependencies
COPY requirements.txt .
RUN python -m venv /app/venv \
    && /app/venv/bin/python -m pip install --no-cache-dir --disable-pip-version-check \
       --only-binary=:all: -r requirements.txt

FROM runtime AS final
COPY --from=dependencies /app/venv /app/venv
COPY app.py conversion_worker.py ./
COPY static ./static
COPY templates ./templates

# Application and dependencies remain root-owned and read-only for the service.
USER app
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/healthz', timeout=3)"]

CMD ["python", "-m", "gunicorn", "--bind=0.0.0.0:5000", "--workers=1", "--threads=2", "--timeout=300", "--access-logfile=-", "app:app"]
