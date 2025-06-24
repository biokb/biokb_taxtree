FROM ghcr.io/astral-sh/uv:python3.12-alpine
WORKDIR /app
COPY src/ ./src/
COPY README.md .
COPY pyproject.toml .
RUN pip install .
CMD ["uvicorn", "src.biokb_taxtree.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
