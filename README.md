# Bird Call Downloader

This tool automatically downloads bird call recordings from Xeno-Canto and eBird/Macaulay Library based on your configuration.

## Project Structure

```
/calls/
├── birdcall_core/           # Shared core module
│   ├── __init__.py
│   ├── config.py            # Configuration handling
│   ├── downloader.py        # Core download functionality
│   └── utils.py             # Shared utilities
├── flask/                   # Flask web interface
│   ├── app.py
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   └── templates/
├── main.py                  # Command-line interface
└── config.json              # Configuration file
```

## Setup

### Prerequisites
- Python 3.7 or higher
- pip (Python package installer)

### Installation

1. Clone or download this repository
2. Install the required packages:

```bash
# Navigate to the project directory
cd /path/to/bird-call-downloader

# Create a virtual environment
python3 -m venv .venv

# Activate it (Windows)
.\.venv\Scripts\activate

# Activate it (Mac/Linux)
source .venv/bin/activate

# Install dependencies
python3 -m pip install -r requirements.txt
```

## Usage

### Flask Web Interface (recommended)

The tool provides a web-based interface for easy configuration and monitoring:

```bash
cd /path/to/bird-call-downloader
python flask/app.py
```

Then open your browser and navigate to: `http://localhost:8000`

The web interface includes:
- Configuration form to set all download parameters
- Real-time progress tracking
- Parallel downloads from both sources

### Command Line

Alternatively, you can use the command-line version:

```bash
python main.py
```

The command-line interface reads from the same config.json file and provides progress bars during download.

## Configuration Options

All settings are controlled through the `config.json` file:

```json
{
  "download_dir": "/path/to/downloads",
  "overwrite": false,
  "verbosity": "info",
  "xeno": {
    "location": null,
    "country": "malaysia",
    "max_per_species": 5,
    "better_than_rating": "C",
    "min_length_seconds": null,
    "max_length_seconds": 300
  },
  "ebird": {
    "api_key": "your_ebird_api_key",
    "region_code": "MY-06",
    "backup_region_codes": ["SG", "MY", "TH"],
    "max_per_species": 5
  }
}
```

### General Settings

- `download_dir`: The directory where recordings will be saved
- `overwrite`: If `true`, existing files will be overwritten; if `false`, existing files will be skipped
- `verbosity`: Logging detail level - choose from "debug", "info", "warning", "error", or "critical"

### Xeno-canto Settings

- `country`: Country to download recordings from (use full name like "malaysia")
- `location`: Specific location within a country (leave as `null` to search entire country)
- `max_per_species`: Maximum number of recordings to download per species
- `better_than_rating`: Only download recordings with quality better than this rating (A=best through E=worst)
- `min_length_seconds`: Minimum recording length in seconds (leave as `null` for no minimum)
- `max_length_seconds`: Maximum recording length in seconds (leave as `null` for no maximum)

### eBird/Macaulay Library Settings

- `api_key`: Your eBird API key (get one from https://ebird.org/api/keygen)
- `region_code`: Primary region code to search for recordings (e.g., "MY" for Malaysia, "MY-06" for Pahang state)
- `backup_region_codes`: List of additional region codes to search if not enough recordings found in primary region
- `max_per_species`: Maximum number of recordings to download per species

## Downloader Overview

The downloader works by retrieving audio files from two separate sources in parallel:

### Xeno-Canto Download Process
1. **API Query**: The tool constructs a query to the Xeno-Canto API using parameters like country, location, and quality rating
2. **Pagination**: It retrieves all pages of results for the specified query
3. **Filtering**: Recordings are grouped by species and sorted by quality rating (A-E)
4. **Selection**: For each species, the tool selects up to the configured maximum number of highest-quality recordings
5. **Download**: Files are downloaded and saved to species-specific folders with metadata in the filename

### eBird/ML Download Process
1. **Species List**: The tool uses the eBird API to get a complete list of species for the specified region
2. **Catalog Search**: For each species, it searches the Macaulay Library web catalog for audio recordings
3. **Regional Fallback**: If not enough recordings are found in the primary region, it tries the backup regions
4. **Selection**: For each species, it retrieves the highest-rated recordings up to the configured maximum
5. **Download**: Files are downloaded to species-specific folders with location and observer information

The downloads run in parallel threads, with progress tracked independently for each source and displayed in real-time in the web interface.

## File Organization

Downloaded files are organized as follows:

```
download_dir/
├── XC/                          # Xeno-Canto recordings
│   ├── Species Name/
│   │   ├── (Quality) Species Name; Location; Recordist; XC123456.mp3
│   │   └── ...
├── ML/                          # Macaulay Library recordings
│   ├── Species Name/
│   │   ├── Species Name; Location; Observer; ML123456.mp3
│   │   └── ...
```

## Logs

Logs are stored in the `logs` folder, with a timestamp in the filename to track different download sessions.