"""Sensor platform for Sonos NRK Radio Enricher."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_IDLE
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_DESCRIPTION,
    ATTR_ENRICHED_ARTIST,
    ATTR_ENRICHED_TITLE,
    ATTR_IMAGE_URL,
    ATTR_IS_NRK,
    ATTR_PROGRAM_TITLE,
    ATTR_STATION_NAME,
    ATTR_TRACK_ARTIST,
    ATTR_TRACK_TITLE,
    DOMAIN,
)
from .coordinator import NRKDataCoordinator
from .nrk_stations import NRKStation, get_station_by_uri, is_nrk_radio

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sonos NRK sensor entities.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        async_add_entities: Callback to add entities

    """
    coordinator: NRKDataCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Discover all Sonos media_player entities
    sonos_entities = []
    for state in hass.states.async_all("media_player"):
        # Check if it's a Sonos entity
        # The Sonos integration creates entities with specific attributes
        if _is_sonos_entity(state.entity_id, state.attributes):
            sonos_entities.append(state.entity_id)

    _LOGGER.info("Discovered %d Sonos media player entities", len(sonos_entities))

    # Create a monitor sensor for each Sonos entity
    sensors = [
        SonosNRKMonitorSensor(hass, coordinator, entity_id)
        for entity_id in sonos_entities
    ]

    async_add_entities(sensors)


def _is_sonos_entity(entity_id: str, attributes: dict[str, Any]) -> bool:
    """Determine if an entity is a Sonos media player.

    Args:
        entity_id: Entity ID to check
        attributes: Entity attributes

    Returns:
        True if entity is a Sonos player

    """
    # Check for Sonos-specific attributes
    # The Sonos integration typically includes these markers
    if "source_list" in attributes:
        # Additional validation: check device info or manufacturer
        if device_info := attributes.get("device_info"):
            manufacturer = device_info.get("manufacturer", "").lower()
            if "sonos" in manufacturer:
                return True

    # Fallback: check entity_id pattern (less reliable)
    # Some Sonos integrations use specific naming
    if "sonos" in entity_id.lower():
        _LOGGER.debug("Potential Sonos entity detected by name: %s", entity_id)
        return True

    return False


class SonosNRKMonitorSensor(CoordinatorEntity[NRKDataCoordinator], SensorEntity):
    """Sensor that monitors a Sonos media player for NRK radio playback."""

    _attr_has_entity_name = True
    _attr_translation_key = "nrk_enricher"

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: NRKDataCoordinator,
        sonos_entity_id: str,
    ) -> None:
        """Initialize the sensor.

        Args:
            hass: Home Assistant instance
            coordinator: Data update coordinator
            sonos_entity_id: Entity ID of the Sonos player to monitor

        """
        super().__init__(coordinator)
        self.hass = hass
        self._sonos_entity_id = sonos_entity_id
        self._current_station: NRKStation | None = None
        self._is_nrk_radio = False

        # Generate unique entity_id based on Sonos entity
        sonos_name = sonos_entity_id.replace("media_player.", "")
        self._attr_unique_id = f"{sonos_name}_nrk_enricher"
        self.entity_id = f"sensor.{sonos_name}_nrk"

        # Set device info to link to the Sonos device
        if sonos_state := hass.states.get(sonos_entity_id):
            if device_id := sonos_state.attributes.get("device_id"):
                self._attr_device_info = {
                    "identifiers": {(DOMAIN, device_id)},
                }

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to hass."""
        await super().async_added_to_hass()

        # Subscribe to state changes of the parent Sonos entity
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._sonos_entity_id],
                self._async_sonos_state_changed,
            )
        )

        # Initial state check
        await self._async_update_from_sonos()

    @callback
    def _async_sonos_state_changed(
        self, event: Event[EventStateChangedData]
    ) -> None:
        """Handle Sonos entity state changes.

        Args:
            event: State change event

        """
        self.hass.async_create_task(self._async_update_from_sonos())

    async def _async_update_from_sonos(self) -> None:
        """Update sensor state based on current Sonos state."""
        sonos_state = self.hass.states.get(self._sonos_entity_id)
        if not sonos_state:
            return

        # Get media_content_id (the URI being played)
        media_content_id = sonos_state.attributes.get("media_content_id", "")

        # Check if NRK radio is playing
        if is_nrk_radio(media_content_id):
            station = get_station_by_uri(media_content_id)
            if station:
                self._is_nrk_radio = True

                # Register station with coordinator if changed
                if self._current_station != station:
                    if self._current_station:
                        self.coordinator.unregister_station(self._current_station)
                    self.coordinator.register_station(station)
                    self._current_station = station
                    # Trigger immediate coordinator refresh
                    await self.coordinator.async_request_refresh()
        else:
            # Not playing NRK
            if self._current_station:
                self.coordinator.unregister_station(self._current_station)
                self._current_station = None
            self._is_nrk_radio = False

        # Update entity state
        self.async_write_ha_state()

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        sonos_state = self.hass.states.get(self._sonos_entity_id)
        if not sonos_state:
            return STATE_IDLE

        if self._is_nrk_radio and self._current_station:
            # Return enriched title when playing NRK
            track_info = self.coordinator.get_track_info(self._current_station)
            if track_info:
                return track_info.enriched_title
            return "NRK Radio"
        else:
            # Return original Sonos media title when not NRK
            return sonos_state.attributes.get("media_title", STATE_IDLE)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        sonos_state = self.hass.states.get(self._sonos_entity_id)
        if not sonos_state:
            return {}

        attributes = {
            ATTR_IS_NRK: self._is_nrk_radio,
            "sonos_entity_id": self._sonos_entity_id,
        }

        if self._is_nrk_radio and self._current_station:
            # Add enriched NRK data
            track_info = self.coordinator.get_track_info(self._current_station)
            if track_info:
                attributes.update(
                    {
                        ATTR_STATION_NAME: track_info.station_name,
                        ATTR_PROGRAM_TITLE: track_info.program_title,
                        ATTR_TRACK_TITLE: track_info.track_title,
                        ATTR_TRACK_ARTIST: track_info.track_artist,
                        ATTR_ENRICHED_ARTIST: track_info.enriched_artist,
                        ATTR_ENRICHED_TITLE: track_info.enriched_title,
                        ATTR_DESCRIPTION: track_info.description,
                        ATTR_IMAGE_URL: track_info.image_url,
                    }
                )
            else:
                # NRK detected but no data yet
                attributes[ATTR_STATION_NAME] = self._current_station["name"]
        else:
            # Pass through original Sonos attributes
            attributes.update(
                {
                    "media_title": sonos_state.attributes.get("media_title"),
                    "media_artist": sonos_state.attributes.get("media_artist"),
                    "media_album_name": sonos_state.attributes.get(
                        "media_album_name"
                    ),
                    "entity_picture": sonos_state.attributes.get("entity_picture"),
                }
            )

        return attributes

    @property
    def icon(self) -> str:
        """Return the icon for this sensor."""
        if self._is_nrk_radio:
            return "mdi:radio"
        return "mdi:speaker"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Sensor is available if parent Sonos entity exists
        return self.hass.states.get(self._sonos_entity_id) is not None
