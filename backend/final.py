import requests
import base64
import json
import spacy
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import torch
from transformers import RobertaTokenizer, RobertaModel
from flask import Flask, request, jsonify
from flask_cors import CORS

# Initialize the Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Load the English NLP model
nlp = spacy.load("en_core_web_sm")

# Load the pre-trained CodeBERT model and tokenizer
tokenizer = RobertaTokenizer.from_pretrained("microsoft/codebert-base")
model = RobertaModel.from_pretrained("microsoft/codebert-base")

# Load programming-related keywords from JSON file
def load_keywords(file_path):
    with open(file_path, 'r') as json_file:
        keywords = json.load(json_file)
    return keywords

# Load code standards from JSON file
def load_code_standards(file_path='code_standards.json'):
    with open(file_path, 'r') as f:
        standards = json.load(f)
    return standards

def extract_relevant_keyword(query, programming_keywords):
    # Process the query with spaCy
    doc = nlp(query)

    # Extract keywords (nouns and proper nouns)
    keywords = [token.text for token in doc if token.pos_ in ['NOUN', 'PROPN']]

    # Filter keywords to include only programming-related terms
    relevant_keywords = [kw for kw in keywords if kw.lower() in programming_keywords]

    # Count frequency of each keyword
    keyword_freq = Counter(relevant_keywords)

    # Sort keywords by frequency and return the most relevant one
    sorted_keywords = keyword_freq.most_common(1)

    if sorted_keywords:
        return sorted_keywords[0][0]  # Return the most relevant keyword
    return None  # Return None if no relevant keywords found

def get_embedding(text):
    """
    Get the embedding of the given text using CodeBERT.
    """
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
        # Use the [CLS] token representation as the embedding
        embeddings = outputs.last_hidden_state[:, 0, :].squeeze()
    return embeddings

def cosine_similarity(embedding1, embedding2):
    """
    Calculate the cosine similarity between two embeddings.
    """
    return torch.nn.functional.cosine_similarity(embedding1, embedding2, dim=0).item()

def find_most_relevant_code(query, code_snippets):
    """
    Find the most relevant code snippet based on the given query.
    """
    # Get the embedding for the query
    query_embedding = get_embedding(query)

    # Get embeddings for all code snippets
    code_embeddings = [get_embedding(code) for code in code_snippets]

    # Compute similarity scores
    similarities = [cosine_similarity(query_embedding, code_embedding) for code_embedding in code_embeddings]

    # Find the index of the code snippet with the highest similarity score
    most_relevant_index = similarities.index(max(similarities))
    return code_snippets[most_relevant_index], similarities[most_relevant_index]

# Fetch file content and search for the relevant keyword
def fetch_and_search(repo_id, item_path, keyword, headers, organization, project):
    content_url = f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repo_id}/items?path={item_path}&api-version=7.0&$format=text"
    content_response = requests.get(content_url, headers=headers)

    if content_response.status_code == 200:
        content = content_response.text

        # Extract the portion with the relevant keyword (class, function, etc.)
        start_index = content.lower().find(keyword.lower())
        if start_index != -1:
            # Capture a portion of the code starting from the keyword
            end_index = content.find('class ', start_index + 1)  # look for the next class definition or end of file
            if end_index == -1:
                end_index = len(content)  # till end of file if no other class is found
            relevant_snippet = content[start_index:end_index]

            return (item_path, relevant_snippet)
    return (item_path, None)  # Return None if no match found

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

# Search for the relevant keyword in Azure DevOps
def search_video_processor_class(query):
    # Azure DevOps configuration
    organization = ""  
    project =""
    pat = ""

    # Create authorization header with PAT
    authorization = str(base64.b64encode(bytes(':' + pat, 'ascii')), 'ascii')
    headers = {
        'Authorization': 'Basic ' + authorization,
        'Accept': 'application/json'
    }

    # Use the Git API endpoint to list repositories
    repos_url = f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories?api-version=7.0"

    # List of excluded file extensions
    excluded_extensions = ['.mp4','.json','.avi', '.mkv', '.wav', '.mp3', '.jpg', '.jpeg', '.png', '.pkl', '.h5', '.pt', '.unet']

    try:
        # Get list of repositories
        repos_response = requests.get(repos_url, headers=headers)
        repos_response.raise_for_status()

        repos = repos_response.json()['value']

        # Load programming keywords from JSON file
        programming_keywords = load_keywords('programming_keywords.json')

        # Extract keyword from the user query
        keyword = extract_relevant_keyword(query, programming_keywords)

        if not keyword:
            return {"error": "No relevant keyword found."}

        # Search through each repository
        code_snippets = []
        for repo in repos:
            repo_id = repo['id']

            # Get all items in the repository
            items_url = f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repo_id}/items?recursionLevel=Full&api-version=7.0"

            items_response = requests.get(items_url, headers=headers)

            if items_response.status_code == 200:
                items_data = items_response.json()
                if 'value' in items_data:
                    # Search through all file types
                    files = items_data['value']

                    # Filter out excluded file types
                    files = [item for item in files if not any(item['path'].endswith(ext) for ext in excluded_extensions)]

                    # Create a ThreadPoolExecutor to handle multithreading
                    with ThreadPoolExecutor(max_workers=10) as executor:
                        future_to_file = {executor.submit(fetch_and_search, repo_id, item['path'], keyword, headers, organization, project): item['path'] for item in files}

                        for future in as_completed(future_to_file):
                            file_path, snippet = future.result()
                            if snippet:
                                code_snippets.append((file_path, snippet))  # Store the relevant snippet for later use

        # Find the most relevant code snippet from the fetched snippets
        if code_snippets:
            most_relevant_code, similarity_score = find_most_relevant_code(query, [s[1] for s in code_snippets])
            # Get the file path of the most relevant code
            file_link = next(item[0] for item in code_snippets if item[1] == most_relevant_code)
            
            # Load code standards
            standards = load_code_standards()
            
            # Evaluate the code against standards
            alignment_percentage, suggestions = evaluate_code(most_relevant_code, standards)
            
            return {
                "most_relevant_code": most_relevant_code,
                "similarity_score": similarity_score,
                "file_link": f"https://dev.azure.com/{organization}/{project}/_git/{repo_id}?path={file_link}",
                "alignment_percentage": alignment_percentage,
                "suggestions": suggestions
            }
        else:
            return {"error": "No relevant code snippets found."}

    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

# Define a route to handle incoming search queries
@app.route('/search', methods=['POST'])
def search():
    query = request.json.get('query')
    if not query:
        return jsonify({"error": "No query provided"}), 400

    # Perform the search using the existing logic
    result = search_video_processor_class(query)
    return jsonify(result)

if __name__ == "__main__":
    app.run(port=5000, debug=True)