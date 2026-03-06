"""NRK Radio API client."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import logging
from typing import Any

import aiohttp

from .const import NRK_API_TIMEOUT, NRK_STREAM_DELAY
from .nrk_stations import NRKStation

_LOGGER = logging.getLogger(__name__)


class NRKTrackInfo:
    """Container for enriched NRK track information."""

    def __init__(
        self,
        station_name: str,
        program_title: str | None = None,
        track_title: str | None = None,
        track_artist: str | None = None,
        description: str | None = None,
        image_url: str | None = None,
    ) -> None:
        """Initialize track info."""
        self.station_name = station_name
        self.program_title = program_title
        self.track_title = track_title
        self.track_artist = track_artist
        self.description = description
        self.image_url = image_url

    @property
    def enriched_artist(self) -> str:
        """Get enriched artist string (station + program)."""
        result = self.station_name
        if self.program_title:
            result += f" – {self.program_title}"
        return result

    @property
    def enriched_title(self) -> str:
        """Get enriched title string (track + artist)."""
        if self.track_title and self.track_artist:
            return f"{self.track_title} – {self.track_artist}"
        if self.track_title:
            return self.track_title
        return "Unknown"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for entity attributes."""
        return {
            "station_name": self.station_name,
            "program_title": self.program_title,
            "track_title": self.track_title,
            "track_artist": self.track_artist,
            "description": self.description,
            "image_url": self.image_url,
            "enriched_artist": self.enriched_artist,
            "enriched_title": self.enriched_title,
        }


class NRKApiClient:
    """Client for NRK Radio API."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Initialize the API client.

        Args:
            session: aiohttp client session (shared from HA)

        """
        self._session = session

    async def get_current_track(self, station: NRKStation) -> NRKTrackInfo | None:
        """Get current track information for a station.

        Tries primary API (liveelements) first, falls back to livebuffer API.

        Args:
            station: NRK station configuration

        Returns:
            NRKTrackInfo if successful, None if all attempts fail

        """
        # Account for stream delay
        adjusted_time = datetime.now(timezone.utc) - timedelta(
            milliseconds=station["stream_delay"]
        )

        # Try primary API first
        try:
            track_info = await self._fetch_from_liveelements(station, adjusted_time)
            if track_info:
                return track_info
        except Exception as err:
            _LOGGER.debug(
                "Primary API (liveelements) failed for %s: %s",
                station["name"],
                err,
            )

        # Fall back to livebuffer API
        try:
            track_info = await self._fetch_from_livebuffer(station, adjusted_time)
            if track_info:
                return track_info
        except Exception as err:
            _LOGGER.warning(
                "Fallback API (livebuffer) failed for %s: %s",
                station["name"],
                err,
            )

        return None

    async def _fetch_from_liveelements(
        self, station: NRKStation, current_time: datetime
    ) -> NRKTrackInfo | None:
        """Fetch track info from liveelements API.

        This is the primary API that returns current program segments.

        Args:
            station: NRK station configuration
            current_time: Current time adjusted for stream delay

        Returns:
            NRKTrackInfo if successful, None otherwise

        """
        try:
            async with asyncio.timeout(NRK_API_TIMEOUT):
                async with self._session.get(station["api_url"]) as response:
                    response.raise_for_status()
                    data = await response.json()

            # Find current segment with relativeTimeType === "Present"
            for segment in data.get("segments", []):
                if segment.get("relativeTimeType") != "Present":
                    continue

                # Check if current time falls within segment window
                start_time = self._parse_timestamp(segment.get("startTime"))
                end_time = self._parse_timestamp(segment.get("endTime"))

                if not (start_time and end_time):
                    continue

                if start_time <= current_time <= end_time:
                    return self._extract_track_info_from_segment(station, segment)

            _LOGGER.debug(
                "No matching segment found in liveelements for %s", station["name"]
            )
            return None

        except aiohttp.ClientError as err:
            _LOGGER.debug("HTTP error fetching liveelements: %s", err)
            raise
        except Exception as err:
            _LOGGER.debug("Error parsing liveelements response: %s", err)
            raise

    async def _fetch_from_livebuffer(
        self, station: NRKStation, current_time: datetime
    ) -> NRKTrackInfo | None:
        """Fetch track info from livebuffer API (fallback).

        Args:
            station: NRK station configuration
            current_time: Current time adjusted for stream delay

        Returns:
            NRKTrackInfo if successful, None otherwise

        """
        try:
            async with asyncio.timeout(NRK_API_TIMEOUT):
                async with self._session.get(
                    station["livebuffer_url"]
                ) as response:
                    response.raise_for_status()
                    data = await response.json()

            # Iterate through program entries
            for entry in data.get("entries", []):
                actual_start = self._parse_timestamp(entry.get("actualStart"))
                actual_end = self._parse_timestamp(entry.get("actualEnd"))

                if not (actual_start and actual_end):
                    continue

                if actual_start <= current_time <= actual_end:
                    return self._extract_track_info_from_entry(station, entry)

            _LOGGER.debug(
                "No matching entry found in livebuffer for %s", station["name"]
            )
            return None

        except aiohttp.ClientError as err:
            _LOGGER.debug("HTTP error fetching livebuffer: %s", err)
            raise
        except Exception as err:
            _LOGGER.debug("Error parsing livebuffer response: %s", err)
            raise

    def _extract_track_info_from_segment(
        self, station: NRKStation, segment: dict
    ) -> NRKTrackInfo:
        """Extract track info from a liveelements segment.

        Args:
            station: NRK station configuration
            segment: Segment data from API

        Returns:
            NRKTrackInfo extracted from segment

        """
        program_title = segment.get("programTitle")
        track_title = segment.get("title")
        description = segment.get("description")

        # Image URL might be nested
        image_url = None
        if images := segment.get("images"):
            if isinstance(images, list) and images:
                image_url = images[0].get("url")
            elif isinstance(images, dict):
                image_url = images.get("url")

        # Track artist might be in different fields
        track_artist = segment.get("artist") or segment.get("contributor")

        return NRKTrackInfo(
            station_name=station["name"],
            program_title=program_title,
            track_title=track_title,
            track_artist=track_artist,
            description=description,
            image_url=image_url,
        )

    def _extract_track_info_from_entry(
        self, station: NRKStation, entry: dict
    ) -> NRKTrackInfo:
        """Extract track info from a livebuffer entry.

        Args:
            station: NRK station configuration
            entry: Entry data from API

        Returns:
            NRKTrackInfo extracted from entry

        """
        program_title = entry.get("title")
        description = entry.get("description")

        # Image handling
        image_url = None
        if image_id := entry.get("imageId"):
            image_url = f"https://gfx.nrk.no/img/{image_id}"

        # Livebuffer might not have detailed track info
        return NRKTrackInfo(
            station_name=station["name"],
            program_title=program_title,
            description=description,
            image_url=image_url,
        )

    @staticmethod
    def _parse_timestamp(timestamp: str | None) -> datetime | None:
        """Parse ISO timestamp string to datetime.

        Args:
            timestamp: ISO format timestamp string

        Returns:
            datetime object or None if parsing fails

        """
        if not timestamp:
            return None

        try:
            # Handle different ISO formats
            if timestamp.endswith("Z"):
                timestamp = timestamp[:-1] + "+00:00"
            return datetime.fromisoformat(timestamp)
        except (ValueError, AttributeError):
            return None
