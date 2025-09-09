# app/book_pdf_exporter.py
from weasyprint import HTML, CSS
from jinja2 import Template
import os
from datetime import datetime
import pathlib

def save_book_as_pdf(title: str, book_data: dict, filename: str) -> str:
    """
    Generates the final, professionally formatted PDF with all structure requirements met.
    """
    output_dir = "generated_books"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)

    # --- Prepare all data for the template ---
    all_sections_for_toc = []
    has_prologue = bool(book_data.get('prologue_text'))
    has_epilogue = bool(book_data.get('epilogue_text'))
    # Use preface_text directly in template context
    
    # Correctly build the TOC including a check for the preface
    if book_data.get('preface_text'):
        all_sections_for_toc.append({"title": "Preface", "href": "#preface"})
    if has_prologue:
        all_sections_for_toc.append({"title": "Prologue", "href": "#prologue"})
    for i, ch in enumerate(book_data.get("chapters", [])):
        all_sections_for_toc.append({"title": ch["heading"], "href": f"#chapter-{i+1}"})
    if has_epilogue:
        all_sections_for_toc.append({"title": "Epilogue", "href": "#epilogue"})

    template_context = {
        "book_title": title,
        "print_date": datetime.now().strftime("%B %d, %Y"),
        "toc_entries": all_sections_for_toc,
        "has_prologue": has_prologue,
        "has_epilogue": has_epilogue,
        **book_data
    }
    
    # --- FINAL, CORRECTED HTML TEMPLATE ---
    html_template = Template("""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>{{ book_title }}</title></head>
    <body>
        <div class="page swapi-call-page debug-page"><h1>SWAPI API</h1><pre>{{ swapi_call_text }}</pre></div>
        <div class="page swapi-json-page debug-page"><pre>{{ swapi_json_output }}</pre></div>
        
        <!-- FIX #1: Correctly structured four blank pages -->
        <div class="page blank-page"></div>
        <div class="page blank-page"></div>
        <div class="page blank-page"></div>
        <div class="page blank-page"></div>
        
        {% if image_path %}
        <div class="page image-page">
            <div class="image-container">
                <img src="{{ image_path }}" alt="AI Generated Book Image">
            </div>
        </div>
        {% endif %}
        
        <!-- FIX #2: Title page without the date -->
        <div class="page title-page">
            <div class="title-main-block">
                <div class="title-decoration">✧</div>
                <h1 class="book-title">{{ book_title }}</h1>
                <div class="title-decoration">✦</div>
                <h2 class="subtitle">A STAR WARS FAN NOVEL</h2>
            </div>
        </div>
        
        <!-- FIX #2: New, separate page for the print date -->
        <div class="page print-date-page">
            <p>A personalized edition created on<br>{{ print_date }}</p>
        </div>

        <div class="page blank-page"></div><div class="page blank-page"></div>
        
        <div class="page toc-page">
            <h1>Table of Contents</h1>
            <div class="toc-list">
            {% for entry in toc_entries %}
                <div class="toc-entry">
                    <span class="entry-title">{{ entry.title }}</span>
                    <span class="leader"></span>
                    <a href="{{ entry.href }}"></a>
                </div>
            {% endfor %}
            </div>
        </div>

        <div class="page blank-page"></div>
        
        <!-- FIX #3: Added the Preface block -->
        {% if preface_text %}
        <div class="page content-page" id="preface">
            <h2>Preface</h2>
            <div class="content-block">{% for p in preface_text.split('\\n\\n') %}<p>{{ p }}</p>{% endfor %}</div>
        </div>
        <div class="page blank-page"></div>
        {% endif %}
        
        {% if has_prologue %}
        <div class="page content-page" id="prologue">
            <h2>Prologue</h2>
            <div class="content-block">{% for p in prologue_text.split('\\n\\n') %}<p>{{ p }}</p>{% endfor %}</div>
        </div>
        <div class="page blank-page"></div>
        {% endif %}

        {% for chapter in chapters %}
        <div class="page chapter-title-page">
            <div class="chapter-title-content">
                <span class="chapter-number">Chapter {{ loop.index }}</span>
                <h2>{{ chapter.heading }}</h2>
            </div>
        </div>

        {% if chapter.image_path %}
        <div class="page image-page">
            <div class="image-container">
                <img src="{{ chapter.image_path }}" alt="Image for Chapter {{ loop.index }}">
            </div>
        </div>
        {% endif %} <!-- <<< ADD THIS LINE -->

        <div class="page content-page" id="chapter-{{ loop.index }}">
            <div class="content-block">
            {% for p in chapter.content.split('\\n\\n') %}<p>{{ p }}</p>{% endfor %}
            </div>
        </div>
        {% endfor %} 
        
        {% if has_epilogue %}
        <div class="page blank-page"></div>
        <div class="page content-page" id="epilogue">
            <h2>Epilogue</h2>
            <div class="content-block">{% for p in epilogue_text.split('\\n\\n') %}<p>{{ p }}</p>{% endfor %}</div>
        </div>
        {% endif %}
    </body>
    </html>
    """)
    rendered_html = html_template.render(template_context)

    # --- CSS Styling with Restored Print Date Page Style ---
    fonts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'fonts'))
    baskerville_regular_uri = pathlib.Path(os.path.abspath(os.path.join(fonts_dir, 'LibreBaskerville-Regular.ttf'))).as_uri()
    baskerville_italic_uri = pathlib.Path(os.path.abspath(os.path.join(fonts_dir, 'LibreBaskerville-Italic.ttf'))).as_uri()
    baskerville_bold_uri = pathlib.Path(os.path.abspath(os.path.join(fonts_dir, 'LibreBaskerville-Bold.ttf'))).as_uri()

    font_config = f"""
    @font-face  {{ font-family: 'Baskerville'; src: url('{baskerville_regular_uri}'); }}
    @font-face {{ font-family: 'Baskerville'; font-style: italic; src: url('{baskerville_italic_uri}'); }}
    @font-face {{ font-family: 'Baskerville'; font-weight: bold; src: url('{baskerville_bold_uri}'); }}
    """
    
    main_css = """
    @page { size: 140mm 216mm; margin: 25mm; }
    @page:blank { @bottom-center { content: ""; } }
    @page main { @bottom-center { content: counter(page); font-family: 'Baskerville', serif; font-size: 9pt; } }
    @page image-page-style { margin: 0; }

    body { font-family: 'Baskerville', serif; font-size: 11pt; line-height: 1.6; -webkit-font-smoothing: antialiased; }

    .page { page-break-after: always; position: relative; height: 100%; }
    body > div:last-of-type { page-break-after: auto; }

    h1, h2, h3 { font-weight: bold; margin: 0; text-align: center; }

    .debug-page pre {
        white-space: pre-wrap;
        word-wrap: break-word;
        font-size: 8pt;
        line-height: 1.5;
    }

    .image-page {
        page: image-page-style;
        display: flex;
        justify-content: center;
        align-items: center;
        width: 100%;
        height: 100%;
        background-color: #000000;
    }
    .image-container img { max-width: 100%; max-height: 100%; object-fit: contain; }

    .title-page { display: flex; flex-direction: column; align-items: center; text-align: center; }
    .title-main-block { margin: auto 0; }
    .book-title { font-size: 38pt; font-weight: bold; margin: 0.5em 0; line-height: 1.2; }
    .subtitle { font-size: 14pt; margin: 1em 0; letter-spacing: 0.2em; text-transform: uppercase; }
    .title-decoration { font-size: 24pt; margin: 1em 0; color: #555; }
    
   .print-date-page {
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
        height: 100vh;
        width: 100%;
        padding: 32mm; /* Your book's margin */
        box-sizing: border-box;
        }

    .print-date-page p {
        text-align: center;
        font-style: italic;
        font-size: 10pt;
        margin-bottom: 20pt; /* Push it a bit above the bottom */
        }
    .toc-page { padding: 2em 0; page-break-inside: avoid; page: main; }
    .toc-page h1 { font-size: 32pt; margin-bottom: 1.2em; letter-spacing: 0.1em; }
    .toc-list { width: 85%; margin: 0 auto; }
    .toc-entry { display: flex; align-items: baseline; margin-bottom: 1.2em; font-size: 12pt; }
    .toc-entry .leader { flex-grow: 1; border-bottom: 1px dotted rgba(0,0,0,0.5); margin: 0 0.5em; position: relative; top: -0.2em; }
    .toc-entry a { display: none; }

    /* ...and replace it with this corrected version. */
    .toc-page { padding: 2em 0; page-break-inside: avoid; }
    .toc-page h1 { font-size: 32pt; margin-bottom: 1.0em; letter-spacing: 0.1em; } /* Tighter margin */
    .toc-list { width: 85%; margin: 0 auto; }
    .toc-entry { display: flex; align-items: baseline; margin-bottom: 0.9em; font-size: 12pt; } /* More compact */
    .toc-entry .leader { flex-grow: 1; border-bottom: 1px dotted rgba(0,0,0,0.5); margin: 0 0.5em; position: relative; top: -0.2em; }
    .entry-title { flex-shrink: 0; padding-right: 0.5em; }
    .toc-entry a { display: none; }
    

    .chapter-title-page { display: flex; align-items: center; justify-content: center; }
    .chapter-title-content { text-align: center; padding: 2em; }
    .chapter-number { display: block; font-size: 16pt; font-style: italic; color: #666; margin-bottom: 1.5em; text-transform: uppercase; }
    .chapter-title-content h2 { font-size: 32pt; font-weight: bold; text-transform: uppercase; letter-spacing: 0.1em; line-height: 1.3; }

    .content-page {
        padding: 0;
    }

    .main-content-body {
        /* This resets the page counter to 1 right before the first chapter starts */
        counter-reset: page 1;
    }

    /* This applies the 'main' page style (with numbers) to ALL pages inside the main-content-body */
    .main-content-body .page {
        page: main;
    }

    /* This applies the 'main' page style ONLY to the epilogue */
    #epilogue.page {
        page: main;
    }

    /* --- General Content Styling --- */
    .content-page h2 { font-size: 20pt; text-transform: uppercase; margin-bottom: 2.5em; letter-spacing: 0.1em; }
    .content-block { margin: 0 auto; max-width: 100%; }
    .content-block p { text-align: justify; text-indent: 2em; margin-bottom: 0; line-height: 1.7; hyphens: auto; }
    .content-block p + p { margin-top: 1em; }
    .content-block p:first-child { text-indent: 0; }
    .content-block p:first-child::first-letter { font-size: 3.5em;font-weight: bold; margin-right: -0.1em; }

    .print-date-page {
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .print-date-page p {
        text-align: center;
        font-style: italic;
        font-size: 10pt;
    }
-
    """
    
    css = CSS(string=font_config + main_css)
    # Ensure you have renamed your project folder to have a clean path
    base_url = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    HTML(string=rendered_html, base_url=base_url).write_pdf(output_path, stylesheets=[css])
    
    return output_path