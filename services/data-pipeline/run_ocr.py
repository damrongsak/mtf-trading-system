#!/usr/bin/env python3
"""
Minimal batch OCR for scanned PDFs using Gemini.
Uses PyMuPDF (fitz) to convert PDF pages to images, then Gemini for OCR.
"""
import os
import sys
import io
import time

# Check for fitz
try:
    import fitz
    print("PyMuPDF available")
except ImportError:
    print("PyMuPDF not available, trying to install...")
    os.system(f"{sys.executable} -m pip install PyMuPDF -q")
    import fitz

# Check for genai  
try:
    from google import genai
    from google.genai import types
    print("google-genai available")
except ImportError:
    print("google-genai not available, trying to install...")
    os.system(f"{sys.executable} -m pip install google-genai -q")
    from google import genai
    from google.genai import types

# Config
PDF_PATH = os.path.expanduser("~/.openclaw/workspace/pdf_books/Quantitative_Financial/Heard_on_The_Street_Quantitative_Question.pdf")
OUTPUT_MD = os.path.expanduser("~/.openclaw/workspace/markdown_books/quant_markdowns/heard_on_the_street_full.md")
START_PAGE = 0
END_PAGE = 50  # Process first 50 pages as test

API_KEY = os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    # Try to read from .env file
    env_file = os.path.expanduser("~/workspace/mtf-trading-system/.env")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                if line.startswith("GOOGLE_API_KEY="):
                    API_KEY = line.split("=", 1)[1].strip()
                    break

if not API_KEY:
    print("Error: GOOGLE_API_KEY not found")
    sys.exit(1)

print(f"API Key: {API_KEY[:20]}...")

def extract_page_as_image(doc, page_num):
    """Extract a page as PIL Image"""
    page = doc.load_page(page_num)
    zoom = 2.0 
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img_data = pix.tobytes("png")
    from PIL import Image
    pil_image = Image.open(io.BytesIO(img_data))
    return pil_image

def ocr_batch(client, images, page_numbers):
    """OCR a batch of pages using Gemini"""
    prompt = """
    You are an expert OCR engine for quantitative finance books.
    Extract ALL text, math formulas, tables, and questions from these pages.
    Output as clean markdown. Include page numbers.
    """
    contents = [prompt] + images
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=contents,
            config=types.GenerateContentConfig(temperature=0.1)
        )
        return response.text
    except Exception as e:
        return f"\n[OCR Error on pages {page_numbers}: {e}]\n"

def main():
    client = genai.Client(api_key=API_KEY)
    doc = fitz.open(PDF_PATH)
    total_pages = len(doc)
    print(f"Total pages in PDF: {total_pages}")
    
    end_idx = min(END_PAGE, total_pages)
    all_markdown = []
    
    BATCH_SIZE = 5  # Process 5 pages at a time
    
    for i in range(START_PAGE, end_idx, BATCH_SIZE):
        batch_images = []
        batch_pages = list(range(i, min(i + BATCH_SIZE, end_idx)))
        
        print(f"Processing pages {batch_pages}...")
        
        for j in batch_pages:
            img = extract_page_as_image(doc, j)
            batch_images.append(img)
            
        md_text = ocr_batch(client, batch_images, batch_pages)
        if md_text:
            all_markdown.append(f"\n<!-- Pages {batch_pages[0]+1}-{batch_pages[-1]+1} -->\n")
            all_markdown.append(md_text.strip())
        
        # Small delay to avoid rate limits
        time.sleep(3)
        
    # Save to file
    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(all_markdown))
    
    print(f"\nDone! Saved {end_idx - START_PAGE} pages to {OUTPUT_MD}")

if __name__ == "__main__":
    main()
