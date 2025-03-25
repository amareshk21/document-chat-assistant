from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI
from typing import List
import json
import os
from pathlib import Path
import subprocess
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import shutil
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize ChromaDB
chroma_client = chromadb.Client()
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=os.getenv("OPENAI_API_KEY"),
    model_name="text-embedding-ada-002"
)

# Create or get collection
collection = chroma_client.create_collection(
    name="my_documents",
    embedding_function=openai_ef
)

def load_documents_from_directory(directory: str) -> List[str]:
    """Load all text files from the specified directory."""
    documents = []
    for file_path in Path(directory).glob("**/*.txt"):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                if content.strip():  # Only add non-empty documents
                    documents.append(content)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    return documents

def reload_documents():
    """Reload documents into ChromaDB."""
    try:
        print("Starting document reload...")
        # Delete existing collection
        print("Deleting existing collection...")
        chroma_client.delete_collection("my_documents")
        
        # Create new collection
        print("Creating new collection...")
        global collection
        collection = chroma_client.create_collection(
            name="my_documents",
            embedding_function=openai_ef
        )
        
        # Load documents
        print("Loading documents from data directory...")
        documents = []
        data_dir = Path("data")
        
        if not data_dir.exists():
            print("Data directory not found!")
            return {"status": "error", "message": "Data directory not found"}
            
        # Process each text file
        for file_path in data_dir.glob("**/*.txt"):
            print(f"Processing file: {file_path}")
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read().strip()
                    if content:
                        # Split content into smaller chunks
                        chunks = [chunk.strip() for chunk in content.split("\n\n") if chunk.strip()]
                        print(f"Found {len(chunks)} chunks in {file_path}")
                        documents.extend(chunks)
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
                
        if documents:
            print(f"Adding {len(documents)} documents to ChromaDB...")
            collection.add(
                documents=documents,
                ids=[f"doc_{i}" for i in range(len(documents))]
            )
            print("Documents added successfully!")
            return {"status": "success", "message": f"Loaded {len(documents)} documents"}
        else:
            print("No documents found to load!")
            return {"status": "success", "message": "No documents found"}
            
    except Exception as e:
        print(f"Error reloading documents: {e}")
        return {"status": "error", "message": f"Failed to reload documents: {str(e)}"}

