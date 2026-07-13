FROM python:3.12.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/nac/src

WORKDIR /opt/nac

COPY deploy/runtime/onprem/nac-bff/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --requirement /tmp/requirements.txt \
    && rm /tmp/requirements.txt

COPY src/nac_bff /opt/nac/src/nac_bff

USER 65532:65532
EXPOSE 8080

# The base image is deliberately fail-closed. A deployment composition must
# replace this factory with one that injects validated Entra claims plus the
# server-side access-decision and raw Graph REST v1.0 ports.
CMD ["uvicorn", "nac_bff.fastapi_adapter:create_unconfigured_app", "--factory", "--host", "0.0.0.0", "--port", "8080", "--no-access-log"]
