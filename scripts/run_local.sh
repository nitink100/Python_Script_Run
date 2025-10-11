#!/usr/bin/env bash
set -euo pipefail
docker build -t safe-exec .
docker run --rm -p 8080:8080 safe-exec