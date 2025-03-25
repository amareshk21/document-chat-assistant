from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
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
    client,
    openai_ef
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
    system_prompt: Optional[str] = None

class URLRequest(BaseModel):
    url: str
    name: str

class ScrapeRequest(BaseModel):
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
            n_results=5
        )
        
        # Filter results based on distance threshold
        distance_threshold = 0.8
        relevant_chunks = []
        total_relevancy = 0
        num_relevant_chunks = 0
        
        for i, (distance, doc) in enumerate(zip(results['distances'][0], results['documents'][0])):
            if distance <= distance_threshold:
                # Convert distance to relevance score (0-100)
                relevance_score = round((1 - distance) * 100, 2)
                relevant_chunks.append({
                    "content": doc,
                    "relevance_score": relevance_score
                })
                total_relevancy += relevance_score
                num_relevant_chunks += 1
        
        # Calculate average relevancy score
        avg_relevancy = round(total_relevancy / num_relevant_chunks, 2) if num_relevant_chunks > 0 else 0
        
        # Prepare context for chat
        context = "\n\n".join(chunk["content"] for chunk in relevant_chunks)
        
        # Use custom system prompt if provided
        system_prompt = request.system_prompt if request.system_prompt else """You are a helpful assistant that provides accurate information based on the given context. If the context doesn't contain enough information to answer the question, say so.

User Query: {user_query}

Context:
{context}

Please provide a helpful response based on the above information."""
        
        # Replace variables in the prompt
        system_prompt = system_prompt.format(
            user_query=request.message,
            context=context
        )
        
        # Generate response using OpenAI
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        response_text = response.choices[0].message.content
        
        # Calculate accuracy score using semantic similarity
        try:
            # Get embeddings for response and context chunks
            response_embedding = openai_ef([response_text])[0]
            chunk_embeddings = openai_ef([chunk["content"] for chunk in relevant_chunks])
            
            # Calculate cosine similarity between response and each chunk
            similarities = []
            for chunk_embedding in chunk_embeddings:
                # Calculate cosine similarity
                dot_product = sum(float(a) * float(b) for a, b in zip(response_embedding, chunk_embedding))
                norm_a = sum(float(a) * float(a) for a in response_embedding) ** 0.5
                norm_b = sum(float(b) * float(b) for b in chunk_embedding) ** 0.5
                similarity = float(dot_product / (norm_a * norm_b))
                similarities.append(similarity)
            
            # Calculate average similarity and convert to percentage
            avg_similarity = float(sum(similarities) / len(similarities))
            accuracy_score = round(avg_similarity * 100, 2)
        except Exception as e:
            print(f"Error calculating accuracy score: {str(e)}")
            accuracy_score = 0
        
        # Convert any numpy values to Python native types
        response_data = {
            "response": str(response.choices[0].message.content),
            "context": [
                {
                    "content": str(chunk["content"]),
                    "relevance_score": float(chunk["relevance_score"])
                }
                for chunk in relevant_chunks
            ],
            "relevancy_score": float(avg_relevancy),
            "accuracy_score": float(accuracy_score)
        }
        
        return response_data
        
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/scrape")
async def scrape(request: ScrapeRequest):
    """Scrape content from a URL and save it to the data directory."""
    try:
        result = scrape_url(request.url, request.name)
        if result["status"] == "success":
            # Reload documents into vector database
            reload_result = reload_documents()
            if reload_result["status"] == "error":
                return JSONResponse(
                    status_code=500,
                    content={"status": "error", "message": f"Scraping successful but failed to reload documents: {reload_result['message']}"}
                )
        return result
    except Exception as e:
        print(f"Error in scrape endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cleanup")
async def cleanup():
    """Delete the data directory and reload documents into the vector database."""
    try:
        # Delete data directory
        data_dir = Path("data")
        if data_dir.exists():
            shutil.rmtree(data_dir)
            print("Data directory deleted successfully")
        
        # Reload documents
        result = reload_documents()
        if result["status"] == "error":
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": f"Failed to reload documents: {result['message']}"}
            )
        
        return {"status": "success", "message": "Data cleanup completed successfully"}
    except Exception as e:
        print(f"Error in cleanup endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vector-db-status")
async def vector_db_status():
    """Get the current status of the vector database."""
    try:
        return get_vector_db_status()
    except Exception as e:
        print(f"Error in vector-db-status endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
