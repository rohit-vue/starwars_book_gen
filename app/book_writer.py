from openai import AsyncOpenAI
import os
import asyncio
import re
import json
import random
import string
import httpx
from app.prompt_builder import (
    build_chapter_section_prompt, build_summarization_prompt,
    build_title_generation_prompt, build_data_selection_prompt,
    build_safe_image_prompt_generation_prompt # Use the new safe prompt
)
from dotenv import load_dotenv

load_dotenv()

openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL_TEXT = "gpt-4-1106-preview"
MODEL_IMAGE = "dall-e-3"
WORDS_PER_SECTION_TARGET = 750

def load_all_swapi_data():
    data = {}
    data_dir = "swapi_data"
    if not os.path.exists(data_dir):
        raise FileNotFoundError("The 'swapi_data' directory was not found. Please run the fetch_swapi_data.py script first.")
    for filename in os.listdir(data_dir):
        if filename.endswith(".json"):
            category = filename.replace(".json", "")
            with open(os.path.join(data_dir, filename), "r", encoding='utf-8') as f:
                data[category] = json.load(f)
    return data

ALL_SWAPI_DATA = load_all_swapi_data()
print("SWAPI data loaded successfully.")

# NEW: Robust calculation function to determine chapter count and word length
def calculate_book_parameters(num_pages: int) -> tuple[int, int]:
    WORDS_PER_PAGE = 250
    # Fixed pages: JSON(10), Title(1), Date(1), TOC(1), Preface(1), Prologue(1), Epilogue(1), Blanks(4+2+1+1+1=9) = ~27
    FIXED_FRONT_MATTER = 27
    OVERHEAD_PAGES_PER_CHAPTER = 2 # Title page + Image page
    
    pages_for_chapters = num_pages - FIXED_FRONT_MATTER
    
    chapters_needed = max(1, min(12, round(pages_for_chapters / (5 + OVERHEAD_PAGES_PER_CHAPTER))))

    content_pages_for_chapters = max(1, num_pages - FIXED_FRONT_MATTER - (chapters_needed * OVERHEAD_PAGES_PER_CHAPTER))
    total_words_needed = content_pages_for_chapters * WORDS_PER_PAGE
    target_words_per_chapter = int(total_words_needed / chapters_needed) if chapters_needed > 0 else 0
    
    print(f"Request for {num_pages} pages -> Aiming for {chapters_needed} chapters of ~{target_words_per_chapter} words each.")
    return chapters_needed, target_words_per_chapter


async def select_book_data_context(prompt: str) -> dict:
    selection_prompt = build_data_selection_prompt(prompt, ALL_SWAPI_DATA)
    response = await openai.chat.completions.create(
        model=MODEL_TEXT, messages=[{"role": "user", "content": selection_prompt}],
        temperature=0.3, response_format={"type": "json_object"}
    )
    try:
        selected_names = json.loads(response.choices[0].message.content)
        book_context = {}
        for category, names in selected_names.items():
            if category in ALL_SWAPI_DATA:
                book_context[category] = [item for item in ALL_SWAPI_DATA[category] if item.get('name') in names or item.get('title') in names]
        return book_context
    except (json.JSONDecodeError, KeyError):
        return { "people": [], "planets": [], "starships": [] }

