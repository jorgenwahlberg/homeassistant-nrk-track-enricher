"""The Sonos NRK Radio Enricher integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.core import CoreState, HomeAssistant

from .const import CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, DOMAIN
from .coordinator import NRKDataCoordinator
from .frontend import async_register_lovelace_resource, async_setup_frontend

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration.

    Registers the static HTTP path immediately (needed before HTTP serving
    starts), then defers Lovelace resource registration until after HA has
    fully started (Lovelace storage is not loaded during async_setup).
    """
    await async_setup_frontend(hass)

    async def _register_lovelace(_event=None) -> None:
        await async_register_lovelace_resource(hass)

    if hass.state == CoreState.running:
        await _register_lovelace()
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _register_lovelace)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sonos NRK Radio Enricher from a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry

    Returns:
        True if setup was successful

    """
    _LOGGER.info("Starting Sonos NRK Radio Enricher integration setup")
    hass.data.setdefault(DOMAIN, {})

    # Get configuration
    update_interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
    _LOGGER.debug("Update interval: %s seconds", update_interval)

    # Create coordinator
    coordinator = NRKDataCoordinator(hass, update_interval)
    _LOGGER.debug("Coordinator created")

    # Store coordinator
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Perform initial refresh
    _LOGGER.debug("Performing initial coordinator refresh")
    await coordinator.async_config_entry_first_refresh()

    # Set up platforms
    _LOGGER.debug("Setting up platforms: %s", PLATFORMS)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register update listener for options changes
    entry.async_on_unload(entry.add_update_listener(update_listener))

    _LOGGER.info("Sonos NRK Radio Enricher integration setup complete")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry

    Returns:
        True if unload was successful

    """
    # Unload platforms
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update.

    Args:
        hass: Home Assistant instance
        entry: Config entry

    """
    await hass.config_entries.async_reload(entry.entry_id)
