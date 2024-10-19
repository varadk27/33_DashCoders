import json
import spacy
from elasticsearch import Elasticsearch

# Load SpaCy model for English
nlp = spacy.load("en_core_web_sm")

def extract_keywords(search_query):
    # Process the search query using SpaCy
    doc = nlp(search_query)
    # Extract keywords based on POS tagging
    keywords = [token.text for token in doc if token.is_alpha and token.is_stop is False]
    return keywords

def search_snippets(search_query):
    es = Elasticsearch(['http://localhost:9200'])  # Adjust URL if necessary
    index_name = 'code_snippets'
    
    # Extract keywords from the search query
    keywords = extract_keywords(search_query)
    print(f"Extracted Keywords: {keywords}")  # For debugging

    # Construct a multi-match query using the extracted keywords
    search_body = {
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": " ".join(keywords),  # Use extracted keywords
                            "fields": ["tags", "description", "snippet"],
                            "fuzziness": "AUTO"
                        }
                    }
                ],
                "should": [
                    {
                        "match": {
                            "tags": "video"
                        }
                    },
                    {
                        "match": {
                            "description": "video"
                        }
                    },
                    {
                        "match": {
                            "snippet": "video"
                        }
                    }
                ],
                "minimum_should_match": 1  # Ensure at least one 'should' clause matches
            }
        },
        "size": 1,  # Limit the number of results to 1
        "sort": [
            {
                "_score": {
                    "order": "desc"  # Sort by relevance score
                }
            }
        ]
    }

    print(f"Search body: {search_body}")  # Optional: For debugging

    # Perform the search query
    response = es.search(index=index_name, body=search_body)

    # Check if any snippets were found
    if response['hits']['total']['value'] > 0:
        print(f"Found {response['hits']['total']['value']} snippet(s):\n")
        hit = response['hits']['hits'][0]  # Get the most relevant snippet
        snippet_id = hit['_id']
        snippet_data = hit['_source']
        # Display snippet details in an organized format
        print(f"Snippet ID: {snippet_id}")
        print(f"Snippet: {snippet_data['snippet']}")
        print(f"Description: {snippet_data['description']}")
        print(f"Tags: {', '.join(snippet_data['tags'])}")
        print(f"File Path: {snippet_data['file_path']}\n")
    else:
        print("No snippets found.")

if __name__ == "__main__":
    # Get user input for search query
    search_query = input("Enter a search term: ")
    search_snippets(search_query)
