"""
Script to find and configure Chrome and ChromeDriver paths in Replit environment.
This script will be imported by main.py to set up the correct paths for Selenium.
"""

import os
import glob
import subprocess
import logging

logger = logging.getLogger(__name__)

def find_chrome_binary():
    """Find the Chromium binary in Replit environment."""
    # Try command line which
    try:
        chrome_path = subprocess.check_output(["which", "chromium"]).decode().strip()
        if os.path.exists(chrome_path):
            logger.info(f"Found Chrome binary via which: {chrome_path}")
            return chrome_path
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.debug("Could not find Chrome binary via which command")
    
    # Try common paths in nix store
    nix_paths = glob.glob("/nix/store/*chromium*/bin/chromium")
    if nix_paths:
        logger.info(f"Found Chrome binary via glob: {nix_paths[0]}")
        return nix_paths[0]
    
    # Last resort - hardcoded path that often works in Replit
    default_path = '/nix/store/x205pbkd5xh5g4iv0g58xjla55has3cx-chromium-108.0.5359.94/bin/chromium'
    if os.path.exists(default_path):
        logger.info(f"Using default Chrome path: {default_path}")
        return default_path
    
    logger.warning("Could not find Chrome binary")
    return None

def find_chromedriver_binary():
    """Find the ChromeDriver binary in Replit environment."""
    # Try command line which
    try:
        driver_path = subprocess.check_output(["which", "chromedriver"]).decode().strip()
        if os.path.exists(driver_path):
            logger.info(f"Found ChromeDriver binary via which: {driver_path}")
            return driver_path
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.debug("Could not find ChromeDriver binary via which command")
    
    # Try common paths in nix store
    nix_paths = glob.glob("/nix/store/*chromium*/bin/chromedriver")
    if nix_paths:
        logger.info(f"Found ChromeDriver binary via glob: {nix_paths[0]}")
        return nix_paths[0]
    
    # Last resort - hardcoded path that often works in Replit
    default_path = '/nix/store/x205pbkd5xh5g4iv0g58xjla55has3cx-chromium-108.0.5359.94/bin/chromedriver'
    if os.path.exists(default_path):
        logger.info(f"Using default ChromeDriver path: {default_path}")
        return default_path
    
    logger.warning("Could not find ChromeDriver binary")
    return None

def setup_environment():
    """Set up environment variables for Chrome and ChromeDriver."""
    chrome_binary = find_chrome_binary()
    chromedriver_binary = find_chromedriver_binary()
    
    if chrome_binary:
        os.environ['CHROME_BIN'] = chrome_binary
    
    if chromedriver_binary:
        os.environ['CHROMEDRIVER_PATH'] = chromedriver_binary
    
    logger.info(f"Chrome binary: {os.environ.get('CHROME_BIN', 'Not found')}")
    logger.info(f"ChromeDriver binary: {os.environ.get('CHROMEDRIVER_PATH', 'Not found')}")
    
    return chrome_binary, chromedriver_binary

# Initialize environment if this script is run directly
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    setup_environment()