async def generate_chapter_image(chapter_summary: str) -> str:
    """
    Generates a chapter image using a safer, two-step process to avoid content policy errors.
    """
    print(f"  - Generating image for chapter based on summary: '{chapter_summary[:80]}...'")
    safe_prompt_request = build_safe_image_prompt_generation_prompt(chapter_summary)
    try:
        sanitized_prompt_response = await openai.chat.completions.create(model=MODEL_TEXT, messages=[{"role": "user", "content": safe_prompt_request}], temperature=0.7, max_tokens=300)
        image_prompt = sanitized_prompt_response.choices[0].message.content.strip().strip('"')
        print(f"    - Sanitized DALL-E Prompt: {image_prompt}")
        response = await openai.images.generate(model=MODEL_IMAGE, prompt=image_prompt, size="1024x1024", quality="standard", n=1)
        image_url = response.data[0].url
        output_dir = "generated_images"
        os.makedirs(output_dir, exist_ok=True)
        image_filename = f"{''.join(random.choices(string.ascii_letters + string.digits, k=12))}.png"
        output_path = os.path.join(output_dir, image_filename)
        async with httpx.AsyncClient() as client:
            image_response = await client.get(image_url)
            image_response.raise_for_status()
            with open(output_path, "wb") as f: f.write(image_response.content)
        print(f"  - Chapter image saved to: {output_path}")
        return output_path
    except Exception as e:
        print(f"  - Could not generate chapter image: {e}")
        return None

async def generate_book_title(prompt: str) -> str:
    title_prompt = build_title_generation_prompt(prompt, "book")
    response = await openai.chat.completions.create(
        model=MODEL_TEXT, messages=[{"role": "user", "content": title_prompt}],
        temperature=0.8, max_tokens=20
    )
    return response.choices[0].message.content.strip().strip('"')

async def generate_chapter_titles(prompt: str, data_context: dict, num_chapters: int) -> list[str]:
    titles_prompt = build_title_generation_prompt(prompt, "chapter_list", data_context, num_chapters)
    response = await openai.chat.completions.create(
        model=MODEL_TEXT, messages=[{"role": "user", "content": titles_prompt}],
        temperature=0.7, max_tokens=60 * num_chapters
    )
    content = response.choices[0].message.content
    titles = re.findall(r'^\d+\.\s*(.*)', content, re.MULTILINE)
    return titles if titles else [f"Chapter {i+1}" for i in range(num_chapters)]

async def generate_chapter_section(prompt: str, title: str, summary: str, context: dict, words: int) -> str:
    # This now correctly uses the requested word count
    content_prompt = build_chapter_section_prompt(prompt, title, summary, context, words)
    response = await openai.chat.completions.create(
        model=MODEL_TEXT, messages=[{"role": "user", "content": content_prompt}],
        temperature=0.75, max_tokens=1200
    )
    return response.choices[0].message.content.strip()

