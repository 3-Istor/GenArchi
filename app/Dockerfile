# Image unique de l'application (local et Platform 3). Non-root, dépendances figées par uv.lock.
FROM mirror.gcr.io/library/python:3.13-slim AS build
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
RUN pip install --no-cache-dir uv==0.11.21
WORKDIR /src
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --all-extras --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev --all-extras

FROM mirror.gcr.io/library/python:3.13-slim
ARG APP_VERSION=dev
ENV PATH=/src/.venv/bin:$PATH PYTHONUNBUFFERED=1 APP_VERSION=${APP_VERSION} PORT=8080
RUN useradd --system --uid 10001 --home-dir /nonexistent genarchi \
    && mkdir -p /data/tickets && chown 10001 /data/tickets
COPY --from=build /src /src
COPY front /front
USER 10001
EXPOSE 8080
ENTRYPOINT ["genarchi"]
CMD ["serve-api"]
