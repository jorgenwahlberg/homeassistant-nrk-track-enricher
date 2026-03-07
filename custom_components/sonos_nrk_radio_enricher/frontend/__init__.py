"""Frontend module for NRK Radio Card."""
from __future__ import annotations

import logging
from pathlib import Path

from aiohttp import web
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from ..const import DOMAIN, VERSION

_LOGGER = logging.getLogger(__name__)


class NRKCardJSView(HomeAssistantView):
    """View to serve the NRK Radio Card JavaScript file."""

    requires_auth = False
    url = f"/{DOMAIN}/nrk-radio-card.js"
    name = f"{DOMAIN}:card-js"

    def __init__(self, js_path: Path) -> None:
        """Initialize the view."""
        self.js_path = js_path

    async def get(self, request):
        """Serve the JavaScript file."""
        _LOGGER.debug("Serving NRK Radio Card JS from %s", self.js_path)

        if not self.js_path.exists():
            _LOGGER.error("Card JS file not found at %s", self.js_path)
            return web.Response(status=404, text="Card file not found")

        try:
            content = self.js_path.read_text(encoding="utf-8")
            return web.Response(
                text=content,
                content_type="application/javascript",
                charset="utf-8",
                headers={"Cache-Control": "no-cache"}
            )
        except Exception as err:
            _LOGGER.error("Error reading card JS file: %s", err)
            return web.Response(status=500, text="Error reading card file")


async def async_setup_frontend(hass: HomeAssistant) -> None:
    """Register the frontend module.

    This registers the custom Lovelace card with Home Assistant's frontend.
    The card will be automatically available in the Lovelace card picker.
    """
    # Get the path to our JavaScript file
    js_path = Path(__file__).parent / "nrk-radio-card.js"

    _LOGGER.debug("Card JS file path: %s", js_path)
    _LOGGER.debug("Card JS file exists: %s", js_path.exists())

    # Register a view to serve the JavaScript file
    view = NRKCardJSView(js_path)
    hass.http.register_view(view)

    _LOGGER.debug("Registered card view at %s", view.url)

    # Register the card with the frontend
    card_url = f"{view.url}?v={VERSION}"

    _LOGGER.debug("Registering NRK Radio Card at %s", card_url)

    # Add the card to Lovelace
    add_extra_js_url(hass, card_url)

    _LOGGER.info("NRK Radio Card registered successfully at %s", card_url)
