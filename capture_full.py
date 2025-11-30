"""
Full Page E-book Capture (Single Screenshot)

Captures the entire scrollable content in ONE screenshot using Chrome DevTools Protocol.
No scrolling needed - captures everything at once.

Usage:
    1. Navigate to the page you want in Chrome
    2. Run: python capture_full.py
    3. Repeat for each page
    4. Run: python capture_full.py --pdf  (to generate final PDF)
"""
import os
import sys
import time
import json
import re
import base64
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from PIL import Image
import io

import config
from pdf_generator import create_ocr_pdf


# Session file to track captures
SESSION_FILE = os.path.join(config.OUTPUT_FOLDER, "capture_full_session.json")


def load_session():
    """Load existing capture session or create new one."""
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, 'r') as f:
            return json.load(f)
    return {"screenshots": [], "started": datetime.now().isoformat()}


def save_session(session):
    """Save capture session."""
    with open(SESSION_FILE, 'w') as f:
        json.dump(session, f, indent=2)


def connect_to_browser():
    """Connect to existing Chrome browser."""
    chrome_options = Options()
    chrome_options.add_experimental_option(
        "debuggerAddress", 
        f"{config.CHROME_DEBUG_HOST}:{config.CHROME_DEBUG_PORT}"
    )
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        print(f"Cannot connect to Chrome: {e}")
        print("\nMake sure Chrome is running with: --remote-debugging-port=9222")
        return None


def capture_full_page(driver):
    """Capture the full iframe content using Print to PDF."""
    print("Capturing iframe content using Print to PDF...")
    
    # Get page info
    title = driver.title or "Page"
    original_url = driver.current_url
    
    # Extract a clean name from title
    clean_name = re.sub(r'[^\w\s-]', '', title)[:40].strip()
    if not clean_name:
        clean_name = "page"
    
    screenshots = []
    
    # Find the iframe with the actual e-book content and get its src
    iframe_src = None
    try:
        main_panel = driver.find_element(By.CSS_SELECTOR, "#main-panel, [id='main-panel']")
        print(f"  Found main panel")
        
        # Find iframes and get their src URLs - go deep to find content
        iframes = main_panel.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            if iframe.is_displayed() and iframe.size['height'] > 50:
                src = iframe.get_attribute('src')
                print(f"  L1 iframe: {src[:70]}..." if src and len(src) > 70 else f"  L1 iframe: {src}")
                
                # Enter first iframe
                driver.switch_to.frame(iframe)
                
                # Look for nested iframes
                level2_iframes = driver.find_elements(By.TAG_NAME, "iframe")
                for l2_iframe in level2_iframes:
                    if l2_iframe.is_displayed() and l2_iframe.size['height'] > 50:
                        l2_src = l2_iframe.get_attribute('src')
                        l2_class = l2_iframe.get_attribute('class') or ''
                        print(f"  L2 iframe ({l2_class[:20]}): {l2_src[:60]}..." if l2_src and len(l2_src) > 60 else f"  L2 iframe: {l2_src}")
                        
                        # Enter second iframe
                        driver.switch_to.frame(l2_iframe)
                        
                        # Check for level 3 iframes (the actual content)
                        level3_iframes = driver.find_elements(By.TAG_NAME, "iframe")
                        for l3_iframe in level3_iframes:
                            if l3_iframe.is_displayed():
                                l3_src = l3_iframe.get_attribute('src')
                                l3_class = l3_iframe.get_attribute('class') or ''
                                print(f"  L3 iframe ({l3_class[:20]}): {l3_src[:60]}..." if l3_src and len(l3_src) > 60 else f"  L3 iframe: {l3_src}")
                                
                                # Look for jigsaw or content URLs
                                if l3_src and ('jigsaw' in l3_src or 'book' in l3_src):
                                    iframe_src = l3_src
                                    print(f"  >> Found content URL!")
                                    break
                        
                        # If not found at L3, check current frame's URL
                        if not iframe_src:
                            current_url = driver.execute_script("return window.location.href")
                            print(f"  L2 current URL: {current_url[:70]}..." if len(current_url) > 70 else f"  L2 current URL: {current_url}")
                            if 'jigsaw' in current_url or 'book' in current_url:
                                iframe_src = current_url
                                print(f"  >> Using L2 URL as content!")
                        
                        driver.switch_to.parent_frame()  # Back to L1
                        
                        if iframe_src:
                            break
                
                driver.switch_to.default_content()
                
                if iframe_src:
                    break
                    
                # If nothing found, use the outer iframe src
                if src and not iframe_src:
                    iframe_src = src
                    
    except Exception as e:
        print(f"  Error finding iframe: {e}")
        import traceback
        traceback.print_exc()
        driver.switch_to.default_content()
    
    if not iframe_src:
        print("  Could not find iframe source URL")
        return screenshots
    
    # Navigate to the iframe URL directly
    print(f"  Navigating to iframe content...")
    driver.get(iframe_src)
    time.sleep(2)  # Wait for page to load
    
    # Now print to PDF - this should capture the full content
    try:
        print(f"  Generating PDF of iframe content...")
        
        # Print to PDF
        pdf_data = driver.execute_cdp_cmd('Page.printToPDF', {
            'printBackground': True,
            'preferCSSPageSize': False,
            'paperWidth': 8.27,  # A4 width in inches
            'paperHeight': 200,  # Very tall to capture all content
            'marginTop': 0.2,
            'marginBottom': 0.2,
            'marginLeft': 0.2,
            'marginRight': 0.2,
            'scale': 0.9,
        })
        
        # Save the PDF
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        pdf_filename = f"{timestamp}_{clean_name}_content.pdf"
        pdf_filepath = os.path.join(config.OUTPUT_FOLDER, pdf_filename)
        
        pdf_bytes = base64.b64decode(pdf_data['data'])
        with open(pdf_filepath, 'wb') as f:
            f.write(pdf_bytes)
        
        file_size = len(pdf_bytes) / 1024
        print(f"  Saved PDF: {pdf_filename} ({file_size:.1f} KB)")
        
        screenshots.append({
            "path": pdf_filepath,
            "title": title,
            "url": iframe_src,
            "type": "pdf",
            "captured": datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"  Print to PDF failed: {e}")
    
    # Navigate back to original page
    print(f"  Returning to original page...")
    driver.get(original_url)
    time.sleep(2)
    
    return screenshots


def generate_pdf(session):
    """Generate PDF from all captured screenshots."""
    if not session["screenshots"]:
        print("No screenshots to convert. Capture some pages first!")
        return
    
    print(f"\nGenerating PDF from {len(session['screenshots'])} screenshots...")
    
    # Get all screenshot paths in order
    paths = [s["path"] for s in session["screenshots"] if os.path.exists(s["path"])]
    
    if not paths:
        print("No screenshot files found!")
        return
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_path = os.path.join(config.OUTPUT_FOLDER, f"ebook_full_{timestamp}.pdf")
    
    # Create PDF
    create_ocr_pdf(paths, pdf_path, "E-book Capture")
    
    print(f"\n✓ PDF saved: {pdf_path}")
    
    # Ask to clear session
    response = input("\nClear capture session? (y/n): ").strip().lower()
    if response == 'y':
        clear_session()


def clear_session():
    """Clear the capture session."""
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)
    print("Session cleared.")


