"""
Configuration settings for the e-book scraper.
"""
import os

# Chrome remote debugging settings
CHROME_DEBUG_HOST = "localhost"
CHROME_DEBUG_PORT = 9222

# Output settings
OUTPUT_FOLDER = os.path.join(os.path.dirname(__file__), "output")
SCREENSHOT_FOLDER = os.path.join(OUTPUT_FOLDER, "screenshots")

# Tesseract OCR path (update if not in system PATH)
# Windows example: r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# Leave as None to use system PATH
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# CSS Selectors for Achieve e-book
SELECTORS = {
    # Table of contents sidebar
    "toc_sidebar": '[class*="TableOfContents"]',
    
    # Chapter items in sidebar (expanded chapter with sections)
    "chapter_expanded": '[aria-expanded="true"]',
    
    # Section links within a chapter
    "section_links": 'a[href*="/e-book/"]',
    
    # Main content area
    "content_area": '[class*="EbookContent"], [class*="ebook-content"], main, article',
    
    # E-book tab (to ensure we're on the right tab)
    "ebook_tab": '[role="tab"][aria-selected="true"]',
    
    # Navigation instructions close button (to dismiss if present)
    "nav_instructions_close": '[class*="NavigationInstructions"] button, [aria-label="Close"]',
    
    # Page content container
    "page_container": '[class*="PageContent"], [class*="page-content"], .ebook-page',
}

# Timing settings (in seconds)
TIMEOUTS = {
    "page_load": 30,
    "element_wait": 10,
    "after_click": 2,
    "scroll_delay": 0.5,
    "screenshot_delay": 0.3,
}

# Screenshot settings
SCREENSHOT_SETTINGS = {
    "format": "png",
    "quality": 95,  # For JPEG format
}

# PDF settings
PDF_SETTINGS = {
    "page_size": "A4",
    "margin": 20,  # pixels
    "dpi": 150,
}

# Ensure output directories exist
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(SCREENSHOT_FOLDER, exist_ok=True)

