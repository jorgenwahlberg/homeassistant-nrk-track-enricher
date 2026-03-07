# Tests for Sonos NRK Radio Enricher

This directory contains comprehensive tests for the integration, focusing on verifying correct parsing of NRK API responses.

## Running Tests

### Install Test Dependencies

```bash
pip install -r requirements-test.txt
```

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=custom_components.sonos_nrk_radio_enricher --cov-report=html
```

This generates a coverage report in `htmlcov/index.html`.

### Run Specific Test Files

```bash
# Test NRK API parsing
pytest tests/test_nrk_api.py

# Test station matching
pytest tests/test_nrk_stations.py
```

### Run Specific Tests

```bash
# Run a specific test class
pytest tests/test_nrk_api.py::TestNRKTrackInfo

# Run a specific test
pytest tests/test_nrk_api.py::TestNRKTrackInfo::test_enriched_artist_with_program
```

### Verbose Output

```bash
pytest -v
```

## Test Coverage

### `test_nrk_api.py`

Tests for NRK API client (`nrk_api.py`):

- **NRKTrackInfo class:**
  - Enriched artist formatting (with/without program)
  - Enriched title formatting (with/without artist)
  - Dictionary conversion

- **API parsing:**
  - Timestamp parsing (ISO format, Z suffix, invalid)
  - Track info extraction from segments
  - Track info extraction from livebuffer entries
  - Contributor/creator handling (arrays and strings)
  - Image URL extraction

- **API fetching:**
  - Successful liveelements fetch
  - Successful livebuffer fetch
  - Primary API with fallback behavior
  - Error handling

- **Time window matching:**
  - Current time within segment window
  - Current time before segment
  - Current time after segment
  - Duration-based end time calculation

### `test_nrk_stations.py`

Tests for station configuration (`nrk_stations.py`):

- **Station configuration:**
  - All required fields present
  - Unique station names and URIs
  - Standard stream delay (15 seconds)
  - API URL patterns
  - Sonos URI patterns

- **Station matching:**
  - Match by exact URI
  - Match with query parameters
  - Non-NRK URIs return None
  - Empty string handling
  - All stations matchable

- **Known stations:**
  - Presence of expected stations (P1, P2, P3, etc.)
  - Minimum station count

## Test Data

Tests use sample data matching the actual NRK API response structure:

```json
{
  "title": "Track Title",
  "description": "Artist Name",
  "programTitle": "Program Name",
  "startTime": "2026-03-07T10:00:00+01:00",
  "duration": 180000,
  "relativeTimeType": "Present",
  "imageUrl": "https://example.com/image.jpg"
}
```

**Note:** Artist information is stored in the `description` field for music tracks.

This ensures tests accurately reflect real-world API behavior.

## Continuous Integration

Tests are designed to run in CI/CD pipelines. Add to your GitHub Actions workflow:

```yaml
- name: Run tests
  run: |
    pip install -r requirements-test.txt
    pytest --cov=custom_components.sonos_nrk_radio_enricher
```

## Writing New Tests

When adding new features:

1. Add test cases to relevant test file
2. Use pytest fixtures for common setup
3. Mock external dependencies (HTTP requests)
4. Test both success and failure scenarios
5. Verify edge cases (None values, empty arrays, etc.)

Example:

```python
@pytest.mark.asyncio
async def test_new_feature(nrk_api_client, test_station):
    """Test description."""
    # Setup
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value={...})

    # Execute
    result = await nrk_api_client.some_method(test_station)

    # Assert
    assert result is not None
    assert result.field == "expected_value"
```