def show_status(session):
    """Show current session status."""
    count = len(session["screenshots"])
    print(f"\n{'='*50}")
    print("FULL PAGE CAPTURE SESSION STATUS")
    print(f"{'='*50}")
    print(f"Screenshots captured: {count}")
    
    if count > 0:
        print(f"\nCaptured pages:")
        for s in session["screenshots"]:
            title = s.get("title", "Unknown")[:50]
            size = f"{s.get('width', '?')}x{s.get('height', '?')}"
            print(f"  - {title} ({size})")
    
    print(f"\nCommands:")
    print(f"  python capture_full.py        - Capture current page (full)")
    print(f"  python capture_full.py --pdf  - Generate PDF")
    print(f"  python capture_full.py --clear - Clear session")
    print(f"  python capture_full.py --status - Show this status")


def main():
    args = sys.argv[1:]
    
    # Load session
    session = load_session()
    
    # Handle commands
    if "--pdf" in args:
        generate_pdf(session)
        return
    
    if "--clear" in args:
        clear_session()
        return
    
    if "--status" in args:
        show_status(session)
        return
    
    if "--help" in args or "-h" in args:
        print(__doc__)
        return
    
    # Default: capture current page
    print("\n" + "="*50)
    print("FULL PAGE CAPTURE (Single Screenshot)")
    print("="*50)
    
    driver = connect_to_browser()
    if not driver:
        return
    
    try:
        # Capture the full page
        new_screenshots = capture_full_page(driver)
        
        # Add to session
        session["screenshots"].extend(new_screenshots)
        save_session(session)
        
        total = len(session["screenshots"])
        print(f"\n✓ Captured! Total pages: {total}")
        print(f"\nNext steps:")
        print(f"  - Navigate to next page in Chrome, then run: python capture_full.py")
        print(f"  - When done, generate PDF with: python capture_full.py --pdf")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        pass


if __name__ == "__main__":
    main()

