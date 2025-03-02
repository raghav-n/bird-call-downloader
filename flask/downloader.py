import os
import re
import json
import time
import logging
import requests
from pathlib import Path
from bs4 import BeautifulSoup

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

def run_xeno_threaded(config, progress_callback):
    """Download recordings from Xeno-Canto with progress updates"""
    download_dir = Path(config["download_dir"])
    download_dir_xc = download_dir / "XC"
    overwrite = config["overwrite"]
    
    # Extract Xeno-Canto settings
    xeno_location = config["xeno"]["location"]
    xeno_country = config["xeno"]["country"]
    xeno_better_than = config["xeno"]["better_than_rating"]
    xeno_min_length = config["xeno"]["min_length_seconds"]
    xeno_max_length = config["xeno"]["max_length_seconds"]
    max_per_species = config["xeno"]["max_per_species"]
    
    try:
        # Ensure at least one search parameter is specified
        if not xeno_country and not xeno_location:
            logging.error("Either country or location must be specified for Xeno-Canto downloads.")
            progress_callback(1.0)  # Mark as complete
            return
        
        # Prepare API query
        base_url = "https://xeno-canto.org/api/2/recordings"
        query_params = ["grp:\"birds\""]
        
        if xeno_location:
            query_params.append(f"loc:{xeno_location}")
        if xeno_country:
            query_params.append(f"cnt:{xeno_country}")
        if xeno_better_than:
            query_params.append(f"q:\">{xeno_better_than}\"")
        if xeno_min_length:
            query_params.append(f"len_gt:{xeno_min_length}")
        if xeno_max_length:
            query_params.append(f"len_lt:{xeno_max_length}")
        
        # Make initial request to get page count
        logging.info(f"Fetching Xeno-Canto data with params {query_params}...")
        response = requests.get(f"{base_url}?query={'+'.join(query_params)}", timeout=30)
        data = response.json()
        
        num_pages = data.get("numPages", 0)
        logging.info(f"Found {num_pages} pages of Xeno-Canto data")
        
        if num_pages == 0:
            logging.warning("No recordings found on Xeno-Canto")
            progress_callback(1.0)  # Mark as complete
            return

        all_recordings = []
        
        # Fetch all pages
        for idx in range(num_pages):
            progress_percent = (idx / max(1, num_pages)) * 0.1
            progress_callback(progress_percent)
            logging.info(f"Loading Xeno-Canto recordings page {idx+1}/{num_pages}...")
            
            rec_response = requests.get(f"{base_url}?query={'+'.join(query_params)}&page={idx + 1}", timeout=30)
            rec_data = rec_response.json()
            all_recordings += rec_data["recordings"]
        
        # Group recordings by species
        logging.info("Processing recordings by species...")
        recordings_by_species = {}
        for rec in all_recordings:
            species = rec["en"]
            if species not in recordings_by_species:
                recordings_by_species[species] = []
            recordings_by_species[species].append(rec)
        
        # Sort each species' recordings by quality (A is highest, E is lowest)
        for species, recordings in recordings_by_species.items():
            recordings.sort(key=lambda x: 'ABCDE'.index(x['q'][0]) if x['q'] and x['q'][0] in 'ABCDE' else 999)
        
        # Limit each species to max_per_species recordings
        filtered_recordings = []
        for species, recordings in recordings_by_species.items():
            filtered_recordings.extend(recordings[:max_per_species])
        
        download_args_list = [
            [Path(download_dir_xc / sanitize_filename(rec["en"])), 
            f"({rec['q']}) {rec['en']}; {rec['loc']}; {rec['rec']}; XC{rec['id']}.mp3",
            rec["file"]]
            for rec in filtered_recordings if rec["file"] and rec["en"]
        ]
        
        # Download files with progress updates
        num_downloads = len(download_args_list)
        logging.info(f"Downloading {num_downloads} Xeno-Canto recordings...")
        progress_callback(0.3)  # Mark completion of preparation phase
        
        for i, args in enumerate(download_args_list):
            progress_percent = 0.3 + ((i / max(1, num_downloads)) * 0.7)
            progress_callback(progress_percent)
            
            req = download_file(*args, overwrite=overwrite)
            if req:
                time.sleep(0.5)  # Rate limiting but faster than before
        
        logging.info(f"Completed Xeno-Canto downloads: {num_downloads} files")
        progress_callback(1.0)  # Mark as complete
        
    except Exception as e:
        logging.error(f"Error in Xeno-Canto download: {str(e)}")
        progress_callback(1.0)  # Mark as complete even on error

