"""Frontend module for NRK Radio Card."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later

from ..const import DOMAIN, VERSION

_LOGGER = logging.getLogger(__name__)

_JS_FILENAME = "nrk-radio-card.js"
_URL_BASE = f"/{DOMAIN}"
_CARD_URL = f"{_URL_BASE}/{_JS_FILENAME}"


async def async_setup_frontend(hass: HomeAssistant) -> None:
    """Register the static HTTP path for the card JS.

    Must be called from async_setup() so the path is available before HA
    starts serving requests. Lovelace resource registration is deferred to
    after EVENT_HOMEASSISTANT_STARTED (see __init__.py) because the Lovelace
    storage collection is not loaded yet during async_setup().
    """
    js_path = Path(__file__).parent / _JS_FILENAME

    if not js_path.exists():
        _LOGGER.error("Card JS file not found at %s", js_path)
        return

    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(_URL_BASE, str(Path(__file__).parent), cache_headers=False)]
        )
    except RuntimeError:
        # Path already registered (e.g. during development reload)
        _LOGGER.debug("Static path %s already registered", _URL_BASE)

    _LOGGER.debug("Registered static path %s -> %s", _URL_BASE, Path(__file__).parent)


async def async_register_lovelace_resource(hass: HomeAssistant) -> None:
    """Register (or update) the card as a persistent Lovelace resource.

    This must run after EVENT_HOMEASSISTANT_STARTED so that the Lovelace
    storage collection has finished loading. Registering here ensures the
    resource persists across page loads and hard browser reloads, unlike
    add_extra_js_url which is session-only.
    """
    lovelace = hass.data.get("lovelace")
    if lovelace is None:
        _LOGGER.warning("Lovelace not available, card resource not registered")
        return

    mode = getattr(lovelace, "mode", getattr(lovelace, "resource_mode", "yaml"))
    if mode != "storage":
        _LOGGER.info(
            "Lovelace is in %s mode. Add the card resource manually:\n"
            "  url: %s?v=%s\n  type: module",
            mode, _CARD_URL, VERSION,
        )
        return

    async def _check_and_register(_now: Any = None) -> None:
        if not lovelace.resources.loaded:
            _LOGGER.debug("Lovelace resources not loaded yet, retrying in 5s")
            async_call_later(hass, 5, _check_and_register)
            return

        desired_url = f"{_CARD_URL}?v={VERSION}"
        existing = [
            r for r in lovelace.resources.async_items()
            if r["url"].split("?")[0] == _CARD_URL
        ]

        if existing:
            resource = existing[0]
            if resource["url"] != desired_url:
                _LOGGER.info("Updating NRK Radio Card resource to %s", desired_url)
                await lovelace.resources.async_update_item(
                    resource["id"],
                    {"res_type": "module", "url": desired_url},
                )
            else:
                _LOGGER.debug("NRK Radio Card resource already up to date")
        else:
            _LOGGER.info("Registering NRK Radio Card resource at %s", desired_url)
            await lovelace.resources.async_create_item(
                {"res_type": "module", "url": desired_url}
            )

    await _check_and_register()
