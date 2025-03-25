import os
import json
import shutil
from datetime import datetime, timedelta
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cleanup.log'),
        logging.StreamHandler()
    ]
)

def cleanup_data_folder():
    """Clean up the data folder in the project root."""
    data_dir = Path('data')
    cleaned_files = 0
    cleaned_dirs = 0
    
    if not data_dir.exists():
        logging.info("Data directory does not exist")
        return {"status": "success", "message": "No data directory found"}
    
    logging.info(f"Cleaning up data in: {data_dir}")
    
    # Remove all files and subdirectories in the data directory
    for item in data_dir.glob('**/*'):
        try:
            if item.is_file():
                item.unlink()
                cleaned_files += 1
                logging.info(f"Deleted file: {item}")
            elif item.is_dir():
                shutil.rmtree(item)
                cleaned_dirs += 1
                logging.info(f"Deleted directory: {item}")
        except Exception as e:
            logging.error(f"Error processing {item}: {str(e)}")
            continue
    
    # Remove the data directory itself
    try:
        if data_dir.exists():
            data_dir.rmdir()
            cleaned_dirs += 1
            logging.info(f"Removed data directory: {data_dir}")
    except Exception as e:
        logging.error(f"Error removing data directory: {str(e)}")
    
    message = f"Removed {cleaned_files} files"
    if cleaned_dirs > 0:
        message += f" and {cleaned_dirs} directories"
    logging.info(f"Cleanup completed successfully. {message}")
    return {"status": "success", "message": message}

def main():
    try:
        result = cleanup_data_folder()
        print(json.dumps(result))
    except Exception as e:
        error_msg = f"Cleanup failed: {str(e)}"
        logging.error(error_msg)
        print(json.dumps({"status": "error", "message": error_msg}))

if __name__ == "__main__":
    main() 