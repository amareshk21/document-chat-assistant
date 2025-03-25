import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI
from typing import List, Dict, Any
import os
from pathlib import Path
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize ChromaDB with persistent storage
chroma_client = chromadb.PersistentClient(path="./chroma_db")
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=os.getenv("OPENAI_API_KEY"),
    model_name="text-embedding-ada-002"
)

def get_or_create_collection():
    """Get existing collection or create a new one."""
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
    return collection

def load_documents_from_directory(directory: str) -> List[str]:
    """Load all text files from the specified directory."""
    documents = []
    for file_path in Path(directory).glob("**/*.txt"):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read().strip()
                if content:
                    documents.append(content)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    return documents

def reload_documents() -> Dict[str, Any]:
    """Reload documents into ChromaDB."""
    try:
        print("Starting document reload...")
        
        # Try to delete existing collection if it exists
        try:
            print("Attempting to delete existing collection...")
            chroma_client.delete_collection("my_documents")
            print("Successfully deleted existing collection")
        except Exception as e:
            print(f"No existing collection to delete: {str(e)}")
        
        # Create new collection
        print("Creating new collection...")
        collection = chroma_client.create_collection(
            name="my_documents",
            embedding_function=openai_ef
        )
        print("Successfully created new collection")
        
        # Load documents
        print("Loading documents from data directory...")
        documents = []
        data_dir = Path("data")
        
        if not data_dir.exists():
            print("Data directory not found - creating empty collection")
            return {"status": "success", "message": "No documents found - created empty collection"}
            
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
            return {"status": "success", "message": "No documents found - created empty collection"}
            
    except Exception as e:
        print(f"Error reloading documents: {e}")
        return {"status": "error", "message": f"Failed to reload documents: {str(e)}"}

def get_vector_db_status() -> Dict[str, Any]:
    """Get current status of the vector database."""
    try:
        collection = get_or_create_collection()
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
                    "last_updated": None,  # You might want to add a timestamp field to your documents
                    "sample_content": results['documents'][0][:200] if results['documents'] else ""
                }
            }
        else:
            return {
                "status": "success",
                "data": {
                    "total_documents": 0,
                    "sources": [],
                    "last_updated": None,
                    "sample_content": ""
                }
            }
            
    except Exception as e:
        print(f"Error in vector DB status: {str(e)}")
        return {"status": "error", "message": f"Failed to get vector DB status: {str(e)}"} 