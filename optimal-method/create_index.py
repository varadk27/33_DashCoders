import json
from elasticsearch import Elasticsearch

def create_index(es, index_name):
    # Create an index if it doesn't exist
    if not es.indices.exists(index=index_name):
        es.indices.create(index=index_name, body={
            "mappings": {
                "properties": {
                    "snippet": { "type": "text" },
                    "tags": { "type": "keyword" },
                    "description": { "type": "text" },
                    "file_path": { "type": "text" }
                }
            }
        })
        print(f"Index '{index_name}' created.")
    else:
        print(f"Index '{index_name}' already exists.")

def load_data(es, index_name, json_file):
    with open(json_file, 'r') as file:
        data = json.load(file)
        
        for item in data:
            es.index(index=index_name, document=item)
            print(f"Document indexed: {item}")

if __name__ == "__main__":
    # Connect to Elasticsearch
    es = Elasticsearch(['http://localhost:9200'],timeout=30)
    
    index_name = 'code_snippets'
    
    # Create index
    create_index(es, index_name)
    
    # Load data from JSON file
    json_file_path = 'c:\\Users\\hp\\Desktop\\coep1\\make snippets\\code_snippets.json'  # Adjust the path as needed
    load_data(es, index_name, json_file_path)
