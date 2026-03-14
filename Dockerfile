FROM python:3.12-slim

LABEL maintainer="Pantoll Ventures <contact@pantollventures.com>"
LABEL org.opencontainers.image.source="https://github.com/GDWN-BLDR/stateweave"
LABEL org.opencontainers.image.description="StateWeave MCP Server — git for agent brains"
LABEL org.opencontainers.image.licenses="Apache-2.0"

WORKDIR /app

# Install dependencies first (Docker layer caching)
COPY pyproject.toml README.md LICENSE ./
RUN pip install --no-cache-dir -e ".[server]" 2>/dev/null || pip install --no-cache-dir -e "."

# Copy source
COPY stateweave/ stateweave/

# Verify installation
RUN python -c "from stateweave import __version__; print(f'StateWeave v{__version__} installed')"

EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import stateweave; print('ok')" || exit 1

# Default: run the MCP server over stdio
# Override to run REST API: docker run -p 8080:8080 stateweave python -m stateweave.rest_api
ENTRYPOINT ["python", "-m", "stateweave.mcp_server"]
