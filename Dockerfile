FROM openscad/openscad:trixie.2026-10-12@sha256:4098a7c2c37d5a9110121635a568e6596b8619362ced5c84cc67f47d395e7fd0
USER root
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates xvfb xauth python3 python3-venv \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements-http.txt ./
RUN python3 -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir --require-hashes -r requirements-http.txt
COPY src ./src
COPY models ./models
COPY LICENSE REDISTRIBUTION.md ./
RUN useradd -u 568 -M app
USER 568
# Service mode renders in place: no Docker socket, and only the artifacts dir is writable.
ENV PYTHONPATH=/app/src SCAD_MCP_TRANSPORT=http SCAD_RENDERER=local SCAD_ARTIFACTS_DIR=/artifacts SCAD_MCP_PORT=8781 HOME=/tmp
EXPOSE 8781
CMD ["/opt/venv/bin/python", "-m", "scad_mcp.server"]
