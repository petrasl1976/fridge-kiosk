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
│   ├── services/       # Backend services
│   └── utils/          # Utility functions
├── frontend/           # Frontend files
│   ├── index.html      # Main HTML template
│   ├── css/            # CSS files
│   └── js/             # JavaScript files
├── plugins/            # Plugin directories
│   ├── google-photos/  # Google Photos plugin
│   ├── google-calendar/ # Google Calendar plugin
│   └── ...             # Other plugins
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

1. On Raspbery Pi OS Light (64-bit) install git and clone the repository:
   ```
   sudo apt install -y git
   git clone https://github.com/yourusername/fridge-kiosk.git
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
   vi config/.env
   ```

4. Enable or disable plugins in `config/main.json`

## Plugin Development

See the [Plugin Development Guide](docs/plugin-development.md) for information on creating custom plugins.

## License

MIT 