FROM python:3.13-alpine
WORKDIR /code
COPY src ./src/
COPY pyproject.toml README.md ./
RUN pip install .
RUN mkdir -p /root/.biokb/taxtree
CMD ["fastapi", "run","src/biokb_taxtree/api/main.py"]
