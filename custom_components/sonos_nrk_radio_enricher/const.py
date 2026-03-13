"""Constants for the Sonos NRK Radio Enricher integration."""

DOMAIN = "sonos_nrk_radio_enricher"
NAME = "Sonos NRK Radio Enricher"
VERSION = "1.0.2"

# Frontend
CARD_TYPE = "nrk-radio-card"

# Configuration
CONF_UPDATE_INTERVAL = "update_interval"
DEFAULT_UPDATE_INTERVAL = 30  # seconds

# NRK API Configuration
NRK_STREAM_DELAY = 15  # seconds - broadcast delay
NRK_API_TIMEOUT = 10  # seconds

# Sonos URI patterns
SONOS_NRK_URI_PREFIX = "x-sonosapi-hls:live%3a"
SONOS_NRK_URI_PREFIX_ALT = "x-rincon-mp3radio://"

# Attributes
ATTR_PROGRAM_TITLE = "program_title"
ATTR_TRACK_TITLE = "track_title"
ATTR_TRACK_ARTIST = "track_artist"
ATTR_STATION_NAME = "station_name"
ATTR_STATION_LOGO = "station_logo"
ATTR_IS_NRK = "is_nrk_radio"
ATTR_DESCRIPTION = "description"
ATTR_IMAGE_URL = "image_url"
ATTR_ENRICHED_ARTIST = "enriched_artist"
ATTR_ENRICHED_TITLE = "enriched_title"
