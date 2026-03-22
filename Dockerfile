FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Create app user
RUN addgroup --system --gid 1000 appuser && \
    adduser --system --uid 1000 --ingroup appuser appuser

WORKDIR /app
COPY --chown=appuser:appuser src/main.py .
# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY tests/ ./tests/

# Set environment variables for uv
ENV UV_CACHE_DIR=/app/.uv-cache
ENV UV_NO_CACHE=1

# Install dependencies
RUN uv sync --frozen

# Change ownership
RUN chown -R appuser:appuser /app

USER appuser

# Expose port
EXPOSE 8000

# Run the application
CMD ["uv", "run", "uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
