import json
import spacy
import streamlit as st
from elasticsearch import Elasticsearch

# Load SpaCy model for English
nlp = spacy.load("en_core_web_sm")

def load_code_standards(file_path='code_standards.json'):
    """Load code standards from a JSON file."""
    with open(file_path, 'r') as f:
        standards = json.load(f)
    return standards
def evaluate_code(snippet, standards):
    """
    Evaluate the code snippet against custom standards and return the alignment percentage and suggestions.
    """
    score = 0
    total_criteria = 0
    suggestions = set()  # Use a set to avoid duplicate suggestions

    # Suggestions map for each standard
    suggestions_map = {
        "naming_conventions": "Ensure function and variable names follow snake_case convention.",
        "max_function_length": f"Consider breaking down functions longer than {standards['max_function_length']} lines into smaller ones.",
        "min_comments": f"Add at least {standards['min_comments']} comments to explain your code.",
        "max_line_length": f"Keep lines under {standards['max_line_length']} characters long.",
        "disallowed_keywords": f"Avoid using disallowed keywords: {', '.join(standards['disallowed_keywords'])}.",
    }

    # Check naming conventions
    if "def " in snippet:  # A very basic check for functions
        function_names = [line.split()[1].split("(")[0] for line in snippet.splitlines() if line.strip().startswith("def")]
        for name in function_names:
            if "_" in name:  # Check for snake_case
                score += 1
            else:
                suggestions.add(suggestions_map["naming_conventions"])
            total_criteria += 1

    # Check maximum function length
    function_lengths = [len(line.splitlines()) for line in snippet.splitlines() if line.strip().startswith("def")]
    for length in function_lengths:
        if length <= standards["max_function_length"]:
            score += 1
        else:
            suggestions.add(suggestions_map["max_function_length"])
        total_criteria += 1

    # Check minimum comments
    comment_count = snippet.count("#")  # Count comments
    if comment_count >= standards["min_comments"]:
        score += 1
    else:
        suggestions.add(suggestions_map["min_comments"])
    total_criteria += 1

    # Check maximum line length
    line_length_exceeds = False  # Track if any line exceeds the max length
    for line in snippet.splitlines():
        if len(line) <= standards["max_line_length"]:
            score += 1
        else:
            line_length_exceeds = True  # Mark that we have an issue with line length
        total_criteria += 1

    if line_length_exceeds:
        suggestions.add(suggestions_map["max_line_length"])

    # Check for disallowed keywords
    for keyword in standards["disallowed_keywords"]:
        if keyword in snippet:
            suggestions.add(suggestions_map["disallowed_keywords"])
            total_criteria += 1  # Count this criteria as checked
        else:
            score += 1  # Score for not using disallowed keyword

    # Calculate alignment percentage
    alignment_percentage = (score / total_criteria) * 100 if total_criteria > 0 else 0
    return alignment_percentage, list(suggestions)  # Convert set back to list for output

def search_snippets(search_query):
    es = Elasticsearch(['http://localhost:9200'])  # Adjust URL if necessary
    index_name = 'code_snippets'
    
    # Normalize search query
    normalized_query = search_query.lower()

    # Construct a query to search for the term in both tags and description
    search_body = {
        "query": {
            "bool": {
                "should": [
                    {
                        "match": {
                            "tags": {
                                "query": normalized_query,
                                "fuzziness": "AUTO",  # Allow for slight variations in the search term
                                "boost": 5.0  # Increase weight for matches in tags
                            }
                        }
                    },
                    {
                        "match": {
                            "description": {
                                "query": normalized_query,
                                "fuzziness": "AUTO",
                                "boost": 3.0  # Increase weight for matches in descriptions
                            }
                        }
                    },
                    {
                        "match": {
                            "snippet": {
                                "query": normalized_query,
                                "fuzziness": "AUTO",
                                "boost": 2.0  # Increase weight for matches in snippets
                            }
                        }
                    }
                ],
                "minimum_should_match": 1  # Ensure at least one condition must match
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

    # Perform the search query
    response = es.search(index=index_name, body=search_body)

    # Check if any snippets were found
    if response['hits']['total']['value'] > 0:
        hit = response['hits']['hits'][0]  # Get the most relevant snippet
        snippet_id = hit['_id']
        snippet_data = hit['_source']
        score = hit['_score']  # Get relevance score

        # Calculate similarity percentage based on the score
        similarity_percentage = round((score / response['hits']['max_score']) * 100, 2) if response['hits']['max_score'] > 0 else 0
        
        # Load custom code standards
        standards = load_code_standards()
        
        # Evaluate code alignment with standards
        alignment_percentage, suggestions = evaluate_code(snippet_data['snippet'], standards)
        
        return snippet_id, snippet_data, similarity_percentage, alignment_percentage, suggestions
    else:
        return None, None, None, None, None

def main():
    st.title("Code Snippet Search Chatbot")
    st.write("Ask for code snippets by entering a search term.")
    
    # Input for user search query
    search_query = st.text_input("Enter a search term:")
    
    if st.button("Search"):
        if search_query:
            snippet_id, snippet_data, similarity_percentage, alignment_percentage, suggestions = search_snippets(search_query)
            if snippet_data:
                st.write(f"**Snippet ID:** {snippet_id}")
                st.write(f"**Similarity:** {similarity_percentage}%")
                st.write(f"**Alignment with Standards:** {alignment_percentage:.2f}%")
                
                # Display snippet in a formatted way
                st.write("**Snippet:**")
                st.code(snippet_data['snippet'], language='python')
                
                st.write(f"**Description:** {snippet_data['description']}")
                st.write(f"**Tags:** {', '.join(snippet_data['tags'])}")
                st.write(f"**File Path:** {snippet_data['file_path']}")

                # Display suggestions if alignment is below 85%
                if alignment_percentage < 85:
                    st.write("**Suggestions for Improvement to align with code standards :**")
                    for suggestion in suggestions:
                        st.write(f"- {suggestion}")
                else:
                    st.success("The snippet meets the coding standards!")
            else:
                st.write("No snippets found.")
        else:
            st.write("Please enter a search term.")

if __name__ == "__main__":
    main()
