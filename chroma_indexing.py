"""vector_store.py - a small wrapper around Chroma for the papers RAG project.

Features:
- init: creates or loads a persistent Chroma database
- add_documents: adds chunks in batches, skipping ones already stored (no duplicates)
- save: writes a manifest (embedding model, counts, date); Chroma itself persists automatically
- backup: copies the whole database folder
- search / as_retriever: plug straight into a LangChain chain
"""
import hashlib
import json
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path
from doc_process import DocumentProcessor 
from text_process import chunk , to_documents
from tqdm import tqdm


from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings


def _basename(path: str) -> str:
    """File name from a path, whatever the slash style (Windows or Linux)."""
    return str(path).replace("\\", "/").split("/")[-1]


class VectorStore:
    MANIFEST = "manifest.json"

    def __init__(
        self,
        persist_directory: str = "chroma_db",
        embedding_model: str = "BAAI/bge-m3",
        collection_name: str = "papers",
        batch_size: int = 256,
    ):
        self.persist_directory = str(Path(persist_directory).resolve())
        self.embedding_model = embedding_model
        self.collection_name = collection_name
        self.batch_size = batch_size

        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
        self._check_manifest()

        self.embeddings = HuggingFaceEmbeddings(model_name=embedding_model)
        self.db = self._open_collection()

    # ---------- setup ----------
    def _open_collection(self) -> Chroma:
        return Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory,
        )

    def _manifest_path(self) -> Path:
        return Path(self.persist_directory) / self.MANIFEST

    def _check_manifest(self) -> None:
        """Refuse to open a database that was built with a different embedding model."""
        path = self._manifest_path()
        if not path.exists():
            return
        saved = json.loads(path.read_text(encoding="utf-8"))
        if saved.get("embedding_model") != self.embedding_model:
            raise ValueError(
                f"Database was built with '{saved.get('embedding_model')}' but you asked for "
                f"'{self.embedding_model}'. Use the original model or delete the folder and re-index."
            )

    # ---------- adding ----------
    @staticmethod
    def _make_id(doc: Document) -> str:
        """Stable id from source + page + text, so re-indexing the same chunk is a no-op."""
        raw = f"{_basename(doc.metadata.get('source', ''))}|{doc.metadata.get('page', '')}|{doc.page_content}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()

    def add_documents(self, docs: list[Document], autosave: bool = True) -> int:
        """Embed and store chunks. Returns the number of NEW chunks added."""
        unique = {self._make_id(d): d for d in docs}          # drop duplicates inside the input
        ids = list(unique)

        existing: set[str] = set()
        #for i in range(0, len(ids), self.batch_size):
        #   existing.update(self.db.get(ids=ids[i : i + self.batch_size])["ids"])

        new_ids = [i for i in ids if i not in existing]

        for i in tqdm (range (0, len(new_ids), self.batch_size) , desc="Indexing papers chunks"):
            batch = new_ids[i : i + self.batch_size]
            self.db.add_documents([unique[b] for b in batch], ids=batch)

        if autosave:
            self.save()
        return len(new_ids)

    

    # ---------- reading ----------
    def count(self) -> int:
        return self.db._collection.count()

    def sources(self) -> Counter:
        """Number of chunks per paper file."""
        data = self.db.get(include=["metadatas"])
        return Counter(_basename(m.get("source", "")) for m in data["metadatas"])

    def search(self, query: str, k: int = 5, source: str | None = None):
        """Top-k chunks; optionally restricted to one paper file name."""
        flt = None
        if source:
            match = [s for s in {m["source"] for m in self.db.get(include=["metadatas"])["metadatas"]}
                     if _basename(s) == _basename(source)]
            flt = {"source": match[0]} if match else {"source": "__none__"}
        return self.db.similarity_search(query, k=k, filter=flt)

    def as_retriever(self, k: int = 5):
        return self.db.as_retriever(search_kwargs={"k": k})

    # ---------- deleting ----------
    def delete_source(self, source: str) -> int:
        """Remove every chunk of one paper (matched by file name). Returns how many were removed."""
        data = self.db.get(include=["metadatas"])
        ids = [i for i, m in zip(data["ids"], data["metadatas"])
               if _basename(m.get("source", "")) == _basename(source)]
        for i in range(0, len(ids), self.batch_size):
            self.db.delete(ids=ids[i : i + self.batch_size])
        self.save()
        return len(ids)

    def reset(self) -> None:
        """Empty the collection (the folder stays)."""
        self.db.delete_collection()
        self.db = self._open_collection()
        self.save()

    # ---------- saving ----------
    def save(self) -> dict:
        """Chroma writes to disk automatically; this records a manifest next to the data."""
        info = {
            "embedding_model": self.embedding_model,
            "collection_name": self.collection_name,
            "chunks": self.count(),
            "papers": len(self.sources()),
            "saved_at": datetime.now().isoformat(timespec="seconds"),
        }
        self._manifest_path().write_text(json.dumps(info, indent=2), encoding="utf-8")
        return info

    def backup(self, destination: str) -> str:
        """Copy the whole database folder to `destination` (must not exist yet)."""
        self.save()
        shutil.copytree(self.persist_directory, destination)
        return str(Path(destination).resolve())

    def retreiver(self):
        return self.db.as_retriever(search_kwargs={"k": 5})


if __name__ == "__main__":
    

    store = VectorStore("chroma_db")
    print("Chunks already stored:", store.count())
    #pdf_path = Path("papers/1512.06860v2.pdf")
    #processor = DocumentProcessor(pdf_path)
    #processor.process()
    #chunks = chunk(processor.document , chunk_size=1000, overlap=150)
    with open("SavedChunks/papers_chunks.json", encoding="utf-8") as f:
        doc_chunks = json.load(f)

    vector_db = VectorStore()
    docs = []
    for chunks in doc_chunks : 
        docs.extend(to_documents(chunks))

    vector_db.add_documents(docs)

    results = store.search(query="How to calculate eigenvalues of a Hamiltonian ? " )
    for r in results : 
        print('Retreived chunk : ' , r.page_content )


    #print("Added:", store.add_documents(to_documents(chunks)), "new chunks")
    #print("Total:", store.count(), "chunks from", len(store.sources()), "papers")