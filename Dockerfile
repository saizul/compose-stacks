FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY pyproject.toml setup.py MANIFEST.in README.md LICENSE ./
COPY src ./src
COPY stacks ./stacks
COPY templates ./templates
RUN pip install . && useradd --system --uid 10001 app && rm -rf /app/build
USER app
WORKDIR /work
ENTRYPOINT ["compose-stacks"]
CMD ["--help"]
