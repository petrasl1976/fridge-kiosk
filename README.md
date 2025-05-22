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
├── backend/            # Backend application
│   ├── run.py          # Main backend entry point
│   ├── plugin_loader.py # Plugin loading system  
│   ├── templates/      # HTML templates and frontend assets
│   │   ├── index.html  # Main HTML template
│   │   ├── css/        # CSS files
│   │   │   └── main.css # Main stylesheet
│   │   └── js/         # JavaScript files
│   │       └── main.js # Main JavaScript
│   └── utils/          # Utility functions
│       ├── config.py   # Configuration utilities
│       └── auth/       # Authentication utilities
│           └── google_auth_server.py  # Centralized Google OAuth server
├── plugins/            # Plugin directories
│   └── date-time/      # Date & time display plugin
│       ├── view.html   # Plugin HTML template
│       ├── main.py     # Plugin main code
│       ├── config.json # Plugin configuration
│       ├── requirements.txt # Plugin dependencies (optional)
│       └── static/     # Static assets
│           ├── script.js  # Plugin JavaScript
│           └── style.css  # Plugin CSS
├── config/             # Configuration files
│   ├── main.json       # Main configuration
│   └── .env.example    # Environment variables template
├── scripts/            # Installation scripts
│   ├── install.sh      # Package installation and Python venv setup
│   ├── setup.sh        # System configuration and services setup 
│   ├── uninstall.sh    # Complete uninstallation script
│   └── fridge-kiosk-display.sh  # Kiosk display launch script
```

## Installation

1. On Raspberry Pi OS Light (64-bit) install git and clone the repository:
   ```
   sudo apt update
   sudo apt install -y git
   git clone https://github.com/petrasl1976/fridge-kiosk.git
   cd fridge-kiosk
   ```

2. Install dependencies first:
   ```
   chmod +x scripts/install.sh
   sudo ./scripts/install.sh
   ```

3. Set up system services and configuration:
   ```
   chmod +x scripts/setup.sh
   sudo ./scripts/setup.sh
   ```

4. Configure your .env file:
   ```
   vi config/.env
   ```

5. Enable or disable plugins in `config/main.json`

The installation scripts will:
- Install all required dependencies
- Configure the system for kiosk mode
- Set up systemd services for automatic startup
- Configure environment variables

## Uninstallation

To completely remove the Fridge Kiosk system:

```
sudo ./scripts/uninstall.sh
```

This will:
- Stop and remove all services
- Remove configuration files
- Clean up data and logs
- Reset system changes

## Plugin Development

A plugin is a self-contained module that extends the functionality of the Fridge Kiosk system. The system is designed to be modular, allowing for easy addition and removal of plugins.

### Plugin Structure

Each plugin must follow this directory structure:

```
plugins/my_plugin/
├── requirements.txt    # Python dependencies (optional)
├── config.json         # Plugin configuration
├── main.py             # Main plugin code with API endpoints
├── view.html           # HTML template for your plugin
└── static/             # Static assets directory
    ├── script.js       # JavaScript implementation
    └── style.css       # CSS styles
```

### Required Plugin Components

To create a working plugin, you need these essential components:

1. **main.py**: Backend file with two required functions:
   - `init(config)`: Called once at startup to initialize the plugin
   - `api_data()`: Called when frontend requests fresh data

2. **view.html**: Simple HTML template for your plugin's UI

3. **config.json**: Configuration including:
   - `position`: Screen positioning for different orientations
   - `updateInterval`: Refresh rate in seconds

4. **static/script.js**: JavaScript file with these key parts:
   - `document.addEventListener('DOMContentLoaded', ...)`: Entry point that runs when page loads
   - Main initialization function: Sets up elements and periodically fetches new data
   - Data fetching function: Gets data from API, updates UI, and handles errors

5. **static/style.css**: CSS styling for your plugin's UI

For a complete working example, see the `plugins/date-time` directory in the codebase.

### Plugin Loading Process

1. The backend reads your `config.json` to configure the plugin
2. It calls `main.py:init()` once at startup to get initial data
3. The frontend loads `view.html` and injects it into the page
4. Frontend JavaScript loads and uses your `script.js` to add dynamic behavior
5. Your script periodically calls `/api/plugins/your-plugin/data`, which invokes `main.py:api_data()`

### Adding New Plugins

1. Create a new directory in the `plugins/` directory
2. Add the required files as described above
3. Add your plugin to the `enabledPlugins` list in `config/main.json`
4. Run the dependencies setup script to install any new requirements:
   ```
   sudo ./scripts/install.sh
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

## License

MIT 