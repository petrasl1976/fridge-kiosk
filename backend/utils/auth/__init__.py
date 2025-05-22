"""
Authentication utilities for Fridge Kiosk application.
This module provides centralized OAuth2 authentication for various services.
"""

from pathlib import Path

# Important paths
MODULE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = MODULE_DIR / "templates"
PROJECT_ROOT = MODULE_DIR.parent.parent.parent

# Create templates directory if it doesn't exist
TEMPLATES_DIR.mkdir(exist_ok=True) 