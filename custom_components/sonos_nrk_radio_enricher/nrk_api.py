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
        station_logo: str | None = None,
    ) -> None:
        """Initialize track info."""
        self.station_name = station_name
        self.program_title = program_title
        self.track_title = track_title
        self.track_artist = track_artist
        self.description = description
        self.image_url = image_url
        self.station_logo = station_logo

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
            "station_logo": self.station_logo,
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
        Always fetches station logo from livebuffer API.

        Args:
            station: NRK station configuration

        Returns:
            NRKTrackInfo if successful, None if all attempts fail

        """
        # Account for stream delay
        adjusted_time = datetime.now(timezone.utc) - timedelta(
            milliseconds=station["stream_delay"]
        )

        _LOGGER.debug(
            "Fetching track for %s with adjusted time: %s (delay: %dms)",
            station["name"],
            adjusted_time,
            station["stream_delay"],
        )

        # Fetch station logo from livebuffer (it has channel metadata)
        station_logo = await self._fetch_station_logo(station)

        # Try primary API first
        try:
            track_info = await self._fetch_from_liveelements(station, adjusted_time, station_logo)
            if track_info:
                return track_info
            else:
                _LOGGER.debug(
                    "Liveelements returned no matching segment for %s, trying livebuffer",
                    station["name"],
                )
        except Exception as err:
            _LOGGER.debug(
                "Primary API (liveelements) failed for %s: %s",
                station["name"],
                err,
            )

        # Fall back to livebuffer API (content may be here even if not in liveelements)
        _LOGGER.debug("Trying livebuffer fallback for %s", station["name"])
        try:
            track_info = await self._fetch_from_livebuffer(station, adjusted_time, station_logo)
            if track_info:
                _LOGGER.debug("Successfully got track info from livebuffer for %s", station["name"])
                return track_info
            else:
                _LOGGER.debug("Livebuffer also returned no matching entry for %s", station["name"])
        except Exception as err:
            _LOGGER.warning(
                "Fallback API (livebuffer) failed for %s: %s",
                station["name"],
                err,
            )

        return None

    async def _fetch_station_logo(self, station: NRKStation) -> str | None:
        """Fetch station logo from livebuffer API.

        Args:
            station: NRK station configuration

        Returns:
            Station logo URL if found, None otherwise

        """
        try:
            async with asyncio.timeout(NRK_API_TIMEOUT):
                async with self._session.get(
                    station["livebuffer_url"]
                ) as response:
                    response.raise_for_status()
                    data = await response.json()

            if isinstance(data, dict):
                channel = data.get("channel", {})
                _LOGGER.debug("Channel data for logo: %s", channel)
                if isinstance(channel, dict):
                    # Extract logo from channel.image.images array
                    if "image" in channel and isinstance(channel["image"], dict):
                        images_array = channel["image"].get("images", [])
                        if images_array and isinstance(images_array, list):
                            # Pick a good size - prefer 600x337 or first available
                            for img in images_array:
                                if isinstance(img, dict) and img.get("width") == 600:
                                    logo_url = img.get("url")
                                    _LOGGER.debug("Found station logo (600px): %s", logo_url)
                                    return logo_url
                            # Fallback to first image
                            first_img = images_array[0]
                            if isinstance(first_img, dict):
                                logo_url = first_img.get("url")
                                _LOGGER.debug("Found station logo (first): %s", logo_url)
                                return logo_url

            _LOGGER.debug("No station logo found in livebuffer response")
            return None
        except Exception as err:
            _LOGGER.debug("Failed to fetch station logo: %s", err)
            return None

    async def _fetch_from_liveelements(
        self, station: NRKStation, current_time: datetime, station_logo: str | None = None
    ) -> NRKTrackInfo | None:
        """Fetch track info from liveelements API.

        This is the primary API that returns current program segments.

        Args:
            station: NRK station configuration
            current_time: Current time adjusted for stream delay
            station_logo: Station logo URL (from livebuffer)

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

            # Extract channel logo from response
            station_logo = None
            if isinstance(data, dict):
                channel = data.get("channel", {})
                _LOGGER.debug("Channel data from liveelements: %s", channel)
                if isinstance(channel, dict):
                    # Look for logo in various possible locations
                    if "image" in channel:
                        if isinstance(channel["image"], dict):
                            station_logo = channel["image"].get("url")
                        elif isinstance(channel["image"], str):
                            # Image is a string - could be URL or image ID
                            img = channel["image"]
                            if img.startswith("http"):
                                station_logo = img
                            else:
                                # Assume it's an image ID, construct URL
                                station_logo = f"https://gfx.nrk.no/img/{img}"
                    elif "imageUrl" in channel:
                        station_logo = channel["imageUrl"]
                    elif "squareImage" in channel:
                        if isinstance(channel["squareImage"], dict):
                            station_logo = channel["squareImage"].get("url")
                        elif isinstance(channel["squareImage"], str):
                            img = channel["squareImage"]
                            if img.startswith("http"):
                                station_logo = img
                            else:
                                station_logo = f"https://gfx.nrk.no/img/{img}"

                    _LOGGER.debug("Extracted station logo from liveelements: %s", station_logo)

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
                _LOGGER.debug(
                    "Segment '%s' has relativeTimeType: %s",
                    segment.get("title"),
                    relative_type,
                )
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
                    return self._extract_track_info_from_segment(station, segment, station_logo)
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
        self, station: NRKStation, current_time: datetime, station_logo: str | None = None
    ) -> NRKTrackInfo | None:
        """Fetch track info from livebuffer API (fallback).

        Args:
            station: NRK station configuration
            current_time: Current time adjusted for stream delay
            station_logo: Station logo URL (from previous fetch, optional)

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

            # Extract channel logo from response if not already provided
            if not station_logo and isinstance(data, dict):
                channel = data.get("channel", {})
                _LOGGER.debug("Channel data from livebuffer: %s", channel)
                if isinstance(channel, dict):
                    # Look for logo in various possible locations
                    if "image" in channel:
                        if isinstance(channel["image"], dict):
                            station_logo = channel["image"].get("url")
                        elif isinstance(channel["image"], str):
                            # Image is a string - could be URL or image ID
                            img = channel["image"]
                            if img.startswith("http"):
                                station_logo = img
                            else:
                                # Assume it's an image ID, construct URL
                                station_logo = f"https://gfx.nrk.no/img/{img}"
                    elif "imageUrl" in channel:
                        station_logo = channel["imageUrl"]
                    elif "squareImage" in channel:
                        if isinstance(channel["squareImage"], dict):
                            station_logo = channel["squareImage"].get("url")
                        elif isinstance(channel["squareImage"], str):
                            img = channel["squareImage"]
                            if img.startswith("http"):
                                station_logo = img
                            else:
                                station_logo = f"https://gfx.nrk.no/img/{img}"

                    _LOGGER.debug("Extracted station logo from livebuffer: %s", station_logo)

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

                _LOGGER.debug(
                    "Livebuffer entry '%s': start=%s, end=%s, current=%s",
                    entry.get("title"),
                    actual_start,
                    actual_end,
                    current_time,
                )

                if not (actual_start and actual_end):
                    _LOGGER.debug("Entry missing start or end time, skipping")
                    continue

                if actual_start <= current_time <= actual_end:
                    _LOGGER.debug(
                        "Time match! Entry '%s' matches current time",
                        entry.get("title"),
                    )
                    return self._extract_track_info_from_entry(station, entry, station_logo)
                else:
                    _LOGGER.debug(
                        "Time mismatch for entry '%s'",
                        entry.get("title"),
                    )

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
        self, station: NRKStation, segment: dict, station_logo: str | None = None
    ) -> NRKTrackInfo:
        """Extract track info from a liveelements segment.

        Args:
            station: NRK station configuration
            segment: Segment data from API
            station_logo: Station logo URL from channel data

        Returns:
            NRKTrackInfo extracted from segment

        """
        program_title = segment.get("programTitle")
        track_title = segment.get("title")
        description = segment.get("description")

        # Image URL - API provides it directly as imageUrl
        image_url = segment.get("imageUrl")

        # Artist information is in the description field for music tracks
        track_artist = description

        _LOGGER.debug(
            "Extracted info: program=%s, title=%s, artist=%s (from description)",
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
            station_logo=station_logo,
        )

    def _extract_track_info_from_entry(
        self, station: NRKStation, entry: dict, station_logo: str | None = None
    ) -> NRKTrackInfo:
        """Extract track info from a livebuffer entry.

        Args:
            station: NRK station configuration
            entry: Entry data from API
            station_logo: Station logo URL from channel data

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
            station_logo=station_logo,
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
