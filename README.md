# Sonos NRK Radio Enricher for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A Home Assistant custom integration that enriches Sonos media players with detailed track information when playing NRK (Norwegian Broadcasting) radio stations.

## Features

- Automatically discovers all Sonos media player entities
- Detects when Sonos is playing NRK radio
- Fetches enriched metadata from NRK APIs:
  - Current program title
  - Track name and artist
  - Program description
  - Album artwork
- Creates sensor entities with enriched data as attributes
- Shows original Sonos data when not playing NRK

## Supported NRK Stations

- NRK P1
- NRK P2
- NRK P3
- NRK mP3
- NRK P1+
- NRK P13
- NRK Klassisk
- NRK Jazz
- NRK Folkemusikk
- NRK Sport
- NRK Nyheter
- NRK Sápmi

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/jorgenwahlberg/homeassistant-nrk-track-enricher`
6. Select category: "Integration"
7. Click "Add"
8. Search for "Sonos NRK Radio Enricher"
9. Click "Download"
10. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/sonos_nrk_radio_enricher` directory to your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to Settings → Devices & Services
2. Click "+ Add Integration"
3. Search for "Sonos NRK Radio Enricher"
4. Follow the configuration steps

### Options

- **Update Interval**: How often to poll NRK APIs for track updates (default: 30 seconds)

## Usage

Once configured, the integration will:

1. Automatically discover all Sonos media players
2. Create sensor entities for each Sonos player (e.g., `sensor.living_room_sonos_nrk`)
3. Monitor playback and enrich data when NRK radio is detected

### Sensor Attributes

When playing NRK radio:
- `station_name`: NRK station name
- `program_title`: Current radio program
- `track_title`: Current track name
- `track_artist`: Track artist
- `enriched_artist`: Formatted as "Station – Program"
- `enriched_title`: Formatted as "Track – Artist"
- `description`: Program description
- `image_url`: Album/program artwork URL
- `is_nrk_radio`: true

When not playing NRK:
- `media_title`: Original Sonos media title
- `media_artist`: Original Sonos artist
- `media_album_name`: Original Sonos album
- `is_nrk_radio`: false

## Custom Dashboard Card

This integration includes a custom Lovelace card for displaying NRK radio playback information with artwork.

### Card Features

- Album artwork display with fallback icon
- Station name and program title
- Track title and artist
- Visual NRK badge when playing NRK radio
- Automatic updates when track changes
- Responsive design for mobile and desktop

### Adding the Card

1. After installing the integration, the card is automatically registered
2. In Lovelace dashboard, click "Add Card"
3. Search for "NRK Radio Card"
4. Select your NRK sensor entity
5. Configure card options (optional)

### Card Configuration

```yaml
type: custom:nrk-radio-card
entity: sensor.bedroom_sonos_nrk
name: Now Playing
show_header: true
```

**Configuration Options:**
- `entity` (required): The NRK sensor entity ID
- `name` (optional): Card header text (default: "Now Playing")
- `show_header` (optional): Show/hide header (default: true)

### Card Example

```yaml
type: custom:nrk-radio-card
entity: sensor.living_room_sonos_nrk
name: Living Room Radio
```

The card will automatically display:
- Album artwork when available
- Track title and artist
- Station name and program title
- A red NRK badge when playing NRK radio
- Falls back to standard Sonos data when not playing NRK

## Examples

### Display enriched track in Lovelace

```yaml
type: entities
entities:
  - entity: sensor.living_room_sonos_nrk
    type: attribute
    attribute: enriched_title
    name: Now Playing
  - entity: sensor.living_room_sonos_nrk
    type: attribute
    attribute: enriched_artist
    name: Station/Program
```

### Automation example

```yaml
automation:
  - alias: "Notify when favorite program starts"
    trigger:
      - platform: state
        entity_id: sensor.living_room_sonos_nrk
        attribute: program_title
        to: "P3morgen"
    action:
      - service: notify.mobile_app
        data:
          message: "P3morgen is now on!"
```

## Technical Details

This integration:
- Uses Home Assistant's `DataUpdateCoordinator` for efficient API polling
- Implements state listeners to monitor Sonos entities
- Accounts for NRK's 15-second broadcast delay
- Falls back to secondary API if primary fails
- Only polls APIs when NRK radio is actively playing

## Development & Testing

### Running Tests

The integration includes comprehensive tests to verify correct API parsing:

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=custom_components.sonos_nrk_radio_enricher --cov-report=html
```

See [tests/README.md](tests/README.md) for detailed testing documentation.

### Test Coverage

- **API parsing:** Validates NRK API response handling
- **Station matching:** Verifies URI pattern matching
- **Time windows:** Tests segment time range calculations
- **Data extraction:** Confirms field parsing (contributors, images, etc.)

## Troubleshooting

Enable debug logging in `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.sonos_nrk_radio_enricher: debug
```

## Credits

Based on the [MMM-Sonos](https://github.com/jorgenwahlberg/MMM-Sonos) MagicMirror module's NRK integration logic.

## License

MIT License
