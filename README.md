# Fridge Kiosk

A modular, plugin-based kiosk display system designed for Raspberry Pi.

## Features

- Plugin-based architecture for easy customization
- Supports multiple screen layouts and orientations
- Easily configurable through JSON files
- Lightweight system designed for Raspberry Pi
- Automatic installation and configuration

## Structure

```
fridge-kiosk/
├── backend/            # Backend Flask application
│   ├── app.py          # Main Flask app
│   ├── plugin_loader.py # Plugin loading system  
│   └── utils/          # Utility functions
│       └── config.py   # Configuration utilities
├── frontend/           # Frontend files
│   ├── index.html      # Main HTML template
│   ├── css/            # CSS files
│   │   └── main.css    # Main stylesheet
│   └── js/             # JavaScript files
│       └── main.js     # Main JavaScript
├── plugins/            # Plugin directories
│   └── sensors/        # Temperature & humidity plugin
│       ├── view.html   # Plugin HTML template
│       ├── __init__.py # Plugin main code
│       ├── config.json # Plugin configuration
│       ├── requirements.txt # Plugin dependencies
│       └── static/     # Static assets
│           ├── script.js  # Plugin JavaScript
│           └── style.css  # Plugin CSS
├── config/             # Configuration files
│   ├── main.json       # Main configuration
│   └── .env.example    # Environment variables template
├── scripts/            # Installation scripts
│   ├── setup_dependencies.sh  # Install dependencies
│   ├── install_kiosk.sh       # Main installation script (new combined version)
│   └── uninstall_kiosk.sh     # Complete uninstallation script
└── run.py              # Main application entry point
```

## Installation

1. On Raspberry Pi OS Light (64-bit) install git and clone the repository:
   ```
   sudo apt update
   sudo apt install -y git
   git clone https://github.com/petrasl1976/fridge-kiosk.git
   cd fridge-kiosk
   ```

2. Run the installation script:
   ```
   chmod +x scripts/install_kiosk.sh
   sudo ./scripts/install_kiosk.sh
   ```

3. Configure your .env file:
   ```
   vi config/.env
   ```

4. Enable or disable plugins in `config/main.json`

The installation script will:
- Install all required dependencies
- Configure the system for kiosk mode
- Set up systemd services for automatic startup
- Configure environment variables

## Uninstallation

To completely remove the Fridge Kiosk system:

```
sudo ./scripts/uninstall_kiosk.sh
```

This will:
- Stop and remove all services
- Remove configuration files
- Clean up data and logs
- Reset system changes
- Optionally remove installed packages

## Plugin Development

A plugin is a self-contained module that extends the functionality of the Fridge Kiosk system. The system is designed to be modular, allowing for easy addition and removal of plugins.

### Plugin Structure

Each plugin must follow this directory structure:

```
plugins/my_plugin/
├── __init__.py          # Main plugin code with required exports
├── view.html            # HTML template for your plugin
├── config.json          # Plugin configuration
├── main.py              # Optional API handlers (if needed)
├── requirements.txt     # Python dependencies
└── static/              # Static assets directory
    ├── script.js        # JavaScript implementation
    └── style.css        # CSS styles
```

### Required Files

1. **`__init__.py`**: The main plugin module that must export:
   - `PLUGIN_NAME`: String identifier for your plugin
   - `PLUGIN_VERSION`: Version number (e.g., "1.0.0")
   - `PLUGIN_DESCRIPTION`: Short description of your plugin
   - `setup(app)`: Function to initialize the plugin
   - `get_routes(app)`: Function to register any HTTP routes
   - `get_data()`: Function to return initial data for frontend
   - `cleanup()`: Function to release resources when plugin is disabled

2. **`view.html`**: HTML template for your plugin UI. This will be injected into the main page.

3. **`config.json`**: Configuration for your plugin, which will be loaded at startup.

4. **`static/script.js`**: JavaScript code for your plugin. **IMPORTANT:** Place script files in the `static/` subdirectory, not in the plugin root.

5. **`static/style.css`**: CSS styles for your plugin. **IMPORTANT:** Place style files in the `static/` subdirectory, not in the plugin root.

### Example Implementation

