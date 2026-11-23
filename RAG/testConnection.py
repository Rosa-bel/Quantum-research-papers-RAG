"""Send a tiny request directly to the configured LLM, without running RAG."""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


BASE_URL = "https://api.aionlabs.ai/v1"
MODEL = "aion-labs/aion-2.0"
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


def main() -> None:
    load_dotenv(ENV_FILE)
    api_key = os.getenv("AIONLAB_API_KEY")
    if not api_key:
        raise SystemExit(f"AIONLAB_API_KEY is missing. Add it to {ENV_FILE}.")

    llm = ChatOpenAI(
        model=MODEL,
        base_url=BASE_URL,
        api_key=api_key,
        temperature=0,
    )

    try:
        response = llm.invoke("Reply with exactly: LLM connection successful")
    except Exception as exc:
        raise SystemExit(f"LLM connection failed: {exc}") from exc

    print(response.content)


if __name__ == "__main__":
    main()
