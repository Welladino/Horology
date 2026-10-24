ARG HERMES_VERSION=v0.22.5
FROM nousresearch/hermes-agent:${HERMES_VERSION}

# Modal is an optional Hermes dependency and is not bundled in the upstream
# image. Install the exact version required by this Hermes release into its
# application virtual environment so Explorer survives container recreation.
RUN UV_BIN="$(find /opt/hermes/tools -maxdepth 2 -type f -name uv -perm -111 | head -n 1)" \
    && test -n "$UV_BIN" \
    && "$UV_BIN" pip install --python /opt/hermes/.venv/bin/python modal==1.5.5
RUN /opt/hermes/.venv/bin/python -c "import importlib.metadata as metadata; assert metadata.version('modal') == '1.5.5'"
