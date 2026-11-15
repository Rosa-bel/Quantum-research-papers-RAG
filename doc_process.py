import json
import re
from datetime import datetime, timezone
from pathlib import Path
from text_process import clean_text , chunk 


from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption



class DocumentProcessor:
    # Docling labels that never reach the output
    SKIP_LABELS = {
        "page_header", "page_footer", "footnote", "formula",
        "picture", "table", "document_index", "form", "key_value_region",
    }
    REFERENCES_RE = re.compile(r"^\s*(\d+\.?\s*)?(references|bibliography)\s*$", re.I)

    def __init__(self, pdf_path: Path, out_dir: Path):
        self.pdf_path = pdf_path
        self.out_dir = out_dir
        self.converter = self._build_converter()
        self.document = None
        self.document = None   # {"metadata": {...}, "sections": [...]} filled by process()

    @staticmethod
    def _build_converter() -> DocumentConverter:
        options = PdfPipelineOptions(
            do_ocr=False,                    # arXiv PDFs have a text layer
            do_table_structure=False,        # no table parsing
            generate_picture_images=False,   # don't extract figures
            generate_page_images=False,
            do_picture_classification=False,
            do_picture_description=False,
            do_formula_enrichment=False,     # LaTeX for equations
        )
        return DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
        )
   

    def process(self, exclude_references: bool = True):
        """Parse the PDF into metadata + sections (cleaned text, pages per paragraph)."""
        doc = self.converter.convert(str(self.pdf_path)).document

        title = None
        sections = []
        current = self._new_section("Preamble", "Preamble")   # text before the first heading
        stack = []                                            # [(level, heading)]

        for item, _ in doc.iterate_items():
            label = getattr(item.label, "value", str(item.label))
            if label in self.SKIP_LABELS:
                continue

            text = clean_text(getattr(item, "text", ""))
            if not text:
                continue

            page = item.prov[0].page_no if getattr(item, "prov", None) else None

            if label == "title":
                title = title or text
                continue

            if label == "section_header":
                sections.append(current)
                level = getattr(item, "level", 1) or 1
                while stack and stack[-1][0] >= level:
                    stack.pop()
                stack.append((level, text))
                current = self._new_section(text, " > ".join(h for _, h in stack))
                continue

            current["paragraphs"].append({"page": page, "text": text})

        sections.append(current)

        final = []
        for s in sections:
            if not s["paragraphs"]:
                continue
            if exclude_references and self.REFERENCES_RE.match(s["heading"]):
                continue
            s["pages"] = sorted({p["page"] for p in s["paragraphs"] if p["page"] is not None})
            final.append(s)

        self.document = {
            "metadata": {
                "source": self.pdf_path.name,
                "title": title,
                "num_pages": len(doc.pages),
                "num_sections": len(final),
                "processed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            },
            "sections": final,
        }
        return self.document

   
    def save_chunks(self, chunks ,  filename: str = None) -> Path:
        """Write all chunks of this PDF into one JSON file in out_dir."""
        self.out_dir.mkdir(parents=True, exist_ok=True)
        path = self.out_dir / (filename or f"{self.pdf_path.stem}_chunks.json")
        path.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    @staticmethod
    def _new_section(heading: str, path: str) -> dict:
        return {"heading": heading, "heading_path": path, "paragraphs": []}


if __name__ == "__main__":
    pdf_path = Path("papers/1512.06860v2.pdf")
    out_dir = Path("testDocling_out")
    processor = DocumentProcessor(pdf_path, out_dir)
    processor.process()
    chunks = chunk(processor.document , chunk_size=1000, overlap=150)
    saved = processor.save_chunks(chunks=chunks)
    print(f"{len(chunks)} chunks saved to {saved}")