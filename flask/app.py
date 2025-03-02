import os
import logging
import sys
import time
import threading
from flask import Flask, render_template, request, jsonify
from pathlib import Path
from datetime import datetime

# Add parent directory to path to find birdcall_core module
sys.path.append(str(Path(os.path.dirname(os.path.abspath(__file__))).parent))

# Import from core module
from birdcall_core.config import load_config, save_config, get_log_level
from birdcall_core.downloader import run_xeno_download, run_ebird_download
from birdcall_core.utils import setup_logger

app = Flask(__name__)

# Set up base directories
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent
LOGS_DIR = BASE_DIR / "logs"

# Set up logging
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
logger = setup_logger(LOGS_DIR, name="flask", level=logging.INFO)

# Global progress tracking
progress = {
    'xeno': 0.0,
    'ebird': 0.0,
    'xeno_complete': False,
    'ebird_complete': False,
    'download_running': False,
    'status': 'Not started'
}

@app.route('/')
def index():
    """Render the single page application with values from config.json"""
    # Load existing configuration
    config = load_config()
    
    return render_template(
        'index.html', 
        config=config,
        backup_regions=','.join(config['ebird']['backup_region_codes'])
    )

def update_xeno_progress(progress_value):
    """Callback to update Xeno-Canto progress"""
    progress['xeno'] = float(progress_value)
    if progress_value >= 1.0:
        progress['xeno_complete'] = True
        logger.info("Xeno-Canto download complete")

def update_ebird_progress(progress_value):
    """Callback to update eBird progress"""
    progress['ebird'] = float(progress_value)
    if progress_value >= 1.0:
        progress['ebird_complete'] = True
        logger.info("eBird download complete")

@app.route('/start_download', methods=['POST'])
def start_download():
    """Update config.json and start the download process"""
    try:
        # Reset progress
        progress['xeno'] = 0.0
        progress['ebird'] = 0.0
        progress['xeno_complete'] = False
        progress['ebird_complete'] = False
        progress['download_running'] = True
        progress['status'] = 'Starting downloads...'
        
        # Get form data
        form_data = request.form
        
        # Get enabled download sources
        xeno_enabled = form_data.get('xeno_enabled') == 'on'
        ebird_enabled = form_data.get('ebird_enabled') == 'on'
        
        if not xeno_enabled and not ebird_enabled:
            return jsonify({
                "status": "error", 
                "message": "Please enable at least one download source (Xeno-Canto or eBird)."
            })
        
        # Process form data into config structure
        # Convert values with proper type handling
        xeno_min_length = form_data.get('xeno_min_length', '')
        xeno_max_length = form_data.get('xeno_max_length', '')
        xeno_better_than = form_data.get('xeno_better_than', '')
        xeno_max_per_species = form_data.get('xeno_max_per_species', '3')
        ebird_max_per_species = form_data.get('ebird_max_per_species', '3')
        
        # Type conversions
        xeno_min_length = int(xeno_min_length) if xeno_min_length and int(xeno_min_length) > 0 else None
        xeno_max_length = int(xeno_max_length) if xeno_max_length and int(xeno_max_length) > 0 else None
        xeno_better_than = xeno_better_than if xeno_better_than != "" else None
        backup_regions = [r.strip() for r in form_data.get('backup_regions', '').split(',') if r.strip()]
        
        # Create new config object
        config = {
            "download_dir": form_data.get('download_dir', str(Path.home() / "Downloads" / "BirdCalls")),
            "overwrite": False,  # Always false
            "verbosity": "warning",  # Fixed at warning
            "xeno": {
                "location": form_data.get('xeno_location', '') or None,
                "country": form_data.get('xeno_country', ''),
                "max_per_species": int(xeno_max_per_species),
                "better_than_rating": xeno_better_than,
                "min_length_seconds": xeno_min_length,
                "max_length_seconds": xeno_max_length
            },
            "ebird": {
                "api_key": form_data.get('ebird_api_key', ''),
                "region_code": form_data.get('ebird_region', ''),
                "backup_region_codes": backup_regions,
                "max_per_species": int(ebird_max_per_species)
            }
        }
            
        # Validate Xeno-Canto settings
        if xeno_enabled and not config["xeno"]["country"] and not config["xeno"]["location"]:
            return jsonify({
                "status": "error", 
                "message": "For Xeno-Canto downloads, either Country or Location must be specified."
            })
            
        # Validate eBird settings
        if ebird_enabled:
            if not config["ebird"]["api_key"]:
                return jsonify({
                    "status": "error", 
                    "message": "eBird API key is required for eBird/Macaulay Library downloads."
                })
                
            if not config["ebird"]["region_code"]:
                return jsonify({
                    "status": "error", 
                    "message": "Region code is required for eBird/Macaulay Library downloads."
                })
        
        # Save the new config to config.json
        if not save_config(config):
            return jsonify({
                "status": "error", 
                "message": "Failed to save configuration. Check logs for details."
            })
        
        # Create directories
        download_dir = Path(config["download_dir"])
        download_dir_xc = download_dir / "XC"
        download_dir_ml = download_dir / "ML"
        os.makedirs(download_dir_xc, exist_ok=True)
        os.makedirs(download_dir_ml, exist_ok=True)
        
        # Start download threads
        if xeno_enabled:
            xeno_thread = threading.Thread(
                target=run_xeno_download,
                args=(config, update_xeno_progress)
            )
            xeno_thread.daemon = True
            xeno_thread.start()
            logger.info("Started Xeno-Canto download thread")
        else:
            progress['xeno_complete'] = True
            progress['xeno'] = 1.0
        
        if ebird_enabled:
            ebird_thread = threading.Thread(
                target=run_ebird_download,
                args=(config, update_ebird_progress)
            )
            ebird_thread.daemon = True
            ebird_thread.start()
            logger.info("Started eBird download thread")
        else:
            progress['ebird_complete'] = True
            progress['ebird'] = 1.0
        
        return jsonify({
            "status": "success", 
            "message": "Configuration saved and downloads started"
        })
        
    except Exception as e:
        logger.error(f"Error starting download: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": f"Failed to start download: {str(e)}"
        })

