import json
from elasticsearch import Elasticsearch
import uuid

def index_snippets(json_file):
    # Connect to Elasticsearch
    es = Elasticsearch(['http://localhost:9200'])  # Adjust URL if necessary
    index_name = 'code_snippets'

    # Load snippets from the JSON file
    with open(json_file, 'r') as file:
        snippets = json.load(file)

    # Index each snippet in Elasticsearch
    for snippet in snippets:
        # Use a unique ID for each snippet
        unique_id = str(uuid.uuid4())
        response = es.index(index=index_name, id=unique_id, body=snippet)
        print(f"Indexed snippet with ID {unique_id}: {response['result']}")

if __name__ == "__main__":
    index_snippets('code_snippets.json')
