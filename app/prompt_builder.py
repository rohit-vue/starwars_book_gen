# app/prompt_builder.py
import json

def build_data_selection_prompt(user_prompt: str, all_data: dict) -> str:
    """Builds a prompt to ask the AI to select relevant entities from the SWAPI data."""
    data_summary = {
        "people": [p.get('name') for p in all_data.get('people', [])],
        "planets": [p.get('name') for p in all_data.get('planets', [])],
        "starships": [s.get('name') for s in all_data.get('starships', [])],
        "films": [f.get('title') for f in all_data.get('films', [])],
    }
    return f"""
Based on the user's story prompt, select a small, coherent set of entities from the provided JSON data. This will be the "cast" for the entire novel. Choose a few main characters, a primary setting (planet), and a few relevant starships.
USER PROMPT: "{user_prompt}"
AVAILABLE DATA:
{json.dumps(data_summary, indent=2)}
Your task:
Respond with a JSON object containing the *names* of the entities to use. The JSON object should have keys: "people", "planets", "starships".
Example Response:
{{
  "people": ["Luke Skywalker", "Darth Vader", "Leia Organa"],
  "planets": ["Tatooine", "Alderaan"],
  "starships": ["X-wing", "TIE Advanced x1"]
}}
"""

# In app/prompt_builder.py
def build_title_generation_prompt(user_prompt: str, title_type: str, data_context: dict = None, num_chapters: int = 0) -> str:
    """Builds a prompt for generating a book title or a list of chapter titles."""
    context_str = ""
    if data_context:
        people_names = [p.get('name') for p in data_context.get('people', [])]
        planet_names = [p.get('name') for p in data_context.get('planets', [])]
        context_str = f"The story will feature: {', '.join(people_names)} on the planet {', '.join(planet_names)}."

    if title_type == "book":
        return f"""
Generate a short, creative, and evocative book title for a Star Wars story about: '{user_prompt}'.
{context_str}
The title should sound like a real novel. Do not include 'Star Wars:' in the title itself. Only return the title, with no extra text or quotation marks.
"""
    elif title_type == "chapter_list":
        # MODIFIED: This now asks for a specific number of chapters.
        return f"""
I am writing a {num_chapters}-chapter Star Wars fan novel about: '{user_prompt}'.
{context_str}
Please generate a list of {num_chapters} creative and sequential chapter titles for this story. Return them as a numbered list (e.g., '1. The Awakening', '2. A Fading Hope').
"""

def build_chapter_image_prompt(chapter_summary: str) -> str:
    """Builds a descriptive prompt for DALL-E based on a chapter's summary."""
    return f"""
A dramatic and evocative digital painting in the style of classic Star Wars concept art, illustrating a key scene. The mood should be cinematic, with a focus on atmosphere and scale.
The scene should be based on this summary: "{chapter_summary}"
The image should be gritty and epic, with realistic textures and dramatic lighting. Do NOT include any text, titles, or logos in the image.
"""

def build_chapter_section_prompt(user_prompt: str, chapter_title: str, previous_section_summary: str, data_context: dict, word_target: int) -> str:
    """Builds the main prompt for generating a single section of a chapter's content."""
    return f"""
You are a novelist writing a Star Wars story in the second person ("You feel...", "You see...").
Your task is to write a single, detailed section of the novel.

CRITICAL INSTRUCTION: You MUST base your writing *exclusively* on the data provided in the "DATA CONTEXT" section. Do not invent new characters, planets, or major technologies. Weave the provided data into a narrative.

STORY THEME: "{user_prompt}"
CURRENT SECTION: This section is part of '{chapter_title}'.
CONTINUITY: The previous part of the story concluded with the following events: "{previous_section_summary}"

DATA CONTEXT (Your only source of truth for names, places, and specs):
---
{json.dumps(data_context, indent=2)}
---

Your task:
Write the next section of the story, continuing from the summary. Make it detailed, descriptive, and approximately {word_target} words long.
Begin writing the content directly. Do not repeat the chapter title.
"""

def build_summarization_prompt(section_text: str) -> str:
    """Builds a prompt to summarize a generated section for continuity."""
    return f"""
Summarize the following block of text in 2-3 sentences. Focus on the key actions, character movements, and plot developments. This summary will be used as a continuity guide for the next block of writing.

TEXT TO SUMMARIZE:
---
{section_text}
---
"""

def build_image_generation_prompt(user_prompt: str, data_context: dict) -> str:
    """
    Builds a more descriptive and safer prompt for the DALL-E 3 image generator.
    """
    # Describe roles instead of using direct names to avoid safety filters
    character_descriptions = []
    people = data_context.get('people', [])
    if any("Yoda" in p.get('name', '') for p in people):
        character_descriptions.append("a diminutive, wise, green-skinned Jedi Master")
    if any("Kenobi" in p.get('name', '') for p in people):
        character_descriptions.append("a noble Jedi Knight with a beard")
    if any("Palpatine" in p.get('name', '') for p in people):
        character_descriptions.append("a menacing, shadowy Emperor")
    
    # Generic descriptions if no specific characters are found
    if not character_descriptions and people:
         character_descriptions.append(f"{len(people)} robed figures")

    planets = [p.get('name') for p in data_context.get('planets', [])]
    starships = [s.get('name') for s in data_context.get('starships', [])]
    
    character_str = f"featuring {', '.join(character_descriptions)}" if character_descriptions else ""
    planet_str = f"set on the planet {', '.join(planets)}" if planets else "set in a futuristic city"
    starship_str = f"with notable starships like the {', '.join(starships)}" if starships else ""
    
    return f"""
A dramatic and cinematic digital painting in the style of classic Star Wars concept art. The scene is epic, with a focus on atmosphere, mood, and scale.
The story is about: '{user_prompt}'.
The scene should incorporate these elements: {character_str} {planet_str} {starship_str}.
The mood is gritty and awe-inspiring, with realistic textures and dramatic lighting. Do NOT include any text, titles, or logos in the image.
"""

def build_safe_image_prompt_generation_prompt(chapter_summary: str) -> str:
    """
    Asks the LLM to generate a safe, descriptive prompt for DALL-E based on the chapter summary.
    This acts as a sanitizing layer.
    """
    return f"""
Based on the following chapter summary, write a single, descriptive paragraph to be used as a prompt for an AI image generator (like DALL-E 3).
**CRITICAL INSTRUCTIONS:**
- The generated prompt MUST be safe and adhere to content policies.
- Do NOT use specific, named characters (e.g., "Rex", "Obi-Wan"). Instead, describe their roles (e.g., "a veteran clone trooper in customized armor," "a noble Jedi Master").
- Do NOT describe graphic violence or gore.
- Focus on creating a cinematic, atmospheric, and visually rich scene.
**Chapter Summary:** "{chapter_summary}"
**Your Task:**
Create a single-paragraph DALL-E prompt that captures the essence of this summary. The prompt should be in the style of "A dramatic digital painting..." and should be safe for all audiences.
**Example of a good, safe output:**
"A dramatic digital painting of a veteran clone trooper, his armor showing signs of battle, taking cover in a lush, alien swamp. The mood is one of tense solitude, with shafts of light breaking through the dense canopy above."
Now, generate the safe and descriptive prompt.
"""