@app.route('/progress')
def get_progress():
    """API endpoint to get current progress"""
    # Check if downloads are complete
    if progress['download_running']:
        if progress['xeno_complete'] and progress['ebird_complete']:
            progress['download_running'] = False
            progress['status'] = 'All downloads completed!'
            
    # Add timestamp to help the client determine freshness
    progress['timestamp'] = time.time()
    
    return jsonify(progress)

@app.route('/browse_directories', methods=['POST'])
def browse_directories():
    """List subdirectories of a specified path"""
    try:
        data = request.json
        base_path = data.get('path', str(Path.home()))
        
        # Ensure the path exists
        path = Path(base_path)
        if not path.exists() or not path.is_dir():
            return jsonify({
                "status": "error",
                "message": f"Directory not found: {base_path}"
            })
            
        # Get parent directory
        parent = str(path.parent) if str(path.parent) != str(path) else None
        
        # List subdirectories
        dirs = []
        try:
            for item in path.iterdir():
                if item.is_dir() and not item.name.startswith('.'):  # Skip hidden directories
                    dirs.append({
                        "path": str(item),
                        "name": item.name
                    })
        except PermissionError:
            return jsonify({
                "status": "error",
                "message": f"Permission denied accessing: {base_path}"
            })
            
        return jsonify({
            "status": "success",
            "current_path": str(path),
            "parent_path": parent,
            "directories": sorted(dirs, key=lambda x: x["name"].lower())
        })
    except Exception as e:
        logger.error(f"Error browsing directories: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error browsing directories: {str(e)}"
        })

@app.route('/create_folder', methods=['POST'])
def create_folder():
    """Create a new folder in the specified path"""
    try:
        data = request.json
        parent_path = data.get('path')
        folder_name = data.get('folder_name')
        
        if not parent_path or not folder_name:
            return jsonify({
                "status": "error",
                "message": "Missing parent path or folder name"
            })
            
        # Clean up folder name (remove problematic characters)
        import re
        folder_name = re.sub(r'[<>:"|?*\\\/]', '', folder_name).strip()
        
        if not folder_name:
            return jsonify({
                "status": "error",
                "message": "Invalid folder name"
            })
        
        # Create full path for new folder
        new_folder_path = Path(parent_path) / folder_name
        
        # Check if path already exists
        if new_folder_path.exists():
            return jsonify({
                "status": "error",
                "message": f"Folder '{folder_name}' already exists"
            })
        
        # Create the directory
        try:
            new_folder_path.mkdir(parents=False, exist_ok=False)
        except PermissionError:
            return jsonify({
                "status": "error",
                "message": f"Permission denied creating folder in '{parent_path}'"
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Error creating folder: {str(e)}"
            })
            
        return jsonify({
            "status": "success",
            "message": f"Folder '{folder_name}' created successfully",
            "path": str(new_folder_path)
        })
        
    except Exception as e:
        logger.error(f"Error creating folder: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error creating folder: {str(e)}"
        })

if __name__ == '__main__':
    app.run(debug=False, port=8000)
