# client.py
import requests

def search_hscode(query: str):
    try:
        response = requests.post(
            "http://localhost:8000/search_hscode/",  # Change port if you modified it above
            json={"query": query},
            timeout=5  # Add timeout to avoid hanging
        )
        response.raise_for_status()  # Raise exception for bad status codes
        
        results = response.json()
        for result in results:
            print(f"ID: {result['id']}")
            print(f"Code: {result['code']}")
            print(f"Description: {result['description']}")
            print(f"Similarity: {result['similarity']:.4f}")
            print("---")
            
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to server. Is the FastAPI server running?")
    except requests.exceptions.Timeout:
        print("Error: Request timed out")
    except requests.exceptions.RequestException as e:
        print(f"Error: {str(e)}")

# Test it
if __name__ == "__main__":
    search_hscode("cotton t-shirt")