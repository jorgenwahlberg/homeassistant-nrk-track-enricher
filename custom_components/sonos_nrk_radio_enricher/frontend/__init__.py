"""Frontend module for NRK Radio Card."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.core import HomeAssistant

from ..const import DOMAIN, VERSION

_LOGGER = logging.getLogger(__name__)

_JS_FILENAME = "nrk-radio-card.js"
_STATIC_PATH = f"/{DOMAIN}/{_JS_FILENAME}"


async def async_setup_frontend(hass: HomeAssistant) -> None:
    """Register the frontend module.

    This registers the custom Lovelace card with Home Assistant's frontend.
    The card will be automatically available in the Lovelace card picker.
    """
    js_path = Path(__file__).parent / _JS_FILENAME

    _LOGGER.debug("Card JS file path: %s", js_path)

    if not js_path.exists():
        _LOGGER.error("Card JS file not found at %s", js_path)
        return

    # Register the file as a static path — HA serves it directly from disk.
    # This is more reliable than a dynamic view and survives HA restarts cleanly.
    hass.http.register_static_path(_STATIC_PATH, str(js_path), cache_headers=False)

    _LOGGER.debug("Registered static path %s -> %s", _STATIC_PATH, js_path)

    # Use only the version string in the URL so the URL is stable across
    # restarts of the same version. The browser will always revalidate
    # because cache_headers=False disables caching on the static path.
    card_url = f"{_STATIC_PATH}?v={VERSION}"

    _LOGGER.debug("Registering NRK Radio Card at %s", card_url)

    try:
        add_extra_js_url(hass, card_url)
        _LOGGER.info("NRK Radio Card registered successfully at %s", card_url)
    except Exception as err:
        _LOGGER.error("Failed to register NRK Radio Card: %s", err)
        raise
