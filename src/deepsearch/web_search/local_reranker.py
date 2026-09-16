"""
Reference:
https://github.com/sentient-agi/OpenDeepSearch/blob/main/src/opendeepsearch/ranking_models/jina_reranker.py

"""
import os
import requests
import torch
from typing import List, Optional, Dict, Union
from dotenv import load_dotenv

def batch_inputs(inputs, batch_size=32):
    for i in range(0, len(inputs), batch_size):
        yield i, inputs[i:i + batch_size]

def send_batched_requests(api_url, headers, data, batch_size=32):
    """Rerank data["texts"] in batches, returning results indexed globally.

    The server scores each batch independently and returns indices relative to
    the batch it was handed, so every batch's indices are shifted by that
    batch's offset before the results are merged.
    """
    texts = data.get("texts")
    if not texts:
        raise ValueError("Missing 'texts' in data payload.")

    all_results = []
    for offset, batch in batch_inputs(texts, batch_size=batch_size):
        # Clone the original data to avoid mutating the input
        batch_data = data.copy()
        batch_data["texts"] = batch

        try:
            response = requests.post(api_url, headers=headers, json=batch_data)
            response.raise_for_status()  # Raise exception for non-200 status codes

            resp_data = response.json()
            print("Batch processed successfully.")
            batch_results = resp_data if isinstance(resp_data, list) else [resp_data]
            for item in batch_results:
                if isinstance(item, dict) and "index" in item:
                    all_results.append({**item, "index": item["index"] + offset})
        except requests.exceptions.RequestException as e:
            #raise RuntimeError(f"Error calling local AI API: {str(e)}")
            print(f"Error calling local AI API: {str(e)}")

    return all_results

class LocalReranker():
    """
    Semantic searcher implementation running locally using Text Embeddings Inference (TEI).
    """
    
    def __init__(self, model: str = "BAAI/bge-reranker-base"):
        """
        Initialize the reranker.
        
        Args:
            model: Model name to use (default: "BAAI/bge-reranker-base")
        """
        RERANKER_SERVER_HOST_IP = os.getenv("RERANKER_SERVER_HOST_IP", "0.0.0.0")
        RERANKER_SERVER_PORT = int(os.getenv("RERANKER_SERVER_PORT", 8808))

        self.api_url = f"http://{RERANKER_SERVER_HOST_IP}:{RERANKER_SERVER_PORT}/rerank"
        self.headers = {"Content-Type": "application/json"}
        self.model = model

    def get_reranked_documents(
        self,
        query: Union[str, List[str]],
        documents: List[str],
        top_k: int = 5
    ) -> List[str]:
        """
        Returns only the reranked documents without scores.

        Args:
            query: Query string or list of query strings
            documents: List of documents to rerank
            top_k: Number of top results to return per query

        Returns:
            List of reranked document strings
        """

        data = {
            "query": query,
            "texts": documents,
            "top_n": top_k
        }

        print(f"reranker url={self.api_url}\n")
        print(f"query={query}\n")
        print(f"before rerank, first 5 documents={documents[:5]}\n")
        # Get a single list of all responses, with indices into `documents`
        all_results = send_batched_requests(self.api_url, self.headers, data)

        print(f"length of reranked results: {len(all_results)}, top_k={top_k}\n")

        # Scores are only comparable once every batch's results are merged, so
        # sort globally before taking the top_k.
        scored = [r for r in all_results if 0 <= r["index"] < len(documents)]
        scored.sort(key=lambda r: r.get("score", 0.0), reverse=True)

        reranked_docs = [documents[r["index"]] for r in scored[:top_k]]

        rtn = "\n".join([x.strip() for x in reranked_docs])
        print(f"after rerank, rtn={rtn}")
        return rtn