def run_ebird_threaded(config, progress_callback):
    """Download recordings from eBird/ML with progress updates"""
    download_dir = Path(config["download_dir"])
    download_dir_ml = download_dir / "ML"
    overwrite = config["overwrite"]
    
    try:
        # Extract eBird settings
        api_key = config["ebird"]["api_key"]
        region_code = config["ebird"]["region_code"]
        backup_regions = config["ebird"]["backup_region_codes"]
        max_per_species = config["ebird"]["max_per_species"]
        
        if not api_key:
            logging.error("eBird API key is required for Macaulay Library downloads.")
            progress_callback(1.0)  # Mark as complete
            return
            
        if not region_code:
            logging.error("eBird region code is required for Macaulay Library downloads.")
            progress_callback(1.0)  # Mark as complete
            return
        
        # Get species list for the region
        logging.info(f"Fetching species list for region {region_code}...")
        base_url_sp_list = f"https://api.ebird.org/v2/product/spplist/{region_code}"
        response_sp_list = requests.get(f"{base_url_sp_list}?key={api_key}", timeout=30)
        
        try:
            ebird_taxon_codes = response_sp_list.json()
        except json.JSONDecodeError:
            error_msg = f"Failed to get species list. Check your API key and region code."
            logging.error(error_msg)
            progress_callback(1.0)  # Mark as complete
            return
        
        # Get taxonomy information
        taxonomy_url = f"https://api.ebird.org/v2/ref/taxonomy/ebird?key={api_key}&fmt=json"
        response_taxonomy = requests.get(taxonomy_url, timeout=30)
        taxonomy = {x["speciesCode"]: x["comName"] for x in response_taxonomy.json()}
        
        # Prepare for download
        total_species = len(ebird_taxon_codes)
        file_count = 0
        
        progress_callback(0.0)
        
        # Process each species
        for i, ebird_taxon_code in enumerate(ebird_taxon_codes):
            progress_percent = i / total_species
            progress_callback(progress_percent)
            
            downloaded_assets = []
            backup_regions_iter = iter(backup_regions + [None])
            
            try:
                species = taxonomy[ebird_taxon_code]
            except KeyError:
                # Skip if species not found in taxonomy
                continue
                
            # Sanitize species name for directory path
            sanitized_species = sanitize_filename(species)
            logging.info(f"Processing {i+1}/{total_species}: {species}")
            
            query = f"taxonCode={ebird_taxon_code}&mediaType=audio&sort=rating_rank_desc&view=grid"
            query_region = f"&regionCode={region_code}"
            
            # Search for recordings, using backup regions if needed
            while len(downloaded_assets) < max_per_species:
                response = requests.get(f"https://media.ebird.org/catalog?{query}{query_region}", timeout=30)
                bs = BeautifulSoup(response.text, features="html.parser")
                entries = bs.find_all("li", class_="ResultsGrid-card")
                
                # If no entries found, try next region
                if not entries:
                    try:
                        next_region = next(backup_regions_iter)
                        query_region = f"&regionCode={next_region}" if next_region else ""
                        continue
                    except StopIteration:
                        break
                
                assets = [
                    [entry.find('div', attrs={'data-asset-id': True})['data-asset-id'],
                    entry.find("div", class_="userDateLoc").find_all("a")[0].text if entry.find("div", class_="userDateLoc").find_all("a") else None,
                    entry.find("div", class_="userDateLoc").find_all("span")[-1].text if entry.find("div", class_="userDateLoc").find_all("span") else None]
                    for entry in entries
                ]
                
                # Download each asset
                for asset, observer, location in assets:
                    if asset in downloaded_assets:
                        continue
                    
                    download_url = f"https://cdn.download.ams.birds.cornell.edu/api/v2/asset/{asset}/mp3"
                    filename = f"{species}; {location if location else ''}; {observer if observer else ''}; ML{asset}.mp3"
                    
                    download_file(download_dir_ml / sanitized_species, filename, download_url, overwrite=overwrite)
                    downloaded_assets.append(asset)
                    file_count += 1
                    
                    if len(downloaded_assets) >= max_per_species:
                        break
                
                # Move to next region if needed
                try:
                    next_region = next(backup_regions_iter)
                    query_region = f"&regionCode={next_region}" if next_region else ""
                except StopIteration:
                    break
        
        logging.info(f"Completed eBird/ML downloads: {file_count} files")
        progress_callback(1.0)  # Mark as complete
        
    except Exception as e:
        logging.error(f"Error in eBird download: {str(e)}")
        progress_callback(1.0)  # Mark as complete even on error
