from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI
from typing import List, Optional
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
from data_ingestion import (
    get_or_create_collection,
    reload_documents,
    get_vector_db_status,
    client
)
from url_scraper import scrape_url
from pydantic import BaseModel

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

# Initialize ChromaDB with persistent storage
chroma_client = chromadb.PersistentClient(path="./chroma_db")
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=os.getenv("OPENAI_API_KEY"),
    model_name="text-embedding-ada-002"
)

# Create or get collection
try:
    collection = chroma_client.get_collection(
        name="my_documents",
        embedding_function=openai_ef
    )
    print("Loaded existing collection")
except Exception as e:
    print(f"Creating new collection: {str(e)}")
    collection = chroma_client.create_collection(
        name="my_documents",
        embedding_function=openai_ef
    )
    print("Created new collection")

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

class ChatRequest(BaseModel):
    message: str

class URLRequest(BaseModel):
    url: str
    name: str

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        # Get relevant context from vector database
        collection = get_or_create_collection()
        results = collection.query(
            query_texts=[request.message],
            n_results=3
        )
        
        # Filter results based on distance threshold
        relevant_chunks = []
        for i, distance in enumerate(results['distances'][0]):
            if distance < 0.8:  # Adjust threshold as needed
                relevant_chunks.append(results['documents'][0][i])
        
        if not relevant_chunks:
            return {"response": "I apologize, but I couldn't find any relevant information to answer your question. Please try rephrasing your question or ask about a different topic."}
        
        # Prepare context for the chat
        context = "\n\n".join(relevant_chunks)
        
        # Generate response using OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides accurate information based on the given context. If the context doesn't contain enough information to answer the question, say so."},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {request.message}"}
            ]
        )
        
        return {"response": response.choices[0].message.content}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/scrape")
async def scrape(request: URLRequest):
    try:
        result = scrape_url(request.url, request.name)
        if result["status"] == "success":
            # Reload documents after successful scraping
            reload_documents()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cleanup")
async def cleanup():
    try:
        # Delete data directory using subprocess
        data_dir = Path("data")
        print(f"Attempting to remove data directory at: {data_dir.absolute()}")
        
        # First try to remove any files in the directory
        if data_dir.exists():
            try:
                # Remove all files and subdirectories
                for item in data_dir.glob('**/*'):
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                # Remove the directory itself
                data_dir.rmdir()
                print("Successfully removed data directory and its contents")
            except Exception as e:
                print(f"Error in first removal attempt: {str(e)}")
                try:
                    # Try alternative method using subprocess
                    subprocess.run(['rm', '-rf', str(data_dir)], check=True)
                    print("Successfully removed data directory using subprocess")
                except subprocess.CalledProcessError as e:
                    print(f"Error in subprocess removal: {str(e)}")
                    raise
        
        # Delete ChromaDB collection
        try:
            chroma_client.delete_collection("my_documents")
            print("Successfully deleted ChromaDB collection")
        except Exception as e:
            print(f"Error deleting ChromaDB collection: {str(e)}")
        
        # Create new collection and reload documents
        reload_documents()
        
        return {"status": "success", "message": "Cleanup completed successfully"}
    except Exception as e:
        print(f"Error during cleanup: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vector-db-status")
async def vector_db_status():
    return get_vector_db_status()