def scrape_url(url: str, name: str):
    """Scrape content from URL and save it to an organized directory structure."""
    try:
        # Create base data directory if it doesn't exist
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        
        # Create source-specific directory
        source_dir = data_dir / name
        source_dir.mkdir(exist_ok=True)
        
        # Save metadata
        metadata = {
            "url": url,
            "name": name,
            "scraped_at": datetime.now().isoformat()
        }
        
        with open(source_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        
        # Handle local file
        if url.startswith("file://"):
            content_file = source_dir / "content_kcc.txt"
            print(f"Looking for file at: {content_file}")
            
            if os.path.exists(content_file):
                with open(content_file, "r", encoding="utf-8") as f:
                    content = f.read()
                print(f"Successfully read local file with {len(content)} characters")
                
                # Split content into chunks by sections
                chunks = []
                current_chunk = []
                lines = content.split('\n')
                
                for line in lines:
                    # If line is a section header (ends with :) or is all uppercase
                    if line.strip().endswith(':') or (line.strip().isupper() and len(line.strip()) > 0):
                        # If we have content in current_chunk, save it
                        if current_chunk:
                            chunk_text = '\n'.join(current_chunk).strip()
                            if len(chunk_text) > 0:
                                chunks.append(chunk_text)
                            current_chunk = []
                    
                    # Add line to current chunk
                    if line.strip():
                        current_chunk.append(line)
                
                # Add the last chunk if it exists
                if current_chunk:
                    chunk_text = '\n'.join(current_chunk).strip()
                    if len(chunk_text) > 0:
                        chunks.append(chunk_text)
                
                print(f"Split content into {len(chunks)} chunks")
                for i, chunk in enumerate(chunks):
                    print(f"\nChunk {i+1}:")
                    print("-" * 40)
                    print(chunk[:200] + "..." if len(chunk) > 200 else chunk)
                    print("-" * 40)
                
                if chunks:
                    # Add chunks to ChromaDB
                    collection.add(
                        documents=chunks,
                        ids=[f"doc_{i}" for i in range(len(chunks))]
                    )
                    print(f"Added {len(chunks)} chunks to ChromaDB")
                    return {"status": "success", "message": f"Successfully loaded {len(chunks)} chunks from local file"}
                else:
                    return {"status": "error", "message": "No valid chunks found in the file"}
            else:
                return {"status": "error", "message": f"Local file not found at {content_file}"}
        
        # Set headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        
        # Scrape content
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
        
        print(f"Successfully scraped {len(content)} characters")
        return {"status": "success", "message": f"Successfully scraped and saved content from {url}"}
        
    except Exception as e:
        print(f"Scraping error: {str(e)}")
        return {"status": "error", "message": f"Failed to scrape URL: {str(e)}"}

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")

@app.post("/cleanup")
async def cleanup_data():
    """Clean up scraped data and vector database."""
    try:
        # Delete the data directory and its contents
        data_dir = Path("data")
        if data_dir.exists():
            shutil.rmtree(data_dir)
            print("Removed data directory")
        
        # Delete the ChromaDB collection
        try:
            chroma_client.delete_collection("my_documents")
            print("Deleted ChromaDB collection")
        except Exception as e:
            print(f"Error deleting ChromaDB collection: {e}")
        
        # Create a new empty collection
        global collection
        collection = chroma_client.create_collection(
            name="my_documents",
            embedding_function=openai_ef
        )
        print("Created new empty collection")
        
        return {"status": "success", "message": "Cleaned up data and vector database"}
    except Exception as e:
        print(f"Error during cleanup: {e}")
        return {"status": "error", "message": f"Failed to clean up: {str(e)}"}

@app.post("/scrape")
async def scrape_data(request: Request):
    """Handle URL scraping request."""
    try:
        data = await request.json()
        url = data.get("url")
        name = data.get("name")
        
        if not all([url, name]):
            return {"status": "error", "message": "Missing required fields"}
        
        # Scrape the URL
        result = scrape_url(url, name)
        
        if result["status"] == "success":
            # Reload documents into ChromaDB
            reload_result = reload_documents()
            if reload_result["status"] == "success":
                return {
                    "status": "success", 
                    "message": f"{result['message']} and {reload_result['message']}"
                }
            else:
                return {
                    "status": "partial", 
                    "message": f"{result['message']} but failed to update vector DB: {reload_result['message']}"
                }
        
        return result
        
    except Exception as e:
        return {"status": "error", "message": f"Scraping failed: {str(e)}"}

@app.post("/chat")
async def chat(request: Request):
    try:
        print("Received chat request")
        data = await request.json()
        print("Request data:", data)
        user_message = data.get("message", "")
        print("User message:", user_message)
        
        if not user_message:
            print("No message provided")
            return {"response": "Please provide a message", "context": "", "chunks": []}
        
        # Query the vector database for relevant context
        print("Querying vector database")
        results = collection.query(
            query_texts=[user_message],
            n_results=2
        )
        print("Vector DB results:", results)
        
        if not results or not results['documents'] or not results['documents'][0]:
            print("No relevant documents found")
            return {"response": "I couldn't find relevant information in the documents.", "context": "", "chunks": []}
        
        # Get the relevant chunks and their distances
        chunks = results['documents'][0]
        distances = results['distances'][0]
        print(f"Found {len(chunks)} chunks")
        
        # Filter chunks based on relevance (distance threshold)
        relevant_chunks = []
        chunk_info = []
        for chunk, distance in zip(chunks, distances):
            if distance < 0.8:  # Adjust this threshold as needed
                relevant_chunks.append(chunk)
                # Convert distance to relevance score (0-100)
                relevance_score = round((1 - distance) * 100, 2)
                chunk_info.append({
                    "content": chunk,
                    "relevance_score": relevance_score
                })
        
        if not relevant_chunks:
            print("No relevant chunks found after filtering")
            return {"response": "I couldn't find relevant information in the documents.", "context": "", "chunks": []}
        
        print(f"Found {len(relevant_chunks)} relevant chunks")
        
        # Prepare context from relevant chunks
        context = "\n\n".join(relevant_chunks)
        
        # Create prompt with context
        prompt = f"""Given the following context and user question, provide a helpful response.
        
        Context:
        {context}
        
        User Question: {user_message}
        
        Response:"""
        
        print("Generating response with OpenAI")
        # Generate response using OpenAI
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that answers questions based on the provided context."},
                {"role": "user", "content": prompt}
            ]
        )
        
        print("Response generated successfully")
        return {
            "response": response.choices[0].message.content,
            "context": context,
            "chunks": chunk_info
        }
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return {"response": f"An error occurred: {str(e)}", "context": "", "chunks": []}

@app.get("/vector-db-status")
async def get_vector_db_status():
    """Get current status of the vector database."""
    try:
        # Get document count
        count = collection.count()
        
        # Get all documents
        if count > 0:
            # Get all documents
            results = collection.get()
            
            # Extract sources from documents
            sources = []
            if results and results.get('documents'):
                for doc in results['documents']:
                    # Try to identify the source from the content
                    if "KCC" in doc or "Kisan Credit Card" in doc:
                        sources.append("KCC Documentation")
                    # Add more source identification logic here
            
            return {
                "status": "success",
                "data": {
                    "total_documents": count,
                    "sources": list(set(sources)),
                    "last_updated": datetime.now().isoformat(),
                    "sample_content": results['documents'][0][:200] if results['documents'] else ""
                }
            }
        else:
            return {
                "status": "success",
                "data": {
                    "total_documents": 0,
                    "sources": [],
                    "last_updated": datetime.now().isoformat(),
                    "sample_content": ""
                }
            }
            
    except Exception as e:
        print(f"Error in vector DB status: {str(e)}")
        return {"status": "error", "message": f"Failed to get vector DB status: {str(e)}"}
