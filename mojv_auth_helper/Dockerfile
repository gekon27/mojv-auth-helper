ARG BUILD_FROM=ghcr.io/home-assistant/base-python:3.13-alpine3.24
FROM ${BUILD_FROM}

ARG BUILD_VERSION
ARG BUILD_ARCH

ENV MOJV_HELPER_VERSION="${BUILD_VERSION}"
ENV DISPLAY=":99"

RUN apk add --no-cache \
      chromium \
      chromium-chromedriver \
      xvfb \
      nss \
      freetype \
      harfbuzz \
      font-noto \
    && python3 -m pip install --no-cache-dir \
      aiohttp==3.12.15 \
      selenium==4.48.0

COPY rootfs /
RUN chmod a+x /etc/services.d/mojv-auth/run

LABEL \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="app" \
  io.hass.arch="${BUILD_ARCH}"
