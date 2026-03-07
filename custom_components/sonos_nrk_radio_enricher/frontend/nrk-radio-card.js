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
    const programTitle = stateObj.attributes.program_title || '';
    const trackTitle = stateObj.attributes.track_title || '';
    const trackArtist = stateObj.attributes.track_artist || '';
    const enrichedTitle = stateObj.attributes.enriched_title || stateObj.state;
    const enrichedArtist = stateObj.attributes.enriched_artist || '';
    const imageUrl = stateObj.attributes.image_url || '';

    // Fallback to Sonos data if not NRK
    const displayTitle = isNrk ? enrichedTitle : (stateObj.attributes.media_title || stateObj.state);
    const displayArtist = isNrk ? enrichedArtist : (stateObj.attributes.media_artist || '');
    const displayImage = isNrk ? imageUrl : (stateObj.attributes.entity_picture || '');

    this.shadowRoot.innerHTML = `
      <style>
        ha-card {
          padding: 16px;
          display: flex;
          flex-direction: column;
          align-items: center;
        }
        .card-header {
          font-size: 1.2em;
          font-weight: bold;
          margin-bottom: 12px;
          color: var(--primary-text-color);
        }
        .artwork {
          width: 200px;
          height: 200px;
          border-radius: 8px;
          object-fit: cover;
          margin-bottom: 16px;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        }
        .artwork-placeholder {
          width: 200px;
          height: 200px;
          border-radius: 8px;
          background: var(--disabled-color);
          display: flex;
          align-items: center;
          justify-content: center;
          margin-bottom: 16px;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        }
        .artwork-placeholder ha-icon {
          --mdc-icon-size: 80px;
          color: var(--primary-background-color);
        }
        .info {
          text-align: center;
          width: 100%;
        }
        .title {
          font-size: 1.1em;
          font-weight: 500;
          margin-bottom: 8px;
          color: var(--primary-text-color);
        }
        .artist {
          font-size: 0.95em;
          color: var(--secondary-text-color);
          margin-bottom: 4px;
        }
        .station {
          font-size: 0.85em;
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
        ${this.config.show_header !== false ? `<div class="card-header">${this.config.name || 'Now Playing'}</div>` : ''}

        ${displayImage ?
          `<img class="artwork" src="${displayImage}" alt="Album artwork" />` :
          `<div class="artwork-placeholder">
            <ha-icon icon="mdi:${isNrk ? 'radio' : 'music'}"></ha-icon>
          </div>`
        }

        <div class="info">
          <div class="title">${displayTitle}</div>
          ${displayArtist ? `<div class="artist">${displayArtist}</div>` : ''}
          ${isNrk && programTitle ? `<div class="station">${stationName} – ${programTitle}</div>` : ''}
          ${isNrk ? '<div class="nrk-badge">NRK</div>' : ''}
        </div>
      </ha-card>
    `;
  }

  getCardSize() {
    return 4;
  }

  static getStubConfig() {
    return {
      entity: 'sensor.example_nrk',
      name: 'Now Playing',
      show_header: true
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
