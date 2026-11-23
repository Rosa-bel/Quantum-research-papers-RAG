# Quantum Papers RAG

A small retrieval-augmented generation app for asking questions about a collection of quantum computing papers. FastAPI provides the chat API, Chroma stores paper chunks, and a React frontend provides the chat interface.

## Project structure

```text
.
├── fastAPI/
│   ├── main.py             # FastAPI routes and frontend hosting
│   └── model.py            # Request/response schemas
├── frontend/
│   ├── src/                # React UI and styles
│   ├── index.html          # Vite entry page
│   ├── package.json        # Frontend dependencies and commands
│   └── vite.config.js      # Development server and API proxy
├── RAG/
│   ├── RAG.py              # Retrieval + LLM chain
│   ├── chroma_indexing.py  # Chroma vector-store wrapper
│   ├── doc_process.py      # PDF parsing and section extraction
│   ├── text_process.py     # Text cleanup, chunking, metadata conversion
│   ├── papers/             # Local PDF inputs (ignored by Git)
│   ├── SavedChunks/        # Processed chunks in JSON
│   ├── chroma_db/          # Persistent vector database (ignored by Git)
│   └── evaluation/         # Retrieval evaluation data and scripts
├── requirements.txt        # Python dependencies
├── .env                    # Local API key; do not commit
└── FRONTEND.md             # Frontend run and build instructions
```

`RAG/testConnection.py` sends a direct test prompt to the configured LLM without loading the vector store. `RAG/testDocling_out/` contains a sample Docling output.

## RAG pipeline

1. **Prepare PDFs.** Put paper PDFs in `RAG/papers/`.
2. **Parse and clean.** `DocumentProcessor` in `RAG/doc_process.py` uses Docling to extract the title, sections, paragraphs, and page numbers. `clean_text` in `RAG/text_process.py` removes common PDF artifacts.
3. **Chunk the text.** `chunk` splits section text into overlapping chunks (currently 1,500 characters with 150 characters of overlap by the PDF processor) and records each chunk's source, heading, and page range. Processed chunks are saved as JSON under `RAG/SavedChunks/`.
4. **Index chunks.** `to_documents` converts chunk dictionaries to LangChain documents. `VectorStore` embeds them with `BAAI/bge-m3` and stores the vectors in Chroma at `RAG/chroma_db/`.
5. **Retrieve context.** For a chat request, `RAG.request()` searches the Chroma collection for the five most relevant chunks.
6. **Generate an answer.** The retrieved chunks and question are sent to Aion Labs (`aion-labs/aion-2.0`) through `ChatOpenAI`. The prompt asks the model to answer only from the retrieved context and to say `Not found in the sources.` when the context is insufficient.

The backend opens the existing vector store at startup. It does not automatically parse or index PDFs; PDF processing and indexing are separate preparation steps.

To process the PDFs in `RAG/papers/` and add their chunks to the vector store, run this from the repository root after installing Docling and the Python requirements:

```python
import json
from pathlib import Path

from RAG.chroma_indexing import VectorStore
from RAG.doc_process import DocumentProcessor
from RAG.text_process import to_documents

processor = DocumentProcessor(Path("RAG/papers"), Path("RAG/SavedChunks"))
processor.process()

with Path("RAG/SavedChunks/papers_chunks.json").open(encoding="utf-8") as file:
    chunk_groups = json.load(file)

documents = [
    document
    for group in chunk_groups
    for document in to_documents(group)
]
VectorStore().add_documents(documents)
```

## Setup

### Python backend

From the repository root, create and activate a virtual environment, then install the Python requirements:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Set the LLM key in a root-level `.env` file:

```dotenv
AIONLAB_API_KEY=your_api_key
```

PDF ingestion uses Docling. If it is not already available in your environment, install it with `pip install docling` (it is not currently listed in `requirements.txt`). The first backend startup may also download the `BAAI/bge-m3` embedding model from Hugging Face.

### React frontend

```powershell
cd frontend
npm install
```

## Run the app

For development, start the backend from the repository root:

```powershell
uvicorn fastAPI.main:app --reload --port 8000
```

In a second terminal, run the React development server:

```powershell
cd frontend
npm run dev
```

Open the Vite URL shown in the terminal (usually `http://127.0.0.1:5173`). Vite proxies `/chat` and `/health` to FastAPI on port 8000.

To build React and serve it from FastAPI at `http://127.0.0.1:8000`, run `npm run build` in `frontend/`, then start the backend. FastAPI serves the generated `frontend/dist` files. Rebuild after frontend changes.

## API

- `GET /health` returns `{"status":"ok"}`.
- `POST /chat` accepts `{"prompt":"your question"}` and returns `{"response":"..."}`.

## Direct LLM connection check

With `.env` configured, run this from the repository root:

```powershell
python .\RAG\testConnection.py
```

This calls the LLM directly and does not test PDF retrieval or Chroma.
