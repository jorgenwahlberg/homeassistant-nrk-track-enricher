"""Tests for NRK station configuration and matching."""
import pytest

from custom_components.sonos_nrk_radio_enricher.nrk_stations import (
    NRK_STATIONS,
    get_station_by_uri,
    is_nrk_radio,
)


class TestStationConfiguration:
    """Test NRK station configuration."""

    def test_all_stations_have_required_fields(self):
        """Test that all stations have required fields."""
        required_fields = [
            "name",
            "api_url",
            "livebuffer_url",
            "sonos_uri",
            "stream_delay",
        ]

        for station in NRK_STATIONS:
            for field in required_fields:
                assert field in station, f"Station {station.get('name')} missing {field}"
                assert station[field] is not None

    def test_station_names_are_unique(self):
        """Test that all station names are unique."""
        names = [station["name"] for station in NRK_STATIONS]
        assert len(names) == len(set(names)), "Duplicate station names found"

    def test_sonos_uris_are_unique(self):
        """Test that all Sonos URIs are unique."""
        uris = [station["sonos_uri"] for station in NRK_STATIONS]
        assert len(uris) == len(set(uris)), "Duplicate Sonos URIs found"

    def test_all_stations_have_standard_delay(self):
        """Test that all stations use the standard 15 second delay."""
        for station in NRK_STATIONS:
            assert (
                station["stream_delay"] == 15000
            ), f"Station {station['name']} has non-standard delay"

    def test_api_urls_follow_pattern(self):
        """Test that API URLs follow expected pattern."""
        for station in NRK_STATIONS:
            api_url = station["api_url"]
            assert api_url.startswith(
                "https://psapi.nrk.no/channels/"
            ), f"Invalid API URL for {station['name']}"
            assert api_url.endswith(
                "/liveelements"
            ), f"Invalid API URL ending for {station['name']}"

    def test_livebuffer_urls_follow_pattern(self):
        """Test that livebuffer URLs follow expected pattern."""
        for station in NRK_STATIONS:
            url = station["livebuffer_url"]
            assert url.startswith(
                "https://psapi.nrk.no/radio/channels/livebuffer/"
            ), f"Invalid livebuffer URL for {station['name']}"

    def test_sonos_uris_follow_pattern(self):
        """Test that Sonos URIs follow expected pattern."""
        for station in NRK_STATIONS:
            uri = station["sonos_uri"]
            assert uri.startswith(
                "x-sonosapi-hls:live%3a"
            ), f"Invalid Sonos URI for {station['name']}"


class TestStationMatching:
    """Test station URI matching functions."""

    def test_get_station_by_uri_p1(self):
        """Test getting NRK P1 by URI."""
        uri = "x-sonosapi-hls:live%3ap1?sid=some-session-id"
        station = get_station_by_uri(uri)

        assert station is not None
        assert station["name"] == "NRK P1"

    def test_get_station_by_uri_mp3(self):
        """Test getting NRK mP3 by URI."""
        uri = "x-sonosapi-hls:live%3amp3"
        station = get_station_by_uri(uri)

        assert station is not None
        assert station["name"] == "NRK mP3"

    def test_get_station_by_uri_klassisk(self):
        """Test getting NRK Klassisk by URI."""
        uri = "x-sonosapi-hls:live%3aklassisk"
        station = get_station_by_uri(uri)

        assert station is not None
        assert station["name"] == "NRK Klassisk"

    def test_get_station_by_uri_with_query_params(self):
        """Test matching URI with query parameters."""
        uri = "x-sonosapi-hls:live%3ap2?sid=123&token=abc"
        station = get_station_by_uri(uri)

        assert station is not None
        assert station["name"] == "NRK P2"

    def test_get_station_by_uri_non_nrk(self):
        """Test that non-NRK URI returns None."""
        uri = "x-sonosapi-stream:spotify-123"
        station = get_station_by_uri(uri)

        assert station is None

    def test_get_station_by_uri_empty_string(self):
        """Test that empty string returns None."""
        station = get_station_by_uri("")
        assert station is None

    def test_is_nrk_radio_p1(self):
        """Test is_nrk_radio with P1 URI."""
        uri = "x-sonosapi-hls:live%3ap1"
        assert is_nrk_radio(uri) is True

    def test_is_nrk_radio_sport(self):
        """Test is_nrk_radio with Sport URI."""
        uri = "x-sonosapi-hls:live%3asport"
        assert is_nrk_radio(uri) is True

    def test_is_nrk_radio_non_nrk(self):
        """Test is_nrk_radio with non-NRK URI."""
        uri = "x-rincon-mp3radio://radio.example.com"
        assert is_nrk_radio(uri) is False

    def test_is_nrk_radio_empty(self):
        """Test is_nrk_radio with empty string."""
        assert is_nrk_radio("") is False

    def test_all_stations_matchable(self):
        """Test that all configured stations can be matched."""
        for station in NRK_STATIONS:
            uri = station["sonos_uri"]
            matched = get_station_by_uri(uri)

            assert (
                matched is not None
            ), f"Station {station['name']} not matchable by its own URI"
            assert matched["name"] == station["name"]


class TestKnownStations:
    """Test that expected NRK stations are configured."""

    expected_stations = [
        "NRK P1",
        "NRK P2",
        "NRK P3",
        "NRK mP3",
        "NRK P1+",
        "NRK P13",
        "NRK Klassisk",
        "NRK Jazz",
        "NRK Folkemusikk",
        "NRK Sport",
        "NRK Nyheter",
        "NRK Sápmi",
    ]

    @pytest.mark.parametrize("station_name", expected_stations)
    def test_station_is_configured(self, station_name):
        """Test that expected station is configured."""
        station_names = [s["name"] for s in NRK_STATIONS]
        assert (
            station_name in station_names
        ), f"Expected station {station_name} not found"

    def test_minimum_station_count(self):
        """Test that we have at least the expected number of stations."""
        assert len(NRK_STATIONS) >= len(
            self.expected_stations
        ), "Missing expected stations"
