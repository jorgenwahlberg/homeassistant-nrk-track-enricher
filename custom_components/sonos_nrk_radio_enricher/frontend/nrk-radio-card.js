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
    const oldHass = this._hass;
    this._hass = hass;

    // Only re-render if the entity state has actually changed
    if (this.config && this.config.entity) {
      const oldState = oldHass?.states[this.config.entity];
      const newState = hass.states[this.config.entity];

      // Check if state or attributes changed
      if (!oldState ||
          oldState.state !== newState?.state ||
          JSON.stringify(oldState.attributes) !== JSON.stringify(newState?.attributes)) {
        this.render();
      }
    } else {
      this.render();
    }
  }

  render() {
    if (!this._hass || !this.config) {
      return;
    }

    const entityId = this.config.entity;
    const stateObj = this._hass.states[entityId];

    // Store state reference for click handler access
    this._stateObj = stateObj;

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
    const sonosEntityId = stateObj.attributes.sonos_entity_id || '';

    // Debug: Log if sonos_entity_id is present
    if (sonosEntityId) {
      console.debug('NRK Card: Found Sonos entity ID:', sonosEntityId);
    } else {
      console.debug('NRK Card: No Sonos entity ID found in attributes:', stateObj.attributes);
    }

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

    // For NRK: Show station and program on first line
    // For non-NRK: Show media_title as before
    const displayTitle = isNrk
      ? `${stationName}${programTitle ? ' – ' + programTitle : ''}`
      : (stateObj.attributes.media_title || stateObj.state);

    // For NRK: Show track title and artist on separate lines (only if they exist)
    // For non-NRK: Keep artist as second line
    const displayTrackTitle = isNrk && trackTitle ? trackTitle : '';
    const displayTrackArtist = isNrk && trackArtist ? trackArtist : '';
    const displayArtist = !isNrk ? (stateObj.attributes.media_artist || '') : '';

    this.shadowRoot.innerHTML = `
      <style>
        ha-card {
          position: relative;
          padding: 16px;
          display: flex;
          flex-direction: ${isHorizontal ? 'row' : 'column'};
          align-items: ${isHorizontal ? 'center' : 'center'};
          gap: ${isHorizontal ? '16px' : '0'};
        }
        .card-header {
          font-size: 1.2em;
          font-weight: bold;
          color: var(--primary-text-color);
          margin-bottom: ${isHorizontal ? '0' : '8px'};
          ${isHorizontal ? '' : 'width: 100%;'}
        }
        .control-icon {
          position: absolute;
          top: 8px;
          right: 8px;
          z-index: 1;
        }
        .control-icon ha-icon-button {
          --mdc-icon-button-size: 32px;
          --mdc-icon-size: 20px;
          color: var(--secondary-text-color);
          cursor: pointer;
        }
        .control-icon ha-icon-button:hover {
          color: var(--primary-text-color);
        }
        .artwork-container {
          ${isHorizontal ? 'flex-shrink: 0;' : ''}
        }
        .artwork {
          width: ${isHorizontal ? '72px' : '120px'};
          height: ${isHorizontal ? '72px' : '120px'};
          border-radius: 8px;
          object-fit: cover;
          margin-bottom: ${isHorizontal ? '0' : '8px'};
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        }
        .artwork-placeholder {
          width: ${isHorizontal ? '72px' : '120px'};
          height: ${isHorizontal ? '72px' : '120px'};
          border-radius: 8px;
          background: var(--disabled-color);
          display: flex;
          align-items: center;
          justify-content: center;
          margin-bottom: ${isHorizontal ? '0' : '8px'};
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        }
        .artwork-placeholder ha-icon {
          --mdc-icon-size: ${isHorizontal ? '36px' : '48px'};
          color: var(--primary-background-color);
        }
        .info {
          text-align: ${isHorizontal ? 'left' : 'center'};
          width: 100%;
          ${isHorizontal ? 'flex-grow: 1; display: flex; flex-direction: column; justify-content: center;' : ''}
        }
        .title {
          font-size: ${isHorizontal ? '0.95em' : '1.0em'};
          font-weight: 500;
          margin-bottom: 4px;
          color: var(--primary-text-color);
          line-height: 1.3;
        }
        .track-title {
          font-size: ${isHorizontal ? '0.85em' : '0.9em'};
          color: var(--secondary-text-color);
          margin-bottom: 2px;
          line-height: 1.3;
        }
        .track-artist {
          font-size: ${isHorizontal ? '0.8em' : '0.85em'};
          color: var(--secondary-text-color);
          margin-bottom: 2px;
          line-height: 1.3;
        }
        .artist {
          font-size: ${isHorizontal ? '0.85em' : '0.9em'};
          color: var(--secondary-text-color);
          margin-bottom: 2px;
          line-height: 1.3;
        }
      </style>
      <ha-card>
        ${sonosEntityId ? `
          <div class="control-icon">
            <ha-icon-button class="control-button">
              <ha-icon icon="mdi:cast-audio"></ha-icon>
            </ha-icon-button>
          </div>
        ` : ''}

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
          ${displayTrackTitle ? `<div class="track-title">${displayTrackTitle}</div>` : ''}
          ${displayTrackArtist ? `<div class="track-artist">${displayTrackArtist}</div>` : ''}
          ${displayArtist ? `<div class="artist">${displayArtist}</div>` : ''}
        </div>
      </ha-card>
    `;

    // Attach click handler to control button(s) if they exist
    const controlButtons = this.shadowRoot.querySelectorAll('.control-button');
    controlButtons.forEach(button => {
      button.addEventListener('click', (e) => this._handleControlClick(e));
    });
  }

  _handleControlClick(e) {
    e.stopPropagation(); // Prevent card click events

    const sonosEntityId = this._stateObj?.attributes?.sonos_entity_id;
    if (!sonosEntityId) {
      console.warn('No Sonos entity ID found');
      return;
    }

    // Fire the standard HA more-info event
    const event = new Event('hass-more-info', {
      bubbles: true,
      composed: true,
    });
    event.detail = { entityId: sonosEntityId };
    this.dispatchEvent(event);
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

  static getConfigElement() {
    return document.createElement('nrk-radio-card-editor');
  }
}

class NRKRadioCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  setConfig(config) {
    this._config = config;
    this.render();
  }

  set hass(hass) {
    this._hass = hass;
    this._updateEntityPicker();
  }

  configChanged(newConfig) {
    const event = new Event('config-changed', {
      bubbles: true,
      composed: true,
    });
    event.detail = { config: newConfig };
    this.dispatchEvent(event);
  }

  render() {
    if (!this._config) {
      return;
    }

    this.shadowRoot.innerHTML = `
      <style>
        .card-config {
          padding: 16px;
        }
        .option {
          margin-bottom: 16px;
        }
        .option label {
          display: block;
          margin-bottom: 4px;
          font-weight: 500;
          color: var(--primary-text-color);
        }
        ha-entity-picker,
        ha-textfield {
          width: 100%;
        }
        select.layout-select {
          width: 100%;
          padding: 8px;
          border-radius: 4px;
          border: 1px solid var(--divider-color);
          background-color: var(--card-background-color);
          color: var(--primary-text-color);
          font-size: 14px;
          font-family: inherit;
          cursor: pointer;
        }
        select.layout-select:focus {
          outline: 2px solid var(--primary-color);
          outline-offset: 1px;
        }
        .switch-option {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 16px;
        }
        .switch-option label {
          margin: 0;
          font-weight: 500;
          color: var(--primary-text-color);
        }
      </style>
      <div class="card-config">
        <div class="option">
          <label>Entity (required)</label>
          <ha-entity-picker
            id="entity-picker"
            value="${this._config.entity || ''}"
            include-domains='["sensor"]'
            allow-custom-entity
          ></ha-entity-picker>
        </div>

        <div class="option">
          <label>Name</label>
          <ha-textfield
            id="name-input"
            value="${this._config.name || 'Now Playing'}"
            placeholder="Now Playing"
          ></ha-textfield>
        </div>

        <div class="switch-option">
          <label>Show header</label>
          <ha-switch
            id="header-switch"
            ${this._config.show_header !== false ? 'checked' : ''}
          ></ha-switch>
        </div>

        <div class="option">
          <label>Layout</label>
          <select
            id="layout-select"
            class="layout-select"
          >
            <option value="square" ${this._config.layout === 'square' || !this._config.layout ? 'selected' : ''}>Square</option>
            <option value="horizontal" ${this._config.layout === 'horizontal' ? 'selected' : ''}>Horizontal</option>
          </select>
        </div>
      </div>
    `;

    this._attachEventListeners();
  }

  _updateEntityPicker() {
    const picker = this.shadowRoot?.getElementById('entity-picker');
    if (picker && this._hass) {
      picker.hass = this._hass;
    }
  }

  _attachEventListeners() {
    const entityPicker = this.shadowRoot.getElementById('entity-picker');
    const nameInput = this.shadowRoot.getElementById('name-input');
    const headerSwitch = this.shadowRoot.getElementById('header-switch');
    const layoutSelect = this.shadowRoot.getElementById('layout-select');

    if (entityPicker) {
      entityPicker.addEventListener('value-changed', (ev) => {
        this._valueChanged('entity', ev.detail.value);
      });
      if (this._hass) {
        entityPicker.hass = this._hass;
      }
    }

    if (nameInput) {
      nameInput.addEventListener('input', (ev) => {
        this._valueChanged('name', ev.target.value);
      });
    }

    if (headerSwitch) {
      headerSwitch.addEventListener('change', (ev) => {
        this._valueChanged('show_header', ev.target.checked);
      });
    }

    if (layoutSelect) {
      layoutSelect.addEventListener('change', (ev) => {
        this._valueChanged('layout', ev.target.value);
      });
    }
  }

  _valueChanged(key, value) {
    if (!this._config) {
      return;
    }
    const newConfig = { ...this._config, [key]: value };
    this.configChanged(newConfig);
  }
}

// Define custom elements only if not already defined
if (!customElements.get('nrk-radio-card')) {
  customElements.define('nrk-radio-card', NRKRadioCard);
}
if (!customElements.get('nrk-radio-card-editor')) {
  customElements.define('nrk-radio-card-editor', NRKRadioCardEditor);
}

// Register the card with the card picker (only once)
window.customCards = window.customCards || [];
if (!window.customCards.find(card => card.type === 'nrk-radio-card')) {
  window.customCards.push({
    type: 'nrk-radio-card',
    name: 'NRK Radio Card',
    description: 'Display NRK radio playback information with artwork',
    preview: true,
    documentationURL: 'https://github.com/jorgenwahlberg/homeassistant-nrk-track-enricher'
  });
}
