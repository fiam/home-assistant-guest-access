ARG HA_VERSION=2026.10.4
FROM homeassistant/home-assistant:${HA_VERSION}
RUN uv pip install --system --index https://pypi.org/simple --constraint /usr/src/homeassistant/homeassistant/package_constraints.txt pytest==8.4.2 pytest-asyncio==1.2.0
WORKDIR /work
ENV PYTHONDONTWRITEBYTECODE=1
ENTRYPOINT ["python", "-m", "pytest", "-p", "no:cacheprovider"]
