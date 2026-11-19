from chroma_indexing import VectorStore
from dotenv import  load_dotenv
from langchain_openai import ChatOpenAI
import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

BASE_URL = "https://api.aionlabs.ai/v1"
load_dotenv()  
key = os.getenv("AIONLAB_API_KEY")
MODEL="aion-labs/aion-2.0"

class RAG : 
    def __init__(self):
        self.db = VectorStore()
        self.llm = ChatOpenAI( model=MODEL, 
                                base_url=BASE_URL,
                                api_key=key,
                                temperature=0,)

    def create_prompt_temp(self):
        prompt = ChatPromptTemplate.from_template(
            """Answer using ONLY the context below. Cite sources as [source, page].
        If the answer is not in the context, say "Not found in the sources."
        Context:
        {context}
        Question: {question}"""
        )
        return prompt

    def format_docs(docs):
        return "\n\n".join(
            f"[{d.metadata['source']}, p.{d.metadata['page']}] {d.page_content}" for d in docs
        )

    def create_chain(self):
        prompt = self.create_prompt_temp()
        
        chain = ( {"context": self.db.retreiver(), "question": lambda x: x}
                    | prompt | self.llm | StrOutputParser()
                                                           )

        return chain

    def request(self , prompt):
        chain = self.create_chain()
        return chain.invoke(prompt)


if __name__ == "__main__":
     rag = RAG()
     response = rag.request("Can you eexplain to me what a VQE is ?")
     print(response)





        