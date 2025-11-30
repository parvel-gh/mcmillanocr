# E-book Chapter Scraper

A Python tool to scrape e-book chapters from Macmillan Achieve and save them as searchable, OCR-enabled PDFs.

## Features

- Connects to an existing Chrome browser session (you login manually)
- Auto-detects chapter sections from the table of contents
- Navigates through each section automatically
- Captures full-page screenshots with scrolling
- Generates OCR-enabled PDFs (searchable and selectable text)

## Prerequisites

### 1. Python 3.8+

Make sure you have Python 3.8 or later installed.

### 2. Install Tesseract OCR

Tesseract is required for OCR text extraction.

**Windows:**
1. Download the installer from: https://github.com/UB-Mannheim/tesseract/wiki
2. Run the installer (default path: `C:\Program Files\Tesseract-OCR`)
3. Add Tesseract to your PATH, or update `TESSERACT_PATH` in `config.py`:
   ```python
   TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
   ```

**macOS:**
```bash
brew install tesseract
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install tesseract-ocr
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Chrome Browser

You need Google Chrome installed on your system.

## Usage

### Step 1: Start Chrome with Remote Debugging

Close all Chrome windows first, then start Chrome with remote debugging enabled:

**Windows (Command Prompt):**
```cmd
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```

**Windows (PowerShell):**
```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```

**macOS:**
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
```

**Linux:**
```bash
google-chrome --remote-debugging-port=9222
```

### Step 2: Login and Navigate

1. In the Chrome window that opened, go to: https://achieve.macmillanlearning.com
2. Login with your credentials
3. Navigate to your course and open the e-book
4. **Expand the chapter** you want to scrape in the table of contents (left sidebar)
5. Click on any section within that chapter to load the e-book view

### Step 3: Run the Scraper

```bash
python scraper.py
```

The scraper will:
1. Connect to your Chrome browser
2. Detect all sections in the currently expanded chapter
3. Navigate through each section and capture screenshots
4. Generate an OCR-enabled PDF in the `output` folder

## Output

- **Screenshots**: Saved in `output/screenshots/`
- **PDF**: Saved in `output/` with naming format `Chapter_Title_TIMESTAMP.pdf`

## Configuration

Edit `config.py` to customize:

- `CHROME_DEBUG_PORT`: Chrome remote debugging port (default: 9222)
- `OUTPUT_FOLDER`: Where to save PDFs
- `TESSERACT_PATH`: Path to Tesseract executable
- `TIMEOUTS`: Various timing settings for page loading
- `PDF_SETTINGS`: PDF generation options

## Troubleshooting

### "Failed to connect to Chrome"

- Make sure Chrome is running with `--remote-debugging-port=9222`
- Close ALL other Chrome windows before starting with the debug flag
- Check that port 9222 is not in use by another application

### "No sections found"

- Make sure the Table of Contents sidebar is visible
- Expand the chapter you want to scrape (click the arrow/chevron)
- Ensure you're on an e-book page (not course home or other pages)

### OCR not working

- Verify Tesseract is installed: `tesseract --version`
- Update `TESSERACT_PATH` in `config.py` if needed
- The PDF will still be created without OCR if Tesseract fails

### Screenshots look wrong

- Try adjusting `TIMEOUTS` in `config.py` (increase delays)
- Make sure the page is fully loaded before running the scraper
- Close any popups or overlays on the page

## File Structure

```
ebookscrapper/
├── config.py           # Configuration settings
├── scraper.py          # Main scraper logic
├── pdf_generator.py    # PDF creation with OCR
├── requirements.txt    # Python dependencies
├── README.md           # This file
└── output/             # Generated files
    ├── screenshots/    # Captured screenshots
    └── *.pdf           # Generated PDFs
```

## Legal Notice

This tool is intended for personal use to create accessible copies of e-books you have legitimate access to. Please respect copyright laws and the terms of service of the e-book platform. Do not distribute scraped content.

