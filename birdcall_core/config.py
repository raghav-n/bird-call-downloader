"""
Configuration handling for bird call downloader.
"""
import os
import json
import logging
from pathlib import Path

# Verbosity level mapping
VERBOSITY_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL
}

def get_config_path():
    """Get the path to the config.json file"""
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(script_dir, "config.json")

def load_config():
    """Load configuration from config.json"""
    config_path = get_config_path()
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
            return config
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Error loading config: {str(e)}")
        return {
            "download_dir": str(Path.home() / "Downloads" / "BirdCalls"),
            "overwrite": False,
            "verbosity": "warning",
            "xeno": {
                "location": None,
                "country": "",
                "max_per_species": 3,
                "better_than_rating": "C",
                "min_length_seconds": None,
                "max_length_seconds": 300
            },
            "ebird": {
                "api_key": "",
                "region_code": "",
                "backup_region_codes": [],
                "max_per_species": 3
            }
        }

def save_config(config_data):
    """Save configuration to config.json"""
    config_path = get_config_path()
    try:
        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=2)
        return True
    except Exception as e:
        logging.error(f"Error saving config: {str(e)}")
        return False

def get_log_level(config=None):
    """Get log level from config or return default INFO level"""
    if config is None:
        config = load_config()
    
    verbosity = config.get("verbosity", "info").lower()
    return VERBOSITY_LEVELS.get(verbosity, logging.INFO)
