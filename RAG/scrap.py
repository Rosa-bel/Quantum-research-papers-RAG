import arxiv, json, time
from pathlib import Path

#retrieve papers from arxiv and save them to disk, along with metadata using the arxiv API.

QUERIES = {
    "vqe": 'cat:quant-ph AND abs:"variational quantum eigensolver"',
    "qaoa": 'cat:quant-ph AND abs:"quantum approximate optimization"',
    "qml": 'cat:quant-ph AND abs:"quantum machine learning"',
    "qnn": 'cat:quant-ph AND abs:"quantum neural network"',
    "qgnn": 'abs:"quantum" AND abs:"graph neural network"',
    "drug": 'abs:"quantum" AND (abs:"drug discovery" OR abs:"drug-target")',
}

import requests


PER_TOPIC = 20

out = Path("papers"); out.mkdir(exist_ok=True)
client = arxiv.Client(page_size=50, delay_seconds=3, num_retries=3)

def download_pdf(url, path):
    resp = requests.get(url, timeout=60, headers={"User-Agent": "rag-portfolio-project"})
    resp.raise_for_status()
    path.write_bytes(resp.content)


metadata = {}
for topic, query in QUERIES.items():
    search = arxiv.Search(
        query=query,
        max_results=PER_TOPIC * 2,                 # extra, to allow for duplicates
        sort_by=arxiv.SortCriterion.Relevance,
    )
    kept = 0
    for r in client.results(search):
        pid = r.get_short_id().replace("/", "_")
        if pid in metadata:
            continue                                # already got it from another topic
        pdf_path = out / f"{pid}.pdf"
        try:
            if not pdf_path.exists():
                download_pdf(r.pdf_url, pdf_path)
                time.sleep(3)                     # be polite to the server
            metadata[pid] = {
                "title": r.title,
                "authors": [a.name for a in r.authors],
                "published": r.published.date().isoformat(),
                "abstract": r.summary,
                "url": r.entry_id,
                "topic": topic,
            }
            kept += 1
        except Exception as e:
            print("Failed:", pid, e)
        if kept >= PER_TOPIC:
            break

json.dump(metadata, open("./papers/papers_metadata.json", "w"), indent=2)
print(len(metadata), "papers saved")