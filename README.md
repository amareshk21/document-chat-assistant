# Document Chat Assistant

A web-based chat application that allows users to ask questions about documents. The application uses FastAPI for the backend, ChromaDB for vector storage, and OpenAI's GPT-4 for generating responses.

## Features

- Web scraping functionality to load documents
- Vector database for efficient document search
- Modern and responsive UI
- Real-time chat interface
- Document chunking with relevance scoring
- Data cleanup functionality

## Prerequisites

- Python 3.8+
- OpenAI API key
- ChromaDB

## Installation

1. Clone the repository:
```bash
git clone <your-repository-url>
cd document-chat-assistant
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the project root with your OpenAI API key:
```
OPENAI_API_KEY=your-api-key-here
```

## Usage

1. Start the FastAPI server:
```bash
uvicorn main:app --reload
```

2. Open your browser and navigate to `http://localhost:8000`

3. Use the interface to:
   - Scrape new documents
   - Ask questions about the documents
   - View source information and relevance scores
   - Clean up data when needed

## Project Structure

```
document-chat-assistant/
├── main.py              # FastAPI application
├── static/             # Static files
│   ├── index.html      # Main HTML file
│   ├── styles.css      # CSS styles
│   └── script.js       # JavaScript code
├── data/               # Scraped data storage
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## API Endpoints

- `GET /`: Redirects to the chat interface
- `POST /chat`: Handles chat messages
- `POST /scrape`: Handles URL scraping
- `POST /cleanup`: Handles data cleanup
- `GET /vector-db-status`: Returns vector database status

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 