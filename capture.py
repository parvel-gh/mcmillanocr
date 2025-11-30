"""
Silent E-book Page Capture

A stealthy single-page capture tool. You navigate manually, 
run this script to capture the current page. No auto-navigation.

Usage:
    1. Navigate to the page you want in Chrome
    2. Run: python capture.py
    3. Repeat for each page
    4. Run: python capture.py --pdf  (to generate final PDF)
"""
import os
import sys
import time
import json
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from PIL import Image
import io
import hashlib

import config


def images_similar(img1_data, img2_data, threshold=0.98):
    """Check if two screenshots are similar (for end detection)."""
    if img1_data is None or img2_data is None:
        return False
    
    try:
        img1 = Image.open(io.BytesIO(img1_data))
        img2 = Image.open(io.BytesIO(img2_data))
        
        # Resize to small thumbnails for fast comparison
        size = (100, 100)
        img1_small = img1.resize(size).convert('L')  # Grayscale
        img2_small = img2.resize(size).convert('L')
        
        # Compare pixels
        pixels1 = list(img1_small.getdata())
        pixels2 = list(img2_small.getdata())
        
        if len(pixels1) != len(pixels2):
            return False
        
        # Calculate similarity
        matches = sum(1 for p1, p2 in zip(pixels1, pixels2) if abs(p1 - p2) < 10)
        similarity = matches / len(pixels1)
        
        return similarity >= threshold
    except Exception:
        return False
from pdf_generator import create_ocr_pdf


# Session file to track captures
SESSION_FILE = os.path.join(config.OUTPUT_FOLDER, "capture_session.json")


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


