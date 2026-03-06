"""Data update coordinator for NRK API."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_UPDATE_INTERVAL, DOMAIN
from .nrk_api import NRKApiClient, NRKTrackInfo
from .nrk_stations import NRKStation

_LOGGER = logging.getLogger(__name__)


class NRKDataCoordinator(DataUpdateCoordinator[dict[str, NRKTrackInfo]]):
    """Coordinator for fetching NRK track data."""

    def __init__(
        self,
        hass: HomeAssistant,
        update_interval: int = DEFAULT_UPDATE_INTERVAL,
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance
            update_interval: Update interval in seconds

        """
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )
        self._api_client = NRKApiClient(async_get_clientsession(hass))
        self._active_stations: dict[str, NRKStation] = {}

    def register_station(self, station: NRKStation) -> None:
        """Register a station for monitoring.

        Args:
            station: NRK station configuration

        """
        station_id = station["sonos_uri"]
        if station_id not in self._active_stations:
            _LOGGER.debug("Registering station for monitoring: %s", station["name"])
            self._active_stations[station_id] = station

    def unregister_station(self, station: NRKStation) -> None:
        """Unregister a station from monitoring.

        Args:
            station: NRK station configuration

        """
        station_id = station["sonos_uri"]
        if station_id in self._active_stations:
            _LOGGER.debug("Unregistering station: %s", station["name"])
            del self._active_stations[station_id]

    async def _async_update_data(self) -> dict[str, NRKTrackInfo]:
        """Fetch data from NRK API for all active stations.

        Returns:
            Dictionary mapping station URI to track info

        Raises:
            UpdateFailed: If update fails for critical reasons

        """
        if not self._active_stations:
            return {}

        results: dict[str, NRKTrackInfo] = {}

        for station_id, station in self._active_stations.items():
            try:
                track_info = await self._api_client.get_current_track(station)
                if track_info:
                    results[station_id] = track_info
                    _LOGGER.debug(
                        "Updated track info for %s: %s",
                        station["name"],
                        track_info.enriched_title,
                    )
                else:
                    _LOGGER.debug("No track info available for %s", station["name"])
            except Exception as err:
                _LOGGER.warning(
                    "Failed to update %s: %s",
                    station["name"],
                    err,
                )
                # Continue with other stations even if one fails

        return results

    def get_track_info(self, station: NRKStation) -> NRKTrackInfo | None:
        """Get cached track info for a station.

        Args:
            station: NRK station configuration

        Returns:
            Cached track info or None if not available

        """
        if not self.data:
            return None
        return self.data.get(station["sonos_uri"])
