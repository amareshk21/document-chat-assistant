import requests
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime
import json
import logging

def scrape_url(url: str, name: str):
    """Scrape content from URL and save it to an organized directory structure."""
    try:
        # Create source directory
        source_dir = Path("data") / name
        source_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up headers for the request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        print(f"Scraping URL: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove unwanted elements
        for element in soup.find_all(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()
        
        # Get main content
        content = ""
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
        
        if main_content:
            content = main_content.get_text(separator='\n', strip=True)
        else:
            # Try to find content by common section names
            sections = soup.find_all(['div', 'section'], class_=lambda x: x and any(term in x.lower() for term in ['content', 'main', 'article', 'body']))
            if sections:
                content = '\n\n'.join(section.get_text(separator='\n', strip=True) for section in sections)
            else:
                content = soup.get_text(separator='\n', strip=True)
        
        # Clean up the content
        content = '\n'.join(line.strip() for line in content.split('\n') if line.strip())
        
        if not content or len(content) < 100:  # Arbitrary minimum length
            return {"status": "error", "message": "Failed to extract meaningful content from the URL"}
        
        # Save content
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        content_file = source_dir / f"content_{timestamp}.txt"
        
        with open(content_file, "w", encoding="utf-8") as f:
            f.write(content)
        
        # Save metadata
        metadata = {
            "url": url,
            "name": name,
            "timestamp": timestamp,
            "content_length": len(content)
        }
        
        metadata_file = source_dir / "metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Successfully scraped {len(content)} characters")
        return {"status": "success", "message": f"Successfully scraped and saved content from {url}"}
        
    except Exception as e:
        print(f"Scraping error: {str(e)}")
        return {"status": "error", "message": f"Failed to scrape URL: {str(e)}"} 