def capture_current_page(driver):
    """Capture screenshot of the main content panel only, handling nested iframes."""
    print("Capturing main content panel...")
    
    # Get page info
    title = driver.title or "Page"
    url = driver.current_url
    
    # Extract a clean name from title or URL
    clean_name = re.sub(r'[^\w\s-]', '', title)[:40].strip()
    if not clean_name:
        clean_name = "page"
    
    screenshots = []
    iframe_depth = 0  # Track how many iframes deep we are
    
    # Find the main content panel
    main_panel = None
    panel_selectors = [
        "#main-panel",
        '[id="main-panel"]',
        'div[data-panel-group-id="0"]',
        '#main-content',
        '[role="main"]',
    ]
    
    for selector in panel_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for el in elements:
                if el.is_displayed() and el.size['height'] > 100:
                    main_panel = el
                    print(f"  Found content panel: {selector}")
                    break
            if main_panel:
                break
        except Exception:
            continue
    
    if not main_panel:
        print("  Warning: Could not find #main-panel, using full page")
        main_panel = driver.find_element(By.TAG_NAME, "body")
    
    # Enter nested iframes to reach the scrollable content
    # Structure: main-panel -> outer iframe -> iframe.favre (actual scrollable content)
    # Stop when we find scrollable content
    
    def find_scrollable_depth():
        """Enter iframes one by one, checking for scrollable content at each level."""
        depth = 0
        max_depth = 4
        
        while depth < max_depth:
            # Check if current level has scrollable content
            try:
                check_scroll = driver.execute_script("""
                    var html = document.documentElement;
                    var body = document.body;
                    return {
                        htmlScroll: html ? html.scrollHeight : 0,
                        htmlClient: html ? html.clientHeight : 0,
                        bodyScroll: body ? body.scrollHeight : 0,
                        bodyClient: body ? body.clientHeight : 0
                    };
                """)
                print(f"    Level {depth}: html={check_scroll['htmlScroll']}/{check_scroll['htmlClient']}, body={check_scroll['bodyScroll']}/{check_scroll['bodyClient']}")
                
                # If scrollHeight > clientHeight + some threshold, we found scrollable content
                if check_scroll['htmlScroll'] > check_scroll['htmlClient'] + 100:
                    print(f"  Found scrollable content at level {depth}!")
                    return depth
                if check_scroll['bodyScroll'] > check_scroll['bodyClient'] + 100:
                    print(f"  Found scrollable content at level {depth}!")
                    return depth
            except Exception as e:
                print(f"    Level {depth}: error checking scroll - {e}")
            
            # Try to go deeper
            try:
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                if not iframes:
                    print(f"  No more iframes at level {depth}")
                    break
                
                entered = False
                
                # Look for iframe.favre specifically
                for iframe in iframes:
                    try:
                        iframe_class = iframe.get_attribute('class') or ''
                        if 'favre' in iframe_class.lower() and iframe.is_displayed():
                            driver.switch_to.frame(iframe)
                            depth += 1
                            print(f"  Entered iframe.favre (level {depth})")
                            entered = True
                            break
                    except Exception:
                        continue
                
                # Otherwise enter any visible iframe
                if not entered:
                    for iframe in iframes:
                        try:
                            if iframe.is_displayed() and iframe.size['height'] > 50:
                                driver.switch_to.frame(iframe)
                                depth += 1
                                print(f"  Entered iframe (level {depth})")
                                entered = True
                                break
                        except Exception:
                            continue
                
                if not entered:
                    break
            except Exception:
                break
        
        return depth
    
    # Find the level with scrollable content
    iframe_depth = find_scrollable_depth()
    print(f"  Final iframe depth: {iframe_depth}")
    
    # Get viewport height
    try:
        viewport_height = driver.execute_script("return window.innerHeight") or 700
    except Exception:
        viewport_height = 700
    
    print(f"  Page: {title[:50]}")
    print(f"  Viewport: {viewport_height}px")
    print(f"  Using scroll-until-end mode...")
    
    # Use keyboard scrolling (Page Down) which works even with shadow DOM
    # Compare screenshots to detect when content stops changing
    
    max_screenshots = 50  # Safety limit
    screenshot_num = 0
    
    # First, try to scroll to top using Home key
    driver.switch_to.default_content()
    try:
        # Click on main panel to focus it
        main_panel = driver.find_element(By.CSS_SELECTOR, "#main-panel, [id='main-panel']")
        main_panel.click()
        time.sleep(0.2)
        
        # Send Ctrl+Home to go to top
        actions = ActionChains(driver)
        actions.key_down(Keys.CONTROL).send_keys(Keys.HOME).key_up(Keys.CONTROL).perform()
        time.sleep(0.5)
    except Exception as e:
        print(f"  Could not scroll to top: {e}")
    
    print(f"  Using keyboard scroll mode (Page Down)...")
    
    prev_screenshot_data = None
    
    while screenshot_num < max_screenshots:
        # Take screenshot of main panel
        driver.switch_to.default_content()
        
        try:
            main_panel = driver.find_element(By.CSS_SELECTOR, "#main-panel, [id='main-panel']")
            screenshot_data = main_panel.screenshot_as_png
            img = Image.open(io.BytesIO(screenshot_data))
        except Exception as e:
            print(f"    Screenshot error: {e}")
            screenshot_data = driver.get_screenshot_as_png()
            img = Image.open(io.BytesIO(screenshot_data))
        
        # Check if this screenshot is very similar to the previous one (end of content)
        if prev_screenshot_data is not None and images_similar(prev_screenshot_data, screenshot_data):
            print(f"  Reached end of content after {screenshot_num} screenshots")
            break
        
        # Save screenshot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"{timestamp}_{clean_name}_{screenshot_num+1:03d}.png"
        filepath = os.path.join(config.SCREENSHOT_FOLDER, filename)
        img.save(filepath)
        
        screenshots.append({
            "path": filepath,
            "title": title,
            "url": url,
            "index": screenshot_num,
            "captured": datetime.now().isoformat()
        })
        
        print(f"  [{screenshot_num+1}] Saved")
        screenshot_num += 1
        prev_screenshot_data = screenshot_data
        
        # Scroll down using Page Down
        try:
            # Switch to the innermost iframe where scroll happens
            main_panel = driver.find_element(By.CSS_SELECTOR, "#main-panel, [id='main-panel']")
            
            # Enter iframes to get to the content
            for _ in range(iframe_depth):
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                for iframe in iframes:
                    try:
                        if iframe.is_displayed() and iframe.size['height'] > 50:
                            driver.switch_to.frame(iframe)
                            break
                    except:
                        continue
            
            # Send Page Down + 1 Arrow Down WITHOUT clicking (to avoid clicking images)
            actions = ActionChains(driver)
            actions.send_keys(Keys.PAGE_DOWN)
            actions.send_keys(Keys.ARROW_DOWN)
            actions.perform()
            time.sleep(0.5)
            
            # Return to default content for next screenshot
            driver.switch_to.default_content()
            
        except Exception as e:
            print(f"    Scroll error: {e}")
            driver.switch_to.default_content()
            break
    
    # Scroll back to top
    try:
        driver.switch_to.default_content()
        main_panel = driver.find_element(By.CSS_SELECTOR, "#main-panel, [id='main-panel']")
        main_panel.click()
        actions = ActionChains(driver)
        actions.key_down(Keys.CONTROL).send_keys(Keys.HOME).key_up(Keys.CONTROL).perform()
    except Exception:
        pass
    
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
    pdf_path = os.path.join(config.OUTPUT_FOLDER, f"ebook_capture_{timestamp}.pdf")
    
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
    print("CAPTURE SESSION STATUS")
    print(f"{'='*50}")
    print(f"Screenshots captured: {count}")
    
    if count > 0:
        print(f"\nCaptured pages:")
        seen_titles = set()
        for s in session["screenshots"]:
            title = s.get("title", "Unknown")[:50]
            if title not in seen_titles:
                seen_titles.add(title)
                print(f"  - {title}")
    
    print(f"\nCommands:")
    print(f"  python capture.py        - Capture current page")
    print(f"  python capture.py --pdf  - Generate PDF")
    print(f"  python capture.py --clear - Clear session")
    print(f"  python capture.py --status - Show this status")


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
    print("SILENT PAGE CAPTURE")
    print("="*50)
    
    driver = connect_to_browser()
    if not driver:
        return
    
    try:
        # Capture the page
        new_screenshots = capture_current_page(driver)
        
        # Add to session
        session["screenshots"].extend(new_screenshots)
        save_session(session)
        
        total = len(session["screenshots"])
        print(f"\n✓ Captured! Total screenshots: {total}")
        print(f"\nNext steps:")
        print(f"  - Navigate to next page in Chrome, then run: python capture.py")
        print(f"  - When done, generate PDF with: python capture.py --pdf")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Don't close the browser
        pass


if __name__ == "__main__":
    main()

