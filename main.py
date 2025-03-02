"""
Command-line interface for bird call downloader.
"""
import os
import threading
from pathlib import Path
import logging
from tqdm import tqdm

# Import from core module
from birdcall_core.config import load_config, get_log_level
from birdcall_core.downloader import run_xeno_download, run_ebird_download
from birdcall_core.utils import setup_logger

def run_with_progress_bar(func, config, desc):
    """Wrap a download function with a progress bar"""
    pbar = tqdm(total=100, desc=desc)
    last_progress = 0
    downloaded_count = [0]  # Use list to make it mutable in the closure
    
    def progress_callback(progress):
        nonlocal last_progress
        current = int(progress * 100)
        pbar.update(current - last_progress)
        last_progress = current
    
    result = func(config, progress_callback)
    downloaded_count[0] = result
    pbar.close()
    return downloaded_count[0]

def main():
    """Main entry point for command line interface"""
    # Load configuration
    config = load_config()
    
    # Setup logging
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir = os.path.join(script_dir, "logs")
    log_level = get_log_level(config)
    logger = setup_logger(logs_dir, level=log_level)
    
    # Create download directories
    download_dir = Path(config["download_dir"])
    download_dir_xc = download_dir / "XC"
    download_dir_ml = download_dir / "ML"
    os.makedirs(download_dir_xc, exist_ok=True)
    os.makedirs(download_dir_ml, exist_ok=True)
    
    # Initialize counters
    xc_count, ml_count = 0, 0
    
    # Validate Xeno-Canto settings
    xc_valid = bool(config["xeno"]["country"] or config["xeno"]["location"])
    if not xc_valid:
        logger.warning("Skipping Xeno-Canto download: neither country nor location specified")
    
    # Validate eBird settings
    ml_valid = bool(config["ebird"]["api_key"] and config["ebird"]["region_code"])
    if not ml_valid:
        logger.warning("Skipping eBird download: API key or region code not specified")
    
    # Use threads for parallel downloads
    if xc_valid and ml_valid:
        # If both are valid, use threading for parallel downloads
        xeno_thread = threading.Thread(
            target=lambda: run_with_tqdm(run_xeno_download, config, "XC download:     ", lambda x: setattr(xc_count, 'value', x))
        )
        ebird_thread = threading.Thread(
            target=lambda: run_with_tqdm(run_ebird_download, config, "eBird download: ", lambda x: setattr(ml_count, 'value', x))
        )
        
        # Class to hold mutable value
        class Counter:
            value = 0
        
        xc_count = Counter()
        ml_count = Counter()
        
        xeno_thread.start()
        ebird_thread.start()
        
        xeno_thread.join()
        ebird_thread.join()
        
        xc_files = xc_count.value
        ml_files = ml_count.value
    else:
        # If only one is valid, run it directly
        xc_files = run_with_progress_bar(run_xeno_download, config, "XC download:     ") if xc_valid else 0
        ml_files = run_with_progress_bar(run_ebird_download, config, "eBird download: ") if ml_valid else 0
    
    # Print summary
    print("\nDownload Summary:")
    print(f"- Xeno-Canto: {xc_files} files")
    print(f"- eBird/ML: {ml_files} files")
    print(f"- Total: {xc_files + ml_files} files")
    print("\nAll downloads completed!")

# Define a simpler version of run_with_tqdm for threading usage
def run_with_tqdm(func, config, desc, setter_func):
    """Run function with tqdm progress bar and set the result using a setter function"""
    pbar = tqdm(total=100, desc=desc)
    last_progress = 0
    
    def progress_callback(progress):
        nonlocal last_progress
        current = int(progress * 100)
        pbar.update(current - last_progress)
        last_progress = current
    
    result = func(config, progress_callback)
    setter_func(result)  # Set the result using the provided function
    pbar.close()

if __name__ == "__main__":
    main()
