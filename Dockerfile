# ---------- Stage 1: build nsjail ----------
FROM debian:bookworm AS nsjail-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates git make g++ pkg-config \
    libprotobuf-dev protobuf-compiler libnl-route-3-dev libcap-dev libcap-ng-dev libssl-dev libseccomp-dev \
    flex bison \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /src
RUN git clone --depth=1 https://github.com/google/nsjail.git
# Build nsjail (static often still links a few libs on some platforms; we’ll ship runtime libs too)
RUN make -C nsjail STATIC=1

# ---------- Stage 2: app runtime ----------
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Install runtime libs nsjail may still look for at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libprotobuf32 \
    libnl-route-3-200 \
    libcap2 \
    libcap-ng0 \
    libssl3 \
    libseccomp2 \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Copy the nsjail binary built in stage 1
COPY --from=nsjail-builder /src/nsjail/nsjail /usr/local/bin/nsjail

# Create non-root user
RUN adduser --disabled-password --gecos "" --uid 65532 appuser

# Python deps
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# App source
COPY app.py /app/app.py
COPY runner.py /app/runner.py
COPY policy.kafel /app/policy.kafel

# Permissions
RUN mkdir -p /tmp/safe_exec && chown -R appuser:appuser /app /tmp/safe_exec

USER appuser
EXPOSE 8080
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:8080", "app:app"]
