"""Frontend module for NRK Radio Card."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from ..const import DOMAIN, VERSION

_LOGGER = logging.getLogger(__name__)

_JS_FILENAME = "nrk-radio-card.js"
_STATIC_PATH = f"/{DOMAIN}/{_JS_FILENAME}"


async def async_setup_frontend(hass: HomeAssistant) -> None:
    """Register the frontend module.

    Must be called from the integration-level async_setup(), not from
    async_setup_entry(), so the static path is registered before HA starts
    serving HTTP requests.
    """
    js_path = Path(__file__).parent / _JS_FILENAME

    if not js_path.exists():
        _LOGGER.error("Card JS file not found at %s", js_path)
        return

    # async_register_static_paths is the non-blocking replacement for the
    # deprecated register_static_path. cache_headers=False ensures the
    # browser always revalidates the file rather than serving a stale copy.
    await hass.http.async_register_static_paths(
        [StaticPathConfig(_STATIC_PATH, str(js_path), cache_headers=False)]
    )

    _LOGGER.debug("Registered static path %s -> %s", _STATIC_PATH, js_path)

    # Version in the URL acts as a cache-buster when the integration is updated.
    card_url = f"{_STATIC_PATH}?v={VERSION}"
    add_extra_js_url(hass, card_url)

    _LOGGER.info("NRK Radio Card registered at %s", card_url)
