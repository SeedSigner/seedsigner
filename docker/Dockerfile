FROM python:3.10-bullseye

# install zbar dependencyy
RUN apt-get -qq update
RUN apt-get -y -qq install zbar-tools

COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /uvx /bin/

# Keep the venv outside the repository bind mount.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

WORKDIR /build
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --group l10n --no-install-project
RUN rm -rf /build

# set working dir
WORKDIR /seedsigner
