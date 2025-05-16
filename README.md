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
│   ├── setup_environment.sh   # Configure environment
│   └── setup_service.sh       # Setup systemd service
└── install.sh          # Main installation script
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
   chmod +x install.sh
   ./install.sh
   ```

3. Configure your .env file:
   ```
   cp config/.env.example config/.env
   nano config/.env
   ```

4. Enable or disable plugins in `config/main.json`

The installation script will:
- Install all required dependencies
- Configure the system for kiosk mode
- Set up systemd services for automatic startup
- Configure environment variables

## Plugin Development

To create a new plugin:

1. Create a directory for your plugin in the `plugins/` directory
2. Create the necessary files:
   - `view.html` - HTML template for your plugin
   - `__init__.py` - Main plugin code
   - `config.json` - Plugin configuration
   - `static/script.js` - JavaScript for your plugin
   - `static/style.css` - CSS styles for your plugin
   - `requirements.txt` - Python dependencies for your plugin

3. Add your plugin to the enabled_plugins list in `config/main.json`

Refer to the sensors plugin for an example implementation.

## Services

The system uses three systemd services:

1. `fridge-kiosk-backend.service` - Runs the Flask backend application
2. `fridge-kiosk-display.service` - Runs the Chromium browser in kiosk mode
3. `fridge-kiosk.service` - Master service that manages both backend and display

To manage the services:
```
sudo systemctl {start|stop|restart|status} fridge-kiosk
```

## License

MIT 