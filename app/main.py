# app/main.py
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from app.book_writer import generate_user_prompt_driven_book, generate_book_title
from app.book_pdf_exporter import save_book_as_pdf
from dotenv import load_dotenv
import os
import re
import traceback

load_dotenv()

app = FastAPI(
    title="Star Wars Book Generator",
    description="An API to generate a personalized Star Wars fan novel based on a user prompt.",
    version="4.0.0"
)

# --- NEW: Create directories on startup to prevent errors ---
# This ensures the folders exist before FastAPI tries to mount them.
# The path used here will be the root of your project on Render.
os.makedirs("generated_books", exist_ok=True)
os.makedirs("ui_images", exist_ok=True)
os.makedirs("videos", exist_ok=True)
# --- End of New Code ---

# Serve the static folders
app.mount("/generated_books", StaticFiles(directory="generated_books"), name="generated_books")
app.mount("/ui_images", StaticFiles(directory="ui_images"), name="ui_images")
app.mount("/videos", StaticFiles(directory="videos"), name="videos")

class BookRequest(BaseModel):
    user_input: str
    num_pages: int = 100

def sanitize_filename(text: str) -> str:
    sanitized = re.sub(r'[\\/*?:"<>|]', "", text)
    return sanitized[:50].strip().replace(' ', '_')

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("index.html") as f:
        return HTMLResponse(content=f.read(), status_code=200)

@app.post("/generate-book/", summary="Generate a Star Wars Book")
async def generate_star_wars_book(request: BookRequest):
    # This function remains the same, no changes needed here
    user_prompt = request.user_input.strip()
    if not user_prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")
    
    final_page_count = min(request.num_pages, 100)
    print(f"Processing request for a {final_page_count}-page book.")

    try:
        print("Generating a unique book title...")
        raw_title = await generate_book_title(user_prompt)
        book_title = raw_title.replace("#", "").strip()
        print(f"Generated Title: {book_title}")

        print(f"Generating book components for prompt: '{user_prompt}'...")
        book_data = await generate_user_prompt_driven_book(
            prompt=user_prompt,
            num_pages=final_page_count
        )
        print("Book components generated successfully.")

        filename = f"{sanitize_filename(book_title)}.pdf"
        print(f"Generating PDF: {filename}...")
        
        output_pdf_path = await run_in_threadpool(
            save_book_as_pdf,
            title=book_title,
            book_data=book_data,
            filename=filename
        )
        print(f"PDF saved to: {output_pdf_path}")
        
        pdf_url = f"/generated_books/{filename}"

        return {
            "title": book_title,
            "prompt": user_prompt,
            "pdf_file": pdf_url,
            "preview": book_data.get('prologue_text', '')[:1500] + "..."
        }
    except Exception as e:
        print(f"An error occurred during book generation: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")