#### __init__.py
```python
#!/usr/bin/env python3
"""
My Plugin - Description of your plugin
"""
import os
import json
import logging

# Plugin information
PLUGIN_NAME = "my_plugin"
PLUGIN_VERSION = "1.0.0"
PLUGIN_DESCRIPTION = "Description of your plugin"

# Set up logging
logger = logging.getLogger(f"plugin.{PLUGIN_NAME}")

# Global variables
config = {}

def setup(app):
    """Set up the plugin"""
    global config
    
    logger.info(f"Setting up {PLUGIN_NAME} plugin")
    
    # Get the plugin directory
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Load plugin config
    config_path = os.path.join(plugin_dir, 'config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
    
    # Register routes if using Flask
    blueprint = Blueprint(PLUGIN_NAME, __name__)
    
    @blueprint.route(f'/api/plugins/{PLUGIN_NAME}/data')
    def get_plugin_data():
        # Your API endpoint
        return jsonify({"status": "ok"})
    
    # Register the blueprint
    app.register_blueprint(blueprint)
    
    return True

def get_routes(app):
    """Define plugin routes"""
    return [f'/api/plugins/{PLUGIN_NAME}/data']

def get_data():
    """Return initial data for frontend"""
    return {
        'config': config,
        'data': {},  # Any initial data
        'view': 'view.html',
        'script': 'static/script.js',
        'style': 'static/style.css'
    }

def cleanup():
    """Clean up resources"""
    logger.info(f"Cleaning up {PLUGIN_NAME} plugin")
    return True
```

#### view.html
```html
<div id="my-plugin-container" class="my-plugin">
    <h2 class="my-plugin-header">My Plugin</h2>
    <div class="my-plugin-content">
        <div id="my-plugin-data">Loading...</div>
    </div>
</div>
```

#### static/script.js
```javascript
/**
 * My Plugin for Fridge Kiosk
 */

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Get plugin container
    const container = document.getElementById('plugin-my_plugin');
    if (!container) {
        console.error('My plugin: Container not found');
        return;
    }
    
    // Access plugin config
    const config = window.KIOSK_CONFIG?.plugins?.my_plugin || {};
    const pluginData = window.PLUGINS_DATA?.my_plugin || {};
    
    // Your plugin initialization code here
    
    // Example: Update content periodically
    function fetchData() {
        fetch('/api/plugins/my_plugin/data')
            .then(response => response.json())
            .then(data => {
                // Update UI with data
                document.getElementById('my-plugin-data').textContent = 
                    JSON.stringify(data);
            })
            .catch(error => {
                console.error('Error fetching data:', error);
            });
    }
    
    // Initial fetch
    fetchData();
    
    // Set up periodic updates
    setInterval(fetchData, (config.updateInterval || 30) * 1000);
});
```

#### static/style.css
```css
.my-plugin {
    background-color: #f0f0f0;
    border-radius: 8px;
    padding: 16px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.my-plugin-header {
    font-size: 1.5rem;
    margin-bottom: 12px;
}

.my-plugin-content {
    font-size: 1.2rem;
}
```

#### config.json
```json
{
    "updateInterval": 30,
    "enabled": true,
    "customOptions": {
        "option1": "value1",
        "option2": "value2"
    }
}
```

### Adding New Plugins

1. Create a new directory in the `plugins/` directory
2. Add the required files as described above
3. Add your plugin to the `enabledPlugins` list in `config/main.json`
4. Run the dependencies setup script to install any new requirements:
   ```
   sudo ./scripts/setup_dependencies.sh
   ```
5. Restart the backend service:
   ```
   sudo systemctl restart fridge-kiosk-backend.service
   ```

### Best Practices

1. Keep your plugin as lightweight as possible
2. Use asynchronous operations for API calls
3. Handle errors gracefully
4. Store plugin-specific data in the `data/` subdirectory that's created automatically
5. Follow the existing code style and patterns
6. Always place JavaScript and CSS files in the `static/` subdirectory, not in the plugin root

## Services

The system uses two systemd services:

1. `fridge-kiosk-backend.service` - Runs the Python backend application
2. `fridge-kiosk-display.service` - Runs the Chromium browser in kiosk mode

To manage the services:
```
sudo systemctl {start|stop|restart|status} fridge-kiosk-backend.service
sudo systemctl {start|stop|restart|status} fridge-kiosk-display.service
```

## Adding New Plugins

After installing a new plugin:

1. Run the dependencies setup script to install any new requirements:
   ```
   sudo ./scripts/setup_dependencies.sh
   ```

2. Restart the backend service:
   ```
   sudo systemctl restart fridge-kiosk-backend.service
   ```

## License

MIT 