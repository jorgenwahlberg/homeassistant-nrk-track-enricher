"""NRK Radio API client."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import logging
import re
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

            _LOGGER.debug(
                "Liveelements API response type for %s: %s",
                station["name"],
                type(data).__name__,
            )

            # Handle response - can be a list directly or an object with segments
            if isinstance(data, list):
                segments = data
            elif isinstance(data, dict):
                segments = data.get("segments", [])
            else:
                _LOGGER.warning(
                    "Unexpected API response type for %s: %s",
                    station["name"],
                    type(data),
                )
                return None

            _LOGGER.debug("Found %d segments for %s", len(segments), station["name"])
            if segments:
                _LOGGER.debug(
                    "First segment keys: %s", list(segments[0].keys()) if segments[0] else "empty"
                )

            # Find current segment with relativeTimeType === "Present"
            for segment in segments:
                relative_type = segment.get("relativeTimeType")
                if relative_type != "Present":
                    continue

                _LOGGER.debug(
                    "Found Present segment for %s: %s",
                    station["name"],
                    segment.get("title"),
                )
                _LOGGER.debug("Full Present segment data: %s", segment)

                # Check if current time falls within segment window
                # API provides startTime and duration (can be in different formats)
                start_time_raw = segment.get("startTime")
                duration_raw = segment.get("duration")

                _LOGGER.debug(
                    "Raw time values - startTime: %r (type: %s), duration: %r (type: %s)",
                    start_time_raw,
                    type(start_time_raw).__name__,
                    duration_raw,
                    type(duration_raw).__name__,
                )

                start_time = self._parse_timestamp(start_time_raw)
                duration_ms = self._parse_duration(duration_raw)

                if not start_time:
                    _LOGGER.warning(
                        "Segment missing or invalid startTime: %s (raw value: %r)",
                        segment.get("title"),
                        start_time_raw,
                    )
                    continue

                # Calculate end time from duration
                if duration_ms:
                    end_time = start_time + timedelta(milliseconds=duration_ms)
                else:
                    # If no duration, check endTime field (fallback)
                    end_time = self._parse_timestamp(segment.get("endTime"))
                    if not end_time:
                        _LOGGER.debug(
                            "Segment missing duration and endTime: %s",
                            segment.get("title"),
                        )
                        continue

                _LOGGER.debug(
                    "Checking time window: start=%s, end=%s, current=%s",
                    start_time,
                    end_time,
                    current_time,
                )

                if start_time <= current_time <= end_time:
                    _LOGGER.debug(
                        "Time match! Extracting track info for %s", station["name"]
                    )
                    return self._extract_track_info_from_segment(station, segment)
                else:
                    _LOGGER.debug(
                        "Time mismatch: current time %s not in range %s to %s",
                        current_time,
                        start_time,
                        end_time,
                    )

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

            _LOGGER.debug(
                "Livebuffer API response type for %s: %s",
                station["name"],
                type(data).__name__,
            )

            # Handle response - can be a list directly or an object with entries
            if isinstance(data, list):
                entries = data
            elif isinstance(data, dict):
                entries = data.get("entries", [])
            else:
                _LOGGER.warning(
                    "Unexpected livebuffer response type for %s: %s",
                    station["name"],
                    type(data),
                )
                return None

            _LOGGER.debug("Found %d entries for %s", len(entries), station["name"])
            if entries:
                _LOGGER.debug(
                    "First entry keys: %s", list(entries[0].keys()) if entries[0] else "empty"
                )

            # Iterate through program entries
            for entry in entries:
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

        # Image URL - API provides it directly as imageUrl
        image_url = segment.get("imageUrl")

        # Track artist - can be in contributors or creators arrays
        track_artist = None
        if contributors := segment.get("contributors"):
            if isinstance(contributors, list) and contributors:
                # Join multiple contributors
                track_artist = ", ".join(contributors)
            elif isinstance(contributors, str):
                track_artist = contributors

        # Fallback to creators if no contributors
        if not track_artist:
            if creators := segment.get("creators"):
                if isinstance(creators, list) and creators:
                    track_artist = ", ".join(creators)
                elif isinstance(creators, str):
                    track_artist = creators

        _LOGGER.debug(
            "Extracted info: program=%s, title=%s, artist=%s",
            program_title,
            track_title,
            track_artist,
        )

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
        """Parse NRK timestamp string to datetime.

        NRK uses two formats:
        1. Microsoft JSON Date: /Date(1234567890+0100)/
        2. ISO 8601: 2026-03-07T10:00:00+01:00

        Args:
            timestamp: Timestamp string in either format

        Returns:
            datetime object or None if parsing fails

        """
        if not timestamp:
            return None

        if not isinstance(timestamp, str):
            _LOGGER.debug(
                "Timestamp is not a string: %r (type: %s)",
                timestamp,
                type(timestamp).__name__,
            )
            return None

        # Try Microsoft JSON Date format: /Date(1234567890+0100)/
        date_match = re.match(r'/Date\((\d+)([+-]\d+)\)/', timestamp)
        if date_match:
            try:
                # Extract milliseconds since epoch
                milliseconds = int(date_match.group(1))
                # Convert to datetime (milliseconds to seconds)
                parsed = datetime.fromtimestamp(milliseconds / 1000, tz=timezone.utc)
                _LOGGER.debug("Parsed Date() format timestamp: %s -> %s", timestamp, parsed)
                return parsed
            except (ValueError, OverflowError) as err:
                _LOGGER.debug("Failed to parse Date() timestamp %r: %s", timestamp, err)
                return None

        # Try ISO 8601 format
        try:
            timestamp_to_parse = timestamp
            if timestamp.endswith("Z"):
                timestamp_to_parse = timestamp[:-1] + "+00:00"

            parsed = datetime.fromisoformat(timestamp_to_parse)
            return parsed
        except (ValueError, AttributeError) as err:
            _LOGGER.debug(
                "Failed to parse ISO timestamp %r: %s",
                timestamp,
                err,
            )
            return None

    @staticmethod
    def _parse_duration(duration: str | int | None) -> int | None:
        """Parse NRK duration to milliseconds.

        NRK uses two formats:
        1. ISO 8601 duration: PT3M13S (3 minutes 13 seconds)
        2. Integer milliseconds: 193000

        Args:
            duration: Duration in either format

        Returns:
            Duration in milliseconds or None if parsing fails

        """
        if duration is None:
            return None

        # If already an integer, return it
        if isinstance(duration, int):
            return duration

        if not isinstance(duration, str):
            _LOGGER.debug("Duration is not string or int: %r", duration)
            return None

        # Try parsing ISO 8601 duration format: PT3M13S
        match = re.match(
            r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?',
            duration
        )
        if match:
            try:
                hours = int(match.group(1) or 0)
                minutes = int(match.group(2) or 0)
                seconds = float(match.group(3) or 0)

                total_ms = int((hours * 3600 + minutes * 60 + seconds) * 1000)
                _LOGGER.debug("Parsed ISO duration %s -> %d ms", duration, total_ms)
                return total_ms
            except (ValueError, AttributeError) as err:
                _LOGGER.debug("Failed to parse ISO duration %r: %s", duration, err)
                return None

        # Try parsing as integer string
        try:
            return int(duration)
        except ValueError:
            _LOGGER.debug("Failed to parse duration as integer: %r", duration)
            return None
