import json, os

eval_set = json.load(open("evaluation/test_set.json", encoding="utf-8"))
PAGE_OFFSET = 1      # your JSON starts at page 1, PyPDF starts at 0 -> set to 0 if you used PyPDF numbering
PAGE_TOL = 1         # accept neighbor pages, because passages can span a page break


from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")   # the SAME model as at indexing time

db = Chroma(
    persist_directory="chroma_db",
    embedding_function=embeddings,
)

retriever = db.as_retriever(search_kwargs={"k": 5})
eval_retriever = db.as_retriever(search_kwargs={"k": 10})

q = eval_set[0]
print("EXPECTED:", q["source"], q["page"])
print("DB chunks:", db._collection.count())

docs = eval_retriever.invoke(q["question"])
print("Retrieved:", len(docs))
for d in docs[:5]:
    print(repr(d.metadata.get("source")), d.metadata.get("page"), "|", d.page_content[:80].replace("\n", " "))

def is_hit(doc, q):
    same_src = os.path.basename(doc.metadata["source"]) == os.path.basename(q["source"])
    page_ok = abs(doc.metadata["page"] - (q["page"] - PAGE_OFFSET)) <= PAGE_TOL
    return same_src and page_ok

def first_hit_rank(q):
    docs = eval_retriever.invoke(q["question"])
    for rank, d in enumerate(docs, start=1):
        if is_hit(d, q):
            return rank
    return None

answerable = [q for q in eval_set if q["type"] != "unanswerable"]
for q in answerable:
    q["rank"] = first_hit_rank(q)

def recall_at(k):
    return sum(1 for q in answerable if q["rank"] and q["rank"] <= k) / len(answerable)

mrr = sum(1 / q["rank"] for q in answerable if q["rank"]) / len(answerable)
print({f"recall@{k}": round(recall_at(k), 3) for k in (1, 3, 5, 10)}, "MRR:", round(mrr, 3))

# by question type
for t in sorted({q["type"] for q in answerable}):
    sub = [q for q in answerable if q["type"] == t]
    r5 = sum(1 for q in sub if q["rank"] and q["rank"] <= 5) / len(sub)
    print(t, len(sub), "recall@5 =", round(r5, 3))