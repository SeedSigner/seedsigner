# Same CPython as .python-version / SeedSigner OS
FROM python:3.12.10-bookworm

# zbar (QR decoding) and git (pyproject pins pyzbar/urtypes by git commit)
RUN apt-get -qq update
RUN apt-get -y -qq install zbar-tools git

# uv, pinned by version and image digest
COPY --from=ghcr.io/astral-sh/uv:0.12.13@sha256:b485bd65cc2cf1c9a93b3554012c9c3778cf7b1b5fd3d3096ce9e1226c97e1e6 /uv /uvx /bin/

# Keep the venv outside the repository bind mount so it survives mounting the checkout.
# Always use the image's interpreter; never download a managed CPython.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV UV_PYTHON_DOWNLOADS=never
ENV PATH="/opt/venv/bin:${PATH}"

# Pre-install the locked dependencies (runtime + default `dev` group) into the image;
# docker/setup.sh adds the editable project install once the checkout is mounted.
WORKDIR /build
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-install-project
RUN rm -rf /build

# set working dir
WORKDIR /seedsigner
