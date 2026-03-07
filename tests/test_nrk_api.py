"""Tests for NRK API client."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest

from custom_components.sonos_nrk_radio_enricher.nrk_api import (
    NRKApiClient,
    NRKTrackInfo,
)
from custom_components.sonos_nrk_radio_enricher.nrk_stations import NRKStation


@pytest.fixture
def mock_session():
    """Create a mock aiohttp session."""
    return Mock(spec=aiohttp.ClientSession)


@pytest.fixture
def nrk_api_client(mock_session):
    """Create an NRK API client with mock session."""
    return NRKApiClient(mock_session)


@pytest.fixture
def test_station() -> NRKStation:
    """Create a test NRK station."""
    return {
        "name": "NRK P1",
        "api_url": "https://psapi.nrk.no/channels/p1/liveelements",
        "livebuffer_url": "https://psapi.nrk.no/radio/channels/livebuffer/p1",
        "sonos_uri": "x-sonosapi-hls:live%3ap1",
        "stream_delay": 15000,
    }


# Sample API response data based on actual API structure
# Note: Artist information is in the description field for music tracks
SAMPLE_LIVEELEMENTS_RESPONSE = [
    {
        "title": "Track Title 1",
        "description": "Artist Name",  # Artist info is in description
        "programId": "program123",
        "channelId": "p1",
        "startTime": "2026-03-07T10:00:00+01:00",
        "duration": 180000,  # 3 minutes in milliseconds
        "type": "music",
        "imageUrl": "https://example.com/image.jpg",
        "programTitle": "Morning Show",
        "relativeTimeType": "Past",
        "category": "Music",
        "contributors": [],
        "creators": [],
    },
    {
        "title": "Current Track Title",
        "description": "Current Artist",  # Artist info is in description
        "programId": "program124",
        "channelId": "p1",
        "startTime": "2026-03-07T10:03:00+01:00",
        "duration": 240000,  # 4 minutes in milliseconds
        "type": "music",
        "imageUrl": "https://example.com/current.jpg",
        "programTitle": "Morning Show",
        "relativeTimeType": "Present",
        "category": "Music",
        "contributors": [],
        "creators": [],
    },
    {
        "title": "Future Track",
        "description": "Future Artist",  # Artist info is in description
        "programId": "program125",
        "channelId": "p1",
        "startTime": "2026-03-07T10:07:00+01:00",
        "duration": 180000,
        "type": "music",
        "imageUrl": "https://example.com/future.jpg",
        "programTitle": "Morning Show",
        "relativeTimeType": "Future",
        "category": "Music",
        "contributors": [],
        "creators": [],
    },
]

SAMPLE_LIVEBUFFER_RESPONSE = {
    "entries": [
        {
            "title": "Morning Program",
            "description": "Program description",
            "imageId": "ABC123XYZ",
            "actualStart": "2026-03-07T08:00:00+01:00",
            "actualEnd": "2026-03-07T12:00:00+01:00",
        }
    ]
}


class TestNRKTrackInfo:
    """Test NRKTrackInfo class."""

    def test_enriched_artist_with_program(self):
        """Test enriched artist with program title."""
        info = NRKTrackInfo(
            station_name="NRK P1",
            program_title="Morning Show",
            track_title="Song Title",
            track_artist="Artist Name",
        )
        assert info.enriched_artist == "NRK P1 – Morning Show"

    def test_enriched_artist_without_program(self):
        """Test enriched artist without program title."""
        info = NRKTrackInfo(
            station_name="NRK P1",
            program_title=None,
            track_title="Song Title",
            track_artist="Artist Name",
        )
        assert info.enriched_artist == "NRK P1"

    def test_enriched_title_with_artist(self):
        """Test enriched title with artist."""
        info = NRKTrackInfo(
            station_name="NRK P1",
            track_title="Song Title",
            track_artist="Artist Name",
        )
        assert info.enriched_title == "Song Title – Artist Name"

    def test_enriched_title_without_artist(self):
        """Test enriched title without artist."""
        info = NRKTrackInfo(
            station_name="NRK P1", track_title="Song Title", track_artist=None
        )
        assert info.enriched_title == "Song Title"

    def test_enriched_title_without_both(self):
        """Test enriched title without title or artist."""
        info = NRKTrackInfo(
            station_name="NRK P1", track_title=None, track_artist=None
        )
        assert info.enriched_title == "Unknown"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        info = NRKTrackInfo(
            station_name="NRK P1",
            program_title="Morning Show",
            track_title="Song Title",
            track_artist="Artist Name",
            description="Description",
            image_url="https://example.com/image.jpg",
        )
        data = info.to_dict()

        assert data["station_name"] == "NRK P1"
        assert data["program_title"] == "Morning Show"
        assert data["track_title"] == "Song Title"
        assert data["track_artist"] == "Artist Name"
        assert data["description"] == "Description"
        assert data["image_url"] == "https://example.com/image.jpg"
        assert data["enriched_artist"] == "NRK P1 – Morning Show"
        assert data["enriched_title"] == "Song Title – Artist Name"


class TestNRKApiClient:
    """Test NRKApiClient class."""

    def test_parse_timestamp_iso_format(self, nrk_api_client):
        """Test parsing ISO timestamp."""
        timestamp = "2026-03-07T10:00:00+01:00"
        result = nrk_api_client._parse_timestamp(timestamp)

        assert result is not None
        assert isinstance(result, datetime)
        assert result.year == 2026
        assert result.month == 3
        assert result.day == 7
        assert result.hour == 10

    def test_parse_timestamp_with_z(self, nrk_api_client):
        """Test parsing timestamp with Z suffix."""
        timestamp = "2026-03-07T09:00:00Z"
        result = nrk_api_client._parse_timestamp(timestamp)

        assert result is not None
        assert isinstance(result, datetime)

    def test_parse_timestamp_invalid(self, nrk_api_client):
        """Test parsing invalid timestamp."""
        result = nrk_api_client._parse_timestamp("invalid")
        assert result is None

    def test_parse_timestamp_none(self, nrk_api_client):
        """Test parsing None timestamp."""
        result = nrk_api_client._parse_timestamp(None)
        assert result is None

    def test_extract_track_info_from_segment_with_artist_in_description(self, nrk_api_client, test_station):
        """Test extracting track info from segment - artist comes from description."""
        segment = {
            "title": "Track Title",
            "programTitle": "Morning Show",
            "description": "Artist Name",
            "imageUrl": "https://example.com/image.jpg",
            "contributors": ["Contributor"],
            "creators": [],
        }

        info = nrk_api_client._extract_track_info_from_segment(test_station, segment)

        assert info.station_name == "NRK P1"
        assert info.program_title == "Morning Show"
        assert info.track_title == "Track Title"
        assert info.track_artist == "Artist Name"  # From description
        assert info.description == "Artist Name"
        assert info.image_url == "https://example.com/image.jpg"

    def test_extract_track_info_from_segment_without_description(self, nrk_api_client, test_station):
        """Test extracting track info when description is missing."""
        segment = {
            "title": "Track Title",
            "programTitle": "Morning Show",
            "imageUrl": "https://example.com/image.jpg",
        }

        info = nrk_api_client._extract_track_info_from_segment(test_station, segment)

        assert info.track_artist is None  # No description means no artist

    def test_extract_track_info_from_entry(self, nrk_api_client, test_station):
        """Test extracting track info from livebuffer entry."""
        entry = {
            "title": "Program Title",
            "description": "Program description",
            "imageId": "ABC123XYZ",
        }

        info = nrk_api_client._extract_track_info_from_entry(test_station, entry)

        assert info.station_name == "NRK P1"
        assert info.program_title == "Program Title"
        assert info.description == "Program description"
        assert info.image_url == "https://gfx.nrk.no/img/ABC123XYZ"

    @pytest.mark.asyncio
    async def test_fetch_from_liveelements_success(self, nrk_api_client, test_station):
        """Test successful fetch from liveelements API."""
        # Mock the HTTP response
        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock()
        mock_response.json = AsyncMock(return_value=SAMPLE_LIVEELEMENTS_RESPONSE)

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_response
        nrk_api_client._session.get = Mock(return_value=mock_context_manager)

        # Use a time that matches the "Present" segment
        current_time = datetime(2026, 3, 7, 10, 5, 0, tzinfo=timezone.utc)

        result = await nrk_api_client._fetch_from_liveelements(
            test_station, current_time
        )

        assert result is not None
        assert result.track_title == "Current Track Title"
        assert result.program_title == "Morning Show"
        assert result.track_artist == "Current Artist"

    @pytest.mark.asyncio
    async def test_fetch_from_liveelements_no_present_segment(
        self, nrk_api_client, test_station
    ):
        """Test liveelements API when no Present segment found."""
        # Mock response with no Present segments
        response_data = [
            {
                "title": "Track",
                "relativeTimeType": "Past",
                "startTime": "2026-03-07T09:00:00+01:00",
                "duration": 180000,
            }
        ]

        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock()
        mock_response.json = AsyncMock(return_value=response_data)

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_response
        nrk_api_client._session.get = Mock(return_value=mock_context_manager)

        current_time = datetime.now(timezone.utc)
        result = await nrk_api_client._fetch_from_liveelements(
            test_station, current_time
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_from_livebuffer_success(self, nrk_api_client, test_station):
        """Test successful fetch from livebuffer API."""
        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock()
        mock_response.json = AsyncMock(return_value=SAMPLE_LIVEBUFFER_RESPONSE)

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_response
        nrk_api_client._session.get = Mock(return_value=mock_context_manager)

        # Use a time within the entry's time range
        current_time = datetime(2026, 3, 7, 10, 0, 0, tzinfo=timezone.utc)

        result = await nrk_api_client._fetch_from_livebuffer(
            test_station, current_time
        )

        assert result is not None
        assert result.program_title == "Morning Program"
        assert result.description == "Program description"

    @pytest.mark.asyncio
    async def test_get_current_track_uses_primary_api(
        self, nrk_api_client, test_station
    ):
        """Test that get_current_track uses primary API first."""
        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock()
        mock_response.json = AsyncMock(return_value=SAMPLE_LIVEELEMENTS_RESPONSE)

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_response
        nrk_api_client._session.get = Mock(return_value=mock_context_manager)

        result = await nrk_api_client.get_current_track(test_station)

        # Should successfully get data from primary API
        assert result is not None
        assert result.track_title == "Current Track Title"

    @pytest.mark.asyncio
    async def test_get_current_track_falls_back_to_livebuffer(
        self, nrk_api_client, test_station
    ):
        """Test that get_current_track falls back to livebuffer API."""
        # Make primary API fail
        mock_failed_response = AsyncMock()
        mock_failed_response.raise_for_status = Mock(
            side_effect=aiohttp.ClientError()
        )

        # Make fallback API succeed
        mock_success_response = AsyncMock()
        mock_success_response.raise_for_status = Mock()
        mock_success_response.json = AsyncMock(return_value=SAMPLE_LIVEBUFFER_RESPONSE)

        # Set up mock to fail first call, succeed on second
        mock_context_manager_fail = AsyncMock()
        mock_context_manager_fail.__aenter__.return_value = mock_failed_response

        mock_context_manager_success = AsyncMock()
        mock_context_manager_success.__aenter__.return_value = mock_success_response

        nrk_api_client._session.get = Mock(
            side_effect=[mock_context_manager_fail, mock_context_manager_success]
        )

        result = await nrk_api_client.get_current_track(test_station)

        # Should get data from fallback API
        assert result is not None
        assert result.program_title == "Morning Program"


class TestTimeWindowMatching:
    """Test time window matching logic."""

    @pytest.mark.asyncio
    async def test_time_within_window(self, nrk_api_client, test_station):
        """Test matching when current time is within segment window."""
        segment_data = [
            {
                "title": "Test Track",
                "programTitle": "Test Program",
                "relativeTimeType": "Present",
                "startTime": "2026-03-07T10:00:00Z",
                "duration": 300000,  # 5 minutes
                "contributors": ["Test Artist"],
            }
        ]

        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock()
        mock_response.json = AsyncMock(return_value=segment_data)

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_response
        nrk_api_client._session.get = Mock(return_value=mock_context_manager)

        # Current time is 2 minutes into the 5-minute segment
        current_time = datetime(2026, 3, 7, 10, 2, 0, tzinfo=timezone.utc)

        result = await nrk_api_client._fetch_from_liveelements(
            test_station, current_time
        )

        assert result is not None
        assert result.track_title == "Test Track"

    @pytest.mark.asyncio
    async def test_time_before_window(self, nrk_api_client, test_station):
        """Test when current time is before segment window."""
        segment_data = [
            {
                "title": "Test Track",
                "relativeTimeType": "Present",
                "startTime": "2026-03-07T10:00:00Z",
                "duration": 300000,
                "contributors": [],
            }
        ]

        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock()
        mock_response.json = AsyncMock(return_value=segment_data)

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_response
        nrk_api_client._session.get = Mock(return_value=mock_context_manager)

        # Current time is before segment starts
        current_time = datetime(2026, 3, 7, 9, 55, 0, tzinfo=timezone.utc)

        result = await nrk_api_client._fetch_from_liveelements(
            test_station, current_time
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_time_after_window(self, nrk_api_client, test_station):
        """Test when current time is after segment window."""
        segment_data = [
            {
                "title": "Test Track",
                "relativeTimeType": "Present",
                "startTime": "2026-03-07T10:00:00Z",
                "duration": 300000,  # 5 minutes
                "contributors": [],
            }
        ]

        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock()
        mock_response.json = AsyncMock(return_value=segment_data)

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_response
        nrk_api_client._session.get = Mock(return_value=mock_context_manager)

        # Current time is after segment ends (10:05 + 1 minute)
        current_time = datetime(2026, 3, 7, 10, 6, 0, tzinfo=timezone.utc)

        result = await nrk_api_client._fetch_from_liveelements(
            test_station, current_time
        )

        assert result is None
