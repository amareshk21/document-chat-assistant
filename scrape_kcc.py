import requests
from bs4 import BeautifulSoup
import json
import os
from pathlib import Path

def scrape_kcc_info():
    # Create data directory if it doesn't exist
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # URL of the KCC scheme
    url = "https://www.myscheme.gov.in/schemes/kcc"
    
    try:
        # Send request to the website
        response = requests.get(url)
        response.raise_for_status()
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract different sections
        sections = {
            "overview": "",
            "objectives": [],
            "benefits": [],
            "eligibility": [],
            "application_process": [],
            "documents_required": [],
            "faq": []
        }
        
        # Extract overview
        overview = soup.find('div', text=lambda t: t and 'The KCC Scheme was introduced' in t)
        if overview:
            sections["overview"] = overview.get_text().strip()
        
        # Extract objectives
        objectives_section = soup.find('div', text=lambda t: t and 'Objective / Purpose' in t)
        if objectives_section:
            objectives_list = objectives_section.find_next('ol')
            if objectives_list:
                sections["objectives"] = [li.get_text().strip() for li in objectives_list.find_all('li')]
        
        # Extract benefits
        benefits_section = soup.find('div', text=lambda t: t and 'Benefits' in t)
        if benefits_section:
            benefits_list = benefits_section.find_next('ul')
            if benefits_list:
                sections["benefits"] = [li.get_text().strip() for li in benefits_list.find_all('li')]
        
        # Extract eligibility
        eligibility_section = soup.find('div', text=lambda t: t and 'Eligibility' in t)
        if eligibility_section:
            eligibility_list = eligibility_section.find_next('ol')
            if eligibility_list:
                sections["eligibility"] = [li.get_text().strip() for li in eligibility_list.find_all('li')]
        
        # Extract application process
        process_section = soup.find('div', text=lambda t: t and 'Application Process' in t)
        if process_section:
            process_list = process_section.find_next('ol')
            if process_list:
                sections["application_process"] = [li.get_text().strip() for li in process_list.find_all('li')]
        
        # Extract documents required
        docs_section = soup.find('div', text=lambda t: t and 'Documents Required' in t)
        if docs_section:
            docs_list = docs_section.find_next('ol')
            if docs_list:
                sections["documents_required"] = [li.get_text().strip() for li in docs_list.find_all('li')]
        
        # Extract FAQ
        faq_section = soup.find('div', text=lambda t: t and 'Frequently Asked Questions' in t)
        if faq_section:
            faq_items = faq_section.find_all_next('div', class_='faq-item')
            for item in faq_items:
                question = item.find('div', class_='question')
                answer = item.find('div', class_='answer')
                if question and answer:
                    sections["faq"].append({
                        "question": question.get_text().strip(),
                        "answer": answer.get_text().strip()
                    })
        
        # Save each section as a separate text file
        for section_name, content in sections.items():
            file_path = data_dir / f"{section_name}.txt"
            with open(file_path, 'w', encoding='utf-8') as f:
                if isinstance(content, list):
                    if section_name == "faq":
                        for qa in content:
                            f.write(f"Q: {qa['question']}\n")
                            f.write(f"A: {qa['answer']}\n\n")
                    else:
                        for item in content:
                            f.write(f"- {item}\n")
                else:
                    f.write(content)
        
        print("Successfully scraped and saved KCC scheme information")
        
    except Exception as e:
        print(f"Error scraping the website: {e}")

if __name__ == "__main__":
    scrape_kcc_info() 