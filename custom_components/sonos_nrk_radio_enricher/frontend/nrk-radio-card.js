class NRKRadioCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error('You need to define an entity');
    }
    this.config = config;
    this.render();
  }

  set hass(hass) {
    this._hass = hass;
    this.render();
  }

  render() {
    if (!this._hass || !this.config) {
      return;
    }

    const entityId = this.config.entity;
    const stateObj = this._hass.states[entityId];

    if (!stateObj) {
      this.shadowRoot.innerHTML = `
        <ha-card>
          <div class="card-content">Entity ${entityId} not found</div>
        </ha-card>
      `;
      return;
    }

    const isNrk = stateObj.attributes.is_nrk_radio || false;
    const stationName = stateObj.attributes.station_name || '';
    const stationLogo = stateObj.attributes.station_logo || '';
    const programTitle = stateObj.attributes.program_title || '';
    const trackTitle = stateObj.attributes.track_title || '';
    const trackArtist = stateObj.attributes.track_artist || '';
    const enrichedTitle = stateObj.attributes.enriched_title || stateObj.state;
    const enrichedArtist = stateObj.attributes.enriched_artist || '';
    const imageUrl = stateObj.attributes.image_url || '';

    // Determine layout mode
    const layout = this.config.layout || 'square'; // 'square' or 'horizontal'
    const isHorizontal = layout === 'horizontal';

    // Determine what to show
    // If playing a track (has track_title), show artwork
    // If just program (no track_title), show station logo
    const hasTrack = isNrk && trackTitle;
    const displayImage = hasTrack
      ? (imageUrl || stationLogo)  // Track: prefer artwork, fallback to logo
      : isNrk
        ? stationLogo  // Program only: show station logo
        : (stateObj.attributes.entity_picture || '');  // Non-NRK: Sonos artwork

    // Fallback to Sonos data if not NRK
    const displayTitle = isNrk
      ? (hasTrack ? enrichedTitle : programTitle || stationName)
      : (stateObj.attributes.media_title || stateObj.state);

    const displayArtist = isNrk
      ? (hasTrack ? enrichedArtist : '')
      : (stateObj.attributes.media_artist || '');

    const displayStation = isNrk && hasTrack
      ? `${stationName}${programTitle ? ' – ' + programTitle : ''}`
      : '';

    this.shadowRoot.innerHTML = `
      <style>
        ha-card {
          padding: 16px;
          display: flex;
          flex-direction: ${isHorizontal ? 'row' : 'column'};
          align-items: ${isHorizontal ? 'center' : 'center'};
          gap: ${isHorizontal ? '16px' : '0'};
        }
        .card-header {
          font-size: 1.2em;
          font-weight: bold;
          margin-bottom: ${isHorizontal ? '0' : '12px'};
          color: var(--primary-text-color);
          ${isHorizontal ? 'width: 100%; text-align: left;' : ''}
        }
        .artwork-container {
          ${isHorizontal ? 'flex-shrink: 0;' : ''}
        }
        .artwork {
          width: ${isHorizontal ? '120px' : '200px'};
          height: ${isHorizontal ? '120px' : '200px'};
          border-radius: 8px;
          object-fit: cover;
          margin-bottom: ${isHorizontal ? '0' : '16px'};
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        }
        .artwork-placeholder {
          width: ${isHorizontal ? '120px' : '200px'};
          height: ${isHorizontal ? '120px' : '200px'};
          border-radius: 8px;
          background: var(--disabled-color);
          display: flex;
          align-items: center;
          justify-content: center;
          margin-bottom: ${isHorizontal ? '0' : '16px'};
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        }
        .artwork-placeholder ha-icon {
          --mdc-icon-size: ${isHorizontal ? '60px' : '80px'};
          color: var(--primary-background-color);
        }
        .info {
          text-align: ${isHorizontal ? 'left' : 'center'};
          width: 100%;
          ${isHorizontal ? 'flex-grow: 1; display: flex; flex-direction: column; justify-content: center;' : ''}
        }
        .title {
          font-size: ${isHorizontal ? '1.0em' : '1.1em'};
          font-weight: 500;
          margin-bottom: 8px;
          color: var(--primary-text-color);
        }
        .artist {
          font-size: ${isHorizontal ? '0.9em' : '0.95em'};
          color: var(--secondary-text-color);
          margin-bottom: 4px;
        }
        .station {
          font-size: ${isHorizontal ? '0.8em' : '0.85em'};
          color: var(--disabled-text-color);
          margin-top: 8px;
        }
        .nrk-badge {
          display: inline-block;
          background: #ff4444;
          color: white;
          padding: 4px 12px;
          border-radius: 12px;
          font-size: 0.75em;
          font-weight: bold;
          margin-top: 8px;
        }
      </style>
      <ha-card>
        ${this.config.show_header !== false && !isHorizontal ? `<div class="card-header">${this.config.name || 'Now Playing'}</div>` : ''}

        <div class="artwork-container">
          ${displayImage ?
            `<img class="artwork" src="${displayImage}" alt="Artwork" />` :
            `<div class="artwork-placeholder">
              <ha-icon icon="mdi:${isNrk ? 'radio' : 'music'}"></ha-icon>
            </div>`
          }
        </div>

        <div class="info">
          ${this.config.show_header !== false && isHorizontal ? `<div class="card-header">${this.config.name || 'Now Playing'}</div>` : ''}
          <div class="title">${displayTitle}</div>
          ${displayArtist ? `<div class="artist">${displayArtist}</div>` : ''}
          ${displayStation ? `<div class="station">${displayStation}</div>` : ''}
          ${isNrk ? '<div class="nrk-badge">NRK</div>' : ''}
        </div>
      </ha-card>
    `;
  }

  getCardSize() {
    const layout = this.config.layout || 'square';
    return layout === 'horizontal' ? 2 : 4;
  }

  static getStubConfig() {
    return {
      entity: 'sensor.example_nrk',
      name: 'Now Playing',
      show_header: true,
      layout: 'square'
    };
  }
}

customElements.define('nrk-radio-card', NRKRadioCard);

// Register the card with the card picker
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'nrk-radio-card',
  name: 'NRK Radio Card',
  description: 'Display NRK radio playback information with artwork',
  preview: true,
  documentationURL: 'https://github.com/jorgenwahlberg/homeassistant-nrk-track-enricher'
});
