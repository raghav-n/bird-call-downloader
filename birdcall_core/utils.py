"""
Utility functions for bird call downloader.
"""
import os
import re
import logging
import requests
from pathlib import Path

def sanitize_filename(filename):
    """
    Sanitize a filename to remove or replace disallowed characters.
    """
    # Replace slashes with hyphens
    filename = filename.replace('/', '-').replace('\\', '-')
    
    # Remove other problematic characters often not allowed in filenames
    filename = re.sub(r'[<>:"|?*]', '', filename)
    
    # Trim excessive whitespace and periods
    filename = re.sub(r'\s+', ' ', filename).strip()
    filename = re.sub(r'\.+', '.', filename)
    
    # Ensure filename isn't too long (most filesystems have 255 byte limit)
    if len(filename.encode('utf-8')) > 240:  # Leave some room for extension
        filename = filename[:100] + '...' + filename[-100:]
        
    return filename

def download_file(save_loc, file_name, download_url, overwrite=False):
    """Download a single file"""
    # Sanitize the filename
    file_name = sanitize_filename(file_name)
    
    # Create directory if it doesn't exist
    if not os.path.isdir(save_loc):
        os.makedirs(save_loc, exist_ok=True)
    
    save_file_path = save_loc / file_name

    # Check if file exists and respect overwrite flag
    if not overwrite and os.path.exists(save_file_path):
        # File exists and we don't want to overwrite
        logging.debug(f"Skipping download: {save_file_path} (already exists)")
        return False

    try:
        # Only download if we need to
        rec_file = requests.get(download_url)
        rec_file.raise_for_status()
        
        with open(save_file_path, 'wb') as f:
            f.write(rec_file.content)
        
        logging.debug(f"Downloaded: {save_file_path}")
        return True
    except Exception as e:
        logging.error(f"Failed to download {file_name}: {str(e)}")
        return False

def setup_logger(log_dir, name="birdcall_downloader", level=logging.INFO):
    """Set up and return a configured logger"""
    from datetime import datetime
    
    # Create logs directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Generate timestamp for log filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"{name}_{timestamp}.log"
    log_filepath = os.path.join(log_dir, log_filename)
    
    # Configure logging
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Add handlers
    file_handler = logging.FileHandler(log_filepath)
    console_handler = logging.StreamHandler()
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logger.info(f"Log file created at: {log_filepath}")
    return logger
