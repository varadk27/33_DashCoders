import requests
import base64
import json
import ast

def extract_snippets_from_code(code, file_path):
    """
    Extract functions and classes from the provided code and format them with description, tags, and file path.
    """
    snippets = []

    # Parse the code into an AST
    tree = ast.parse(code)

    # Iterate through the AST nodes
    for node in ast.walk(tree):
        # Extract function definitions
        if isinstance(node, ast.FunctionDef):
            snippet = ast.get_source_segment(code, node)
            snippets.append({
                'snippet': snippet,
                'description': f'A function that defines {node.name}',
                'tags': generate_tags(node.name),
                'file_path': file_path
            })
        
        # Extract class definitions
        elif isinstance(node, ast.ClassDef):
            snippet = ast.get_source_segment(code, node)
            snippets.append({
                'snippet': snippet,
                'description': f'A class that defines {node.name}',
                'tags': generate_tags(node.name),
                'file_path': file_path
            })
    
    return snippets

def generate_tags(name):
    """
    Generate tags based on function or class name.
    """
    # Simple example: split function/class names into meaningful tags
    return [name.lower()]

def save_snippets_to_json(snippets, output_file):
    """
    Save snippets to a JSON file.
    """
    with open(output_file, 'w') as file:
        json.dump(snippets, file, indent=4)

def search_and_extract_snippets():
    organization = ""
    project = ""
    pat = ""

    # Create authorization header with PAT
    authorization = str(base64.b64encode(bytes(':' + pat, 'ascii')), 'ascii')
    headers = {
        'Authorization': 'Basic ' + authorization,
        'Accept': 'application/json'
    }

    # Use the Git API endpoint to list repositories
    repos_url = f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories?api-version=7.0"

    try:
        # Get list of repositories
        print("Fetching repositories...")
        repos_response = requests.get(repos_url, headers=headers)
        repos_response.raise_for_status()

        repos = repos_response.json()['value']
        print(f"Found {len(repos)} repositories")

        all_snippets = []  # List to collect all snippets

        # Search through each repository
        for repo in repos:
            repo_id = repo['id']
            repo_name = repo['name']
            print(f"\nSearching in repository: {repo_name}")
            print(f"Repository ID: {repo_id}")

            # Get items in the repository, filter by files only
            items_url = f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repo_id}/items?recursionLevel=Full&api-version=7.0"

            print(f"Fetching items from repository...")
            items_response = requests.get(items_url, headers=headers)

            if items_response.status_code == 200:
                items_data = items_response.json()
                if 'value' in items_data:
                    # Filter Python files from the items
                    python_files = [item for item in items_data['value'] if item.get('path', '').endswith('.py')]
                    print(f"Found {len(python_files)} Python files")

                    for item in python_files:
                        print(f"\nChecking file: {item['path']}")
                        # Get the file's actual content using 'download' API
                        content_url = f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repo_id}/items?path={item['path']}&api-version=7.0&$format=text"
                        content_response = requests.get(content_url, headers=headers)

                        if content_response.status_code == 200:
                            content = content_response.text
                            # Extract snippets from the code with file path
                            snippets = extract_snippets_from_code(content, item['path'])
                            all_snippets.extend(snippets)  # Add to the main list

                        else:
                            print(f"Failed to fetch content for {item['path']}")
                            print(f"Status code: {content_response.status_code}")
                            print(f"Response: {content_response.text}")
                else:
                    print("No 'value' field in items response")
            else:
                print(f"Failed to fetch items. Status code: {items_response.status_code}")
                print(f"Response: {items_response.text}")

        # Save all snippets to JSON file
        output_file = "code_snippets.json"
        save_snippets_to_json(all_snippets, output_file)
        print(f"\nExtracted {len(all_snippets)} snippets and saved to {output_file}.")

    except requests.exceptions.RequestException as e:
        print(f"Error occurred: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response content: {e.response.text}")

if __name__ == "__main__":
    search_and_extract_snippets()
