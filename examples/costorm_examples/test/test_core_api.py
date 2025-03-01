import requests
import json
import os
from knowledge_storm.utils import load_api_key

load_api_key(toml_file_path='../.config/secrets.toml')

# API endpoint
url = "https://api.core.ac.uk/v3/recommend"

# API key
api_key = os.getenv('CORE_API_KEY')

# Headers
print(api_key)
headers = {"Authorization": f"Bearer {api_key}"}

# Data to be sent in the POST request
data = {
    # "text": "Deep Learning",
    # "limit": 5
    # "identifier": "core:619",
    # "abstract": "Deep Learning."
    # "authors": ["Author One", "Author Two"],
    "title": "Deep Learning",
    # "result_type": "research",
    # "data_provider_id": 0
}

# Make the POST request
response = requests.post(url, headers=headers, data=json.dumps(data))

# Check the response status code
if response.status_code == 200:
    # Print the response JSON
    print(json.dumps(response.json(), indent=2))
else:
    print(f"Request failed with status code {response.status_code}")
    print(response.text)