import requests
import os
from knowledge_storm.rm import SemanticScholarRM
from knowledge_storm.utils import load_api_key

load_api_key(toml_file_path='../.config/secrets.toml')


def search_text_snippets(query, semantic_scholar_api_key, limit=10):
    """
    Searches for text snippets using the Semantic Scholar API.

    Args:
        query (str): The search query string (plain text).
        semantic_scholar_api_key (str): The API key for authentication.
        limit (int): The maximum number of results to return (default is 10, max is 1000).

    Returns:
        dict: The response data from the API.

    Raises:
        ValueError: If the query is empty or the limit exceeds 1000.
        requests.exceptions.RequestException: For issues with the HTTP request.
    """
    if not query:
        raise ValueError("Query parameter is required.")
    if limit > 1000:
        raise ValueError("Limit cannot exceed 1000.")

    url = "https://api.semanticscholar.org/graph/v1/snippet/search"
    
    headers = {
        "Authorization": f"Bearer {semantic_scholar_api_key}"
    }
    params = {
        "query": query,
        "limit": limit
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Raise an error for HTTP codes 4xx/5xx
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        raise

load_api_key(toml_file_path='../.config/secrets.toml')
# Example usage:
# Replace 'your_api_key' with your actual API key
semantic_scholar_api_key = os.getenv('SEMANTIC_SCHOLAR_API_KEY')
query = "Background information about ai agent ai4science"
limit = 10

try:
    result = search_text_snippets(query, semantic_scholar_api_key, limit)
    print("Search Results:", result)
except Exception as e:
    print("Failed to retrieve snippets:", e)
