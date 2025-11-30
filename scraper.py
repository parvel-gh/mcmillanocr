"""
E-book Chapter Scraper

Connects to an existing Chrome browser session, scrapes an entire e-book chapter
by auto-navigating through sections, and captures screenshots for PDF generation.
"""
import os
import re
import time
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
)
from PIL import Image
import io

import config
from pdf_generator import create_ocr_pdf


class EbookScraper:
    """Scraper for Macmillan Achieve e-book content."""

    def __init__(self):
        self.driver = None
        self.screenshots = []
        self.chapter_title = ""
        self.section_titles = []

    def connect_to_browser(self):
        """Connect to an existing Chrome browser with remote debugging enabled."""
        print(f"Connecting to Chrome at {config.CHROME_DEBUG_HOST}:{config.CHROME_DEBUG_PORT}...")
        
        chrome_options = Options()
        chrome_options.add_experimental_option(
            "debuggerAddress", 
            f"{config.CHROME_DEBUG_HOST}:{config.CHROME_DEBUG_PORT}"
        )
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            print(f"Connected! Current URL: {self.driver.current_url}")
            print(f"Page title: {self.driver.title}")
            return True
        except Exception as e:
            print(f"Failed to connect to Chrome: {e}")
            print("\nMake sure Chrome is running with remote debugging enabled:")
            print('  chrome.exe --remote-debugging-port=9222')
            return False

    def wait_for_element(self, selector, timeout=None, by=By.CSS_SELECTOR):
        """Wait for an element to be present and return it."""
        timeout = timeout or config.TIMEOUTS["element_wait"]
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            return element
        except TimeoutException:
            return None

    def wait_for_clickable(self, selector, timeout=None, by=By.CSS_SELECTOR):
        """Wait for an element to be clickable and return it."""
        timeout = timeout or config.TIMEOUTS["element_wait"]
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, selector))
            )
            return element
        except TimeoutException:
            return None

    def dismiss_navigation_instructions(self):
        """Dismiss the navigation instructions popup if present."""
        try:
            close_buttons = self.driver.find_elements(
                By.CSS_SELECTOR, 
                config.SELECTORS["nav_instructions_close"]
            )
            for btn in close_buttons:
                if btn.is_displayed():
                    btn.click()
                    time.sleep(0.5)
                    print("Dismissed navigation instructions popup")
                    break
        except Exception:
            pass  # Popup not present or already dismissed

    def get_current_chapter_info(self):
        """Extract current chapter title and sections from the sidebar."""
        print("Analyzing chapter structure...")
        
        # Try to find the expanded chapter in the table of contents
        sections = []
        chapter_title = "Chapter"
        
        try:
            # Look for expanded chapter items
            expanded_items = self.driver.find_elements(
                By.CSS_SELECTOR, 
                '[aria-expanded="true"]'
            )
            
            for item in expanded_items:
                # Get chapter title
                try:
                    title_text = item.text.strip().split('\n')[0]
                    if title_text and 'Ch' in title_text:
                        chapter_title = title_text
                        break
                except Exception:
                    continue
            
            # Find all section links within the table of contents
            # Look for links that appear to be sections (nested under chapters)
            all_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/e-book"]')
            
            # Filter to only visible links that look like chapter sections
            for link in all_links:
                try:
                    if link.is_displayed():
                        text = link.text.strip()
                        href = link.get_attribute('href')
                        
                        # Check if this looks like a section link (has section number pattern)
                        if text and href:
                            # Match patterns like "4.1", "Ch 4 Introduction", etc.
                            if re.match(r'^\d+\.\d+', text) or 'Introduction' in text:
                                sections.append({
                                    'title': text,
                                    'href': href,
                                    'element': link
                                })
                except StaleElementReferenceException:
                    continue
            
            # If we couldn't find sections with the pattern, look for selected item and siblings
            if not sections:
                # Find currently selected/active link
                selected = self.driver.find_elements(
                    By.CSS_SELECTOR, 
                    '[aria-selected="true"], [class*="selected"], [class*="active"]'
                )
                for item in selected:
                    try:
                        parent = item.find_element(By.XPATH, '..')
                        sibling_links = parent.find_elements(By.CSS_SELECTOR, 'a')
                        for link in sibling_links:
                            if link.is_displayed():
                                text = link.text.strip()
                                href = link.get_attribute('href')
                                if text and href:
                                    sections.append({
                                        'title': text,
                                        'href': href,
                                        'element': link
                                    })
                    except Exception:
                        continue
                        
        except Exception as e:
            print(f"Error analyzing chapter structure: {e}")
        
        self.chapter_title = chapter_title
        print(f"Chapter: {chapter_title}")
        print(f"Found {len(sections)} sections")
        
        for i, section in enumerate(sections):
            print(f"  {i+1}. {section['title']}")
        
        return sections

    def capture_page_screenshots(self, section_title):
        """Capture screenshots of the current page content by scrolling."""
        print(f"  Capturing: {section_title}")
        screenshots = []
        
        time.sleep(config.TIMEOUTS["after_click"])
        
        # Try to find the main content area
        content_selectors = [
            '[class*="EbookContent"]',
            '[class*="ebook-content"]',
            '[class*="PageContent"]',
            '[class*="page-content"]',
            'main',
            'article',
            '[role="main"]',
            '.content',
        ]
        
        content_area = None
        for selector in content_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elements:
                    if el.is_displayed() and el.size['height'] > 100:
                        content_area = el
                        break
                if content_area:
                    break
            except Exception:
                continue
        
        if not content_area:
            # Fall back to taking full page screenshot
            print("    Using full page screenshot mode")
            content_area = self.driver.find_element(By.TAG_NAME, 'body')
        
        # Get the scrollable container and its dimensions
        try:
            scroll_height = self.driver.execute_script(
                "return arguments[0].scrollHeight", content_area
            )
            client_height = self.driver.execute_script(
                "return arguments[0].clientHeight", content_area
            )
        except Exception:
            # Use window scrolling
            scroll_height = self.driver.execute_script("return document.body.scrollHeight")
            client_height = self.driver.execute_script("return window.innerHeight")
        
        # Calculate number of screenshots needed
        viewport_height = client_height or 800
        num_screenshots = max(1, (scroll_height // viewport_height) + 1)
        
        print(f"    Content height: {scroll_height}px, viewport: {viewport_height}px")
        print(f"    Taking {num_screenshots} screenshot(s)")
        
        # Scroll to top first
        self.driver.execute_script("window.scrollTo(0, 0)")
        time.sleep(config.TIMEOUTS["scroll_delay"])
        
        for i in range(num_screenshots):
            # Scroll to position
            scroll_pos = i * viewport_height
            self.driver.execute_script(f"window.scrollTo(0, {scroll_pos})")
            time.sleep(config.TIMEOUTS["scroll_delay"])
            
            # Take screenshot
            screenshot_data = self.driver.get_screenshot_as_png()
            img = Image.open(io.BytesIO(screenshot_data))
            
            # Save screenshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = re.sub(r'[^\w\s-]', '', section_title)[:30]
            filename = f"{safe_title}_{i+1}_{timestamp}.png"
            filepath = os.path.join(config.SCREENSHOT_FOLDER, filename)
            img.save(filepath)
            
            screenshots.append({
                'path': filepath,
                'section': section_title,
                'index': i,
                'scroll_pos': scroll_pos,
            })
            
            print(f"    Saved: {filename}")
            
            # Check if we've reached the bottom
            current_scroll = self.driver.execute_script("return window.pageYOffset")
            max_scroll = self.driver.execute_script(
                "return document.body.scrollHeight - window.innerHeight"
            )
            if current_scroll >= max_scroll:
                break
        
        # Scroll back to top
        self.driver.execute_script("window.scrollTo(0, 0)")
        
        return screenshots

    def navigate_to_section(self, section):
        """Navigate to a section by clicking its link."""
        try:
            # Re-find the element to avoid stale reference
            link = self.driver.find_element(By.CSS_SELECTOR, f'a[href="{section["href"]}"]')
            
            # Scroll element into view and click
            self.driver.execute_script("arguments[0].scrollIntoView(true);", link)
            time.sleep(0.3)
            
            link.click()
            time.sleep(config.TIMEOUTS["after_click"])
            
            # Wait for content to load
            WebDriverWait(self.driver, config.TIMEOUTS["page_load"]).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            return True
        except Exception as e:
            print(f"  Failed to navigate to section: {e}")
            return False

    def scrape_chapter(self):
        """Main method to scrape an entire chapter."""
        print("\n" + "=" * 60)
        print("E-BOOK CHAPTER SCRAPER")
        print("=" * 60)
        
        # Connect to browser
        if not self.connect_to_browser():
            return False
        
        # Dismiss any popups
        self.dismiss_navigation_instructions()
        
        # Get chapter structure
        sections = self.get_current_chapter_info()
        
        if not sections:
            print("\nNo sections found. Please ensure:")
            print("1. You are on an e-book page")
            print("2. A chapter is expanded in the table of contents")
            print("3. The sidebar is visible")
            
            # Try to capture just the current page
            print("\nAttempting to capture current page only...")
            current_url = self.driver.current_url
            section_title = self.driver.title or "Page"
            screenshots = self.capture_page_screenshots(section_title)
            self.screenshots.extend(screenshots)
            self.section_titles.append(section_title)
        else:
            # Navigate through each section and capture
            print(f"\nStarting to scrape {len(sections)} sections...")
            
            for i, section in enumerate(sections):
                print(f"\n[{i+1}/{len(sections)}] {section['title']}")
                
                # Navigate to section
                if self.navigate_to_section(section):
                    # Capture screenshots
                    screenshots = self.capture_page_screenshots(section['title'])
                    self.screenshots.extend(screenshots)
                    self.section_titles.append(section['title'])
                else:
                    print(f"  Skipping section due to navigation error")
        
        # Generate PDF
        if self.screenshots:
            print("\n" + "-" * 60)
            print("Generating PDF...")
            
            # Create safe filename
            safe_chapter = re.sub(r'[^\w\s-]', '', self.chapter_title)[:50]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pdf_filename = f"{safe_chapter}_{timestamp}.pdf"
            pdf_path = os.path.join(config.OUTPUT_FOLDER, pdf_filename)
            
            # Generate OCR-enabled PDF
            screenshot_paths = [s['path'] for s in self.screenshots]
            create_ocr_pdf(screenshot_paths, pdf_path, self.chapter_title)
            
            print(f"\nSUCCESS! PDF saved to: {pdf_path}")
            print(f"Total screenshots: {len(self.screenshots)}")
            print(f"Sections captured: {len(self.section_titles)}")
        else:
            print("\nNo screenshots captured. PDF not generated.")
            return False
        
        return True

    def close(self):
        """Clean up resources (but don't close the browser)."""
        # We don't close the browser since user may still need it
        self.driver = None


def main():
    """Main entry point."""
    scraper = EbookScraper()
    
    try:
        success = scraper.scrape_chapter()
        if success:
            print("\n✓ Scraping completed successfully!")
        else:
            print("\n✗ Scraping failed or incomplete")
    except KeyboardInterrupt:
        print("\n\nScraping interrupted by user")
    except Exception as e:
        print(f"\n✗ Error during scraping: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.close()


if __name__ == "__main__":
    main()