async def summarize_section(text: str) -> str:
    summary_prompt = build_summarization_prompt(text)
    try:
        response = await openai.chat.completions.create(
            model=MODEL_TEXT, messages=[{"role": "user", "content": summary_prompt}],
            temperature=0.2, max_tokens=200
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return text[:300] + "..."

async def generate_content_block(prompt: str, title: str, context: dict, word_target: int) -> str:
    print(f"--- Generating content for: '{title}' (Target: {word_target} words) ---")
    if word_target <= 0:
        return ""

    # If the target is small (like for a prologue), do it in one go.
    if word_target <= WORDS_PER_SECTION_TARGET:
        print(f"  - Generating single section of {word_target} words...")
        return await generate_chapter_section(prompt, title, "Start of the section.", context, word_target)

    # Otherwise, use the multi-part logic for long chapters
    num_sections = round(word_target / WORDS_PER_SECTION_TARGET)
    parts = []
    summary = f"The section is '{title}'. Set the scene and begin the narrative."
    for i in range(num_sections):
        print(f"  - Generating part {i+1}/{num_sections}...")
        section_text = await generate_chapter_section(prompt, title, summary, context, WORDS_PER_SECTION_TARGET)
        parts.append(section_text)
        if i < num_sections - 1:
            print(f"  - Summarizing part {i+1} for continuity...")
            summary = await summarize_section(section_text)
            await asyncio.sleep(2)
            
    print(f"--- Finished content for: '{title}' ---")
    return "\n\n".join(parts)

async def generate_user_prompt_driven_book(prompt: str, num_pages: int):
    chapters_needed, target_words_per_chapter = calculate_book_parameters(num_pages)
    
    print("Selecting relevant SWAPI data based on prompt...")
    data_context = await select_book_data_context(prompt)
    
    print("Generating front matter and chapter outline...")
    prologue_word_target = 250
    epilogue_word_target = 250
    
    tasks = {
        "prologue": generate_content_block(prompt, "Prologue", data_context, prologue_word_target),
        "epilogue": generate_content_block(prompt, "Epilogue", data_context, epilogue_word_target),
        "titles": generate_chapter_titles(prompt, data_context, chapters_needed)
    }
    results = await asyncio.gather(*tasks.values())
    prologue_text, epilogue_text, chapter_titles = results
    final_titles = chapter_titles[:chapters_needed]
    
    chapters_data = []
    print("\n--- Starting Sequential Chapter and Image Generation ---")
    for i, title in enumerate(final_titles):
        chapter_heading = f"Chapter {i+1}: {title}"
        print(f"\n[Generating Content for {chapter_heading}]")
        
        chapter_text = await generate_content_block(prompt, chapter_heading, data_context, target_words_per_chapter)
        image_summary = await summarize_section(chapter_text)
        image_path = await generate_chapter_image(image_summary)
        
        chapters_data.append({"heading": title, "content": chapter_text, "image_path": image_path})
        await asyncio.sleep(4)

    preface_text = """A long time ago, in a galaxy far, far away, the stories were endless. They were tales of heroism and betrayal, of light and darkness, echoing from the Core Worlds to the Outer Rim. What you hold in your hands is one such echo—a story inspired by a fragment of that vast history.

This is a work of fan-fiction, a tribute to the universe that has captured our imaginations for generations. It is a 'what if,' a new perspective on a familiar galaxy. It was not crafted by a story group or a corporation, but by a spark of digital consciousness guided by a simple prompt, weaving together known legends with new possibilities. May it transport you, once again, to that galaxy of endless adventure."""

    return {
        "swapi_call_text": f"User Prompt: {prompt}",
        "swapi_json_output": json.dumps(data_context, indent=4),
        "preface_text": preface_text,
        "prologue_text": prologue_text,
        "epilogue_text": epilogue_text,
        "chapters": chapters_data,
    }

async def generate_chapter_image(chapter_summary: str) -> str:
    """
    Generates a chapter image using a safer, two-step process to avoid content policy errors.
    """
    print(f"  - Generating image for chapter based on summary: '{chapter_summary[:80]}...'")
    
    # Step 1: Ask the LLM to generate a safe, descriptive prompt for DALL-E.
    print("    - Creating a safe and descriptive prompt for DALL-E...")
    safe_prompt_request = build_safe_image_prompt_generation_prompt(chapter_summary)
    
    try:
        # Get the sanitized prompt from GPT-4
        sanitized_prompt_response = await openai.chat.completions.create(
            model=MODEL_TEXT,
            messages=[{"role": "user", "content": safe_prompt_request}],
            temperature=0.7,
            max_tokens=250
        )
        image_prompt = sanitized_prompt_response.choices[0].message.content.strip().strip('"')
        print(f"    - Sanitized DALL-E Prompt: {image_prompt}")

        # Step 2: Generate the image using the new, safe prompt.
        print("    - Sending sanitized prompt to DALL-E...")
        response = await openai.images.generate(
            model=MODEL_IMAGE,
            prompt=image_prompt,
            size="1024x1792",
            quality="standard",
            n=1
        )
        image_url = response.data[0].url

        # Step 3: Download and save the image.
        output_dir = "generated_images"
        os.makedirs(output_dir, exist_ok=True)
        image_filename = f"{''.join(random.choices(string.ascii_letters + string.digits, k=12))}.png"
        output_path = os.path.join(output_dir, image_filename)
        
        async with httpx.AsyncClient() as client:
            image_response = await client.get(image_url)
            image_response.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(image_response.content)
                
        print(f"  - Chapter image saved to: {output_path}")
        return output_path

    except Exception as e:
        print(f"  - Could not generate chapter image: {e}")
        return None