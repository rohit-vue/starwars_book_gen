import httpx
import warnings

# Ignore SSL certificate warnings
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

SWAPI_BASE_URL = "https://swapi.dev/api"

async def fetch_character_info(name: str) -> dict:
    async with httpx.AsyncClient(verify=False) as client:  # Skip SSL verification here
        try:
            response = await client.get(f"{SWAPI_BASE_URL}/people/", params={"search": name})
            response.raise_for_status()
            results = response.json().get("results", [])
            if not results:
                return {"name": name, "info": "No data found."}
            return results[0]  # Return the first matched result
        except httpx.RequestError as e:
            return {"error": str(e)}