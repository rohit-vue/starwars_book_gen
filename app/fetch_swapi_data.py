# fetch_swapi_data.py
import httpx
import asyncio
import json
import os
import warnings

# Ignore SSL certificate warnings (as seen in your original swapi_client.py)
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

SWAPI_BASE_URL = "https://swapi.dev/api"
OUTPUT_DIR = "swapi_data"


async def fetch_all_for_category(client: httpx.AsyncClient, category: str) -> list:
    """
    Fetches all data for a given category (e.g., 'people', 'planets')
    by following the pagination links.
    """
    all_results = []
    next_url = f"{SWAPI_BASE_URL}/{category}/"
    print(f"--- Starting fetch for category: {category} ---")

    while next_url:
        try:
            print(f"Fetching page: {next_url}")
            response = await client.get(next_url)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
            
            data = response.json()
            
            # Add the results from the current page to our master list
            all_results.extend(data.get("results", []))
            
            # Get the URL for the next page, or None if it's the last page
            next_url = data.get("next")
            
            # Be a good API citizen and wait a tiny bit between requests
            await asyncio.sleep(0.1) 

        except httpx.RequestError as e:
            print(f"An error occurred while requesting {e.request.url!r}: {e}")
            break # Stop trying on an error
            
    print(f"--- Finished fetch for {category}. Found {len(all_results)} items. ---\n")
    return all_results

async def main():
    """
    Main function to orchestrate the fetching and saving of all data.
    """
    # Create the output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # List of categories you want to download
    categories_to_fetch = [
        "people",
        "planets",
        "starships",
        "vehicles",
        "species",
        "films"
    ]
    
    # Use an async client to make efficient requests
    async with httpx.AsyncClient(verify=False, timeout=20.0) as client:
        for category in categories_to_fetch:
            # Fetch all data for the current category
            category_data = await fetch_all_for_category(client, category)
            
            if category_data:
                # Define the output file path
                file_path = os.path.join(OUTPUT_DIR, f"{category}.json")
                
                # Write the collected data to a JSON file
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(category_data, f, ensure_ascii=False, indent=4)
                print(f"Successfully saved data to {file_path}")

if __name__ == "__main__":
    asyncio.run(main())