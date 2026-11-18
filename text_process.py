import re
from langchain_text_splitters import RecursiveCharacterTextSplitter

HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)   # <!-- image -->, <!-- formula-not-decoded -->
IMG_MD_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")     # ![alt](path)
LIGATURES = {"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl"}


def clean_text(text: str) -> str:
    """Clean one block of text coming out of Docling."""
    if not text:
        return ""

    # docling leftovers
    text = HTML_COMMENT_RE.sub(" ", text)
    text = IMG_MD_RE.sub(" ", text)

    # PDF encoding artifacts
    for lig, repl in LIGATURES.items():
        text = text.replace(lig, repl)
    text = text.replace("­", "")                # soft hyphens

    
    text = text.replace("\n", " ")                  # literal "\n" sequences
    text = re.sub(r"\$.*?\$", "", text)              # inline math $...$
    text = re.sub(r"\[[^\]]*\]", "", text)           # [12], [1, 2] citations

    # whitespace (last, so the deletions above don't leave gaps)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([.,;:])", r"\1", text)       # "as shown in ." -> "as shown in."
    return text.strip()


def chunk(document , chunk_size=1000, overlap=150, min_chars=80):
        """Split each section with LangChain's splitter (never across sections),
        then map every chunk back to the pages it comes from."""

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            add_start_index=True,      # position of each chunk in the section text
        )
        source = document['metadata']['source']
        chunks = []

        for section in document["sections"]:
            # Join paragraphs and remember which page each character range belongs to
            text, spans, pos = "", [], 0
            for para in section["paragraphs"]:
                if text:
                    text += "\n\n"
                    pos += 2
                spans.append((pos, pos + len(para["text"]), para["page"]))
                text += para["text"]
                pos += len(para["text"])

            for piece in splitter.create_documents([text]):
                if len(piece.page_content) < min_chars:
                    continue
                start = piece.metadata["start_index"]
                end = start + len(piece.page_content)
                pages = sorted({p for a, b, p in spans if a < end and b > start and p is not None})
                chunks.append({
                    "id": f"{source}_{len(chunks):04d}",
                    "source": source,
                    "heading": section["heading"],
                    "heading_path": section["heading_path"],
                    "pages": pages,
                    "text": piece.page_content,
                })
        return chunks

from langchain_core.documents import Document

def to_documents(chunks: list[dict]) -> list[Document]:
    return [
        Document(
            page_content=c["text"],
            metadata={
                "id": c["id"],
                "source": c["source"],
                "heading": c["heading"],
                "heading_path": c["heading_path"],
                "page_start": c["pages"][0] if c["pages"] else -1,
                "page_end": c["pages"][-1] if c["pages"] else -1,
            },
        )
        for c in chunks
    ]
