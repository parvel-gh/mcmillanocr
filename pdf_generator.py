"""
PDF Generator with OCR Text Layer

Creates searchable PDFs from screenshots by adding an invisible OCR text layer.
"""
import os
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from datetime import datetime

import config


def setup_tesseract():
    """Configure Tesseract OCR path if specified in config."""
    if config.TESSERACT_PATH:
        pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_PATH


def get_ocr_text(image_path):
    """Extract text from an image using Tesseract OCR."""
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception as e:
        print(f"    OCR warning for {os.path.basename(image_path)}: {e}")
        return ""


def get_ocr_data(image_path):
    """
    Get detailed OCR data including bounding boxes for text positioning.
    Returns a list of dictionaries with text, position, and confidence.
    """
    try:
        img = Image.open(image_path)
        # Get detailed OCR output with bounding boxes
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        
        results = []
        n_boxes = len(data['text'])
        
        for i in range(n_boxes):
            text = data['text'][i].strip()
            conf = int(data['conf'][i])
            
            # Only include text with reasonable confidence
            if text and conf > 30:
                results.append({
                    'text': text,
                    'x': data['left'][i],
                    'y': data['top'][i],
                    'width': data['width'][i],
                    'height': data['height'][i],
                    'conf': conf,
                })
        
        return results
    except Exception as e:
        print(f"    OCR data extraction warning: {e}")
        return []


def create_ocr_pdf(image_paths, output_path, title="E-book Chapter"):
    """
    Create an OCR-enabled PDF from a list of screenshot images.
    
    Uses PyMuPDF's built-in OCR support to create a proper searchable PDF
    with an invisible text layer that can be selected and copied.
    
    Args:
        image_paths: List of paths to screenshot images
        output_path: Path for the output PDF file
        title: Title for the PDF metadata
    """
    setup_tesseract()
    
    print(f"Creating OCR-enabled PDF: {os.path.basename(output_path)}")
    print(f"Processing {len(image_paths)} images...")
    
    # Create new PDF document
    doc = fitz.open()
    
    # Set metadata
    doc.set_metadata({
        "title": title,
        "author": "E-book Scraper",
        "subject": "Scraped e-book chapter",
        "creator": "E-book Chapter Scraper",
        "creationDate": datetime.now().strftime("D:%Y%m%d%H%M%S"),
    })
    
    for idx, image_path in enumerate(image_paths):
        print(f"  [{idx + 1}/{len(image_paths)}] Processing {os.path.basename(image_path)}")
        
        try:
            # Open image to get dimensions
            img = Image.open(image_path)
            img_width, img_height = img.size
            
            # Create a new page with image dimensions
            dpi = config.PDF_SETTINGS.get("dpi", 96)
            width_pt = img_width * 72 / dpi
            height_pt = img_height * 72 / dpi
            
            page = doc.new_page(width=width_pt, height=height_pt)
            
            # Insert the image to fill the page
            rect = fitz.Rect(0, 0, width_pt, height_pt)
            page.insert_image(rect, filename=image_path)
            
            # Get OCR data with positions
            ocr_data = get_ocr_data(image_path)
            
            if ocr_data:
                # Scale factors from image pixels to PDF points
                scale_x = width_pt / img_width
                scale_y = height_pt / img_height
                
                # Add invisible text layer using proper PDF text rendering
                # We'll use render_mode=3 which makes text invisible but selectable
                for item in ocr_data:
                    try:
                        # Calculate position in PDF coordinates
                        x = item['x'] * scale_x
                        y = item['y'] * scale_y
                        h = item['height'] * scale_y
                        
                        # Calculate font size to match the text height
                        font_size = max(6, min(h * 0.9, 14))
                        
                        # Position: y needs adjustment for baseline
                        text_point = fitz.Point(x, y + h * 0.8)
                        
                        # Insert text with render_mode=3 (invisible)
                        page.insert_text(
                            text_point,
                            item['text'],
                            fontsize=font_size,
                            fontname="helv",
                            render_mode=3,  # 3 = invisible (for OCR layer)
                        )
                    except Exception:
                        continue
                
                print(f"    Added {len(ocr_data)} OCR text elements")
            else:
                print(f"    No text detected by OCR")
                
        except Exception as e:
            print(f"    Error processing image: {e}")
            continue
    
    # Save the PDF with text layer
    try:
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        
        file_size = os.path.getsize(output_path)
        print(f"\nPDF saved: {output_path}")
        print(f"File size: {file_size / 1024 / 1024:.2f} MB")
        
        return True
    except Exception as e:
        print(f"Error saving PDF: {e}")
        doc.close()
        return False


def create_simple_pdf(image_paths, output_path, title="E-book Chapter"):
    """
    Create a simple PDF without OCR (faster, for testing).
    
    Args:
        image_paths: List of paths to screenshot images
        output_path: Path for the output PDF file
        title: Title for the PDF metadata
    """
    print(f"Creating simple PDF (no OCR): {os.path.basename(output_path)}")
    print(f"Processing {len(image_paths)} images...")
    
    doc = fitz.open()
    
    doc.set_metadata({
        "title": title,
        "author": "E-book Scraper",
        "creator": "E-book Chapter Scraper",
    })
    
    for idx, image_path in enumerate(image_paths):
        print(f"  [{idx + 1}/{len(image_paths)}] Adding {os.path.basename(image_path)}")
        
        try:
            img = Image.open(image_path)
            img_width, img_height = img.size
            
            dpi = config.PDF_SETTINGS.get("dpi", 96)
            width_pt = img_width * 72 / dpi
            height_pt = img_height * 72 / dpi
            
            page = doc.new_page(width=width_pt, height=height_pt)
            rect = fitz.Rect(0, 0, width_pt, height_pt)
            page.insert_image(rect, filename=image_path)
            
        except Exception as e:
            print(f"    Error: {e}")
            continue
    
    try:
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        print(f"\nPDF saved: {output_path}")
        return True
    except Exception as e:
        print(f"Error saving PDF: {e}")
        doc.close()
        return False


if __name__ == "__main__":
    # Test mode: convert any images in screenshot folder to PDF
    import glob
    
    screenshot_dir = config.SCREENSHOT_FOLDER
    images = sorted(glob.glob(os.path.join(screenshot_dir, "*.png")))
    
    if images:
        print(f"Found {len(images)} screenshots")
        output_file = os.path.join(config.OUTPUT_FOLDER, "test_output.pdf")
        create_ocr_pdf(images, output_file, "Test Chapter")
    else:
        print(f"No PNG images found in {screenshot_dir}")
        print("Run scraper.py first to capture screenshots")

