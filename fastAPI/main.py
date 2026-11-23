from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from RAG.RAG import RAG
from .model import ChatRequest, ChatResponse

app = FastAPI()
FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"
FRONTEND_FILE = FRONTEND_DIST / "index.html"

if (FRONTEND_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

rag = RAG()

@app.get("/")
async def root():
    if FRONTEND_FILE.is_file():
        return FileResponse(FRONTEND_FILE)
    return {
        "message": "React frontend is not built yet. In the frontend folder run: npm install && npm run build"
    }

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/chat" , response_model=ChatResponse)
async def chat(request :ChatRequest):
    response = rag.request(request.prompt)
    return ChatResponse(response=response)
