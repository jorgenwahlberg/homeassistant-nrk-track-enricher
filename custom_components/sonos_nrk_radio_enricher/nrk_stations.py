"""NRK Radio station configurations."""
from __future__ import annotations

from typing import TypedDict


class NRKStation(TypedDict):
    """NRK station configuration."""

    name: str
    api_url: str
    livebuffer_url: str
    sonos_uri: str
    stream_delay: int
    logo_url: str


NRK_STATIONS: list[NRKStation] = [
    {
        "name": "NRK P1",
        "api_url": "https://psapi.nrk.no/channels/p1/liveelements",
        "livebuffer_url": "https://psapi.nrk.no/radio/channels/livebuffer/p1",
        "sonos_uri": "x-sonosapi-hls:live%3ap1",
        "stream_delay": 15000,
        "logo_url": "https://gfx.nrk.no/MdWTJg-aV3_NbIEsQ3pLkgb_z_Wh97RCEyLF8PEfpfJQ",
    },
    {
        "name": "NRK P2",
        "api_url": "https://psapi.nrk.no/channels/p2/liveelements",
        "livebuffer_url": "https://psapi.nrk.no/radio/channels/livebuffer/p2",
        "sonos_uri": "x-sonosapi-hls:live%3ap2",
        "stream_delay": 15000,
        "logo_url": "https://gfx.nrk.no/FKQR3YCUvJ4yVKoGp_-O4A_Z0iJHEsV4qr0zMQ8GgqwA",
    },
    {
        "name": "NRK P3",
        "api_url": "https://psapi.nrk.no/channels/p3/liveelements",
        "livebuffer_url": "https://psapi.nrk.no/radio/channels/livebuffer/p3",
        "sonos_uri": "x-sonosapi-hls:live%3ap3",
        "stream_delay": 15000,
        "logo_url": "https://gfx.nrk.no/WoNqKJ_bZU4bE2cGx_0_-wcb4nI-kZ8VGGoGpDEfEoYw",
    },
    {
        "name": "NRK mP3",
        "api_url": "https://psapi.nrk.no/channels/mp3/liveelements",
        "livebuffer_url": "https://psapi.nrk.no/radio/channels/livebuffer/mp3",
        "sonos_uri": "x-sonosapi-hls:live%3amp3",
        "stream_delay": 15000,
        "logo_url": "https://gfx.nrk.no/bsIUhD_l0o6dElhAJ8jW2gXYlVJeVp-WTdJXVGGSOpMA",
    },
    {
        "name": "NRK P1+",
        "api_url": "https://psapi.nrk.no/channels/p1pluss/liveelements",
        "livebuffer_url": "https://psapi.nrk.no/radio/channels/livebuffer/p1pluss",
        "sonos_uri": "x-sonosapi-hls:live%3ap1pluss",
        "stream_delay": 15000,
        "logo_url": "https://gfx.nrk.no/qo_rfz-DVhk3qXa3YAiL3APtN0e8fVnQc4IWKS9Lqd1g",
    },
    {
        "name": "NRK P13",
        "api_url": "https://psapi.nrk.no/channels/p13/liveelements",
        "livebuffer_url": "https://psapi.nrk.no/radio/channels/livebuffer/p13",
        "sonos_uri": "x-sonosapi-hls:live%3ap13",
        "stream_delay": 15000,
        "logo_url": "https://gfx.nrk.no/kKZf-nfhkZ0DlU8kcgDpggnR3Qe3MJ_FoOHVlJgL0qhg",
    },
    {
        "name": "NRK Klassisk",
        "api_url": "https://psapi.nrk.no/channels/klassisk/liveelements",
        "livebuffer_url": "https://psapi.nrk.no/radio/channels/livebuffer/klassisk",
        "sonos_uri": "x-sonosapi-hls:live%3aklassisk",
        "stream_delay": 15000,
        "logo_url": "https://gfx.nrk.no/sUXCPVsxkEIDOcjU5W4v5gNMsChAEcVY9-w-OjAKHwJg",
    },
    {
        "name": "NRK Jazz",
        "api_url": "https://psapi.nrk.no/channels/jazz/liveelements",
        "livebuffer_url": "https://psapi.nrk.no/radio/channels/livebuffer/jazz",
        "sonos_uri": "x-sonosapi-hls:live%3ajazz",
        "stream_delay": 15000,
        "logo_url": "https://gfx.nrk.no/O_4BnC91LzMpYlpR4rQo5Al7MPshPLdFINt_1_dFz1Uw",
    },
    {
        "name": "NRK Folkemusikk",
        "api_url": "https://psapi.nrk.no/channels/folkemusikk/liveelements",
        "livebuffer_url": "https://psapi.nrk.no/radio/channels/livebuffer/folkemusikk",
        "sonos_uri": "x-sonosapi-hls:live%3afolkemusikk",
        "stream_delay": 15000,
        "logo_url": "https://gfx.nrk.no/lKx5OAmf7EzYZUYBnTgA9QMwk8QdOEuLO_qDwXHmgJyA",
    },
    {
        "name": "NRK Sport",
        "api_url": "https://psapi.nrk.no/channels/sport/liveelements",
        "livebuffer_url": "https://psapi.nrk.no/radio/channels/livebuffer/sport",
        "sonos_uri": "x-sonosapi-hls:live%3asport",
        "stream_delay": 15000,
        "logo_url": "https://gfx.nrk.no/zXgaGF0hgikO8kMzpFRTVgQ_yO3r59_kU_Gx2QsGr4Ew",
    },
    {
        "name": "NRK Nyheter",
        "api_url": "https://psapi.nrk.no/channels/nyheter/liveelements",
        "livebuffer_url": "https://psapi.nrk.no/radio/channels/livebuffer/nyheter",
        "sonos_uri": "x-sonosapi-hls:live%3anyheter",
        "stream_delay": 15000,
        "logo_url": "https://gfx.nrk.no/y0VdJvA0JFlqQhR19fOMjQnUBkMO7V_AwV0bq5J2H9Rg",
    },
    {
        "name": "NRK Sápmi",
        "api_url": "https://psapi.nrk.no/channels/sapmi/liveelements",
        "livebuffer_url": "https://psapi.nrk.no/radio/channels/livebuffer/sapmi",
        "sonos_uri": "x-sonosapi-hls:live%3asapmi",
        "stream_delay": 15000,
        "logo_url": "https://gfx.nrk.no/m1_P-8jzlhk-Qet3w1Y5XwoKaVGdFAXwcP9NUEfgVUzg",
    },
]


def get_station_by_uri(sonos_uri: str) -> NRKStation | None:
    """Get NRK station configuration by matching Sonos URI.

    Args:
        sonos_uri: The media_content_id from Sonos entity

    Returns:
        NRKStation configuration if match found, None otherwise

    """
    for station in NRK_STATIONS:
        if sonos_uri.startswith(station["sonos_uri"]):
            return station
    return None


def is_nrk_radio(sonos_uri: str) -> bool:
    """Check if Sonos URI is playing NRK radio.

    Args:
        sonos_uri: The media_content_id from Sonos entity

    Returns:
        True if playing NRK radio, False otherwise

    """
    return get_station_by_uri(sonos_uri) is not None
