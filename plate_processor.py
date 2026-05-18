
import os
import cv2
import numpy as np
import logging
import re

# Set up logging for OCR process
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_image(input_path, reader, output_dir='static/processed'):
    """
    EasyOCR Extraction Pipeline:
    1. Load image
    2. Resize 2x (Cubic)
    3. Grayscale
    4. Gaussian Blur
    5. Adaptive Thresholding
    6. Center Crop
    7. EasyOCR Reader
    8. Cleaning & Validation
    """
    logger.info(f"🔍 EasyOCR Processing: {input_path}")
    
    # 1. Load image
    img = cv2.imread(input_path)
    if img is None:
        logger.error(f"Could not read image: {input_path}")
        return None
    
    # 2. Resize 2x using cubic interpolation
    height, width = img.shape[:2]
    resized = cv2.resize(img, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC)
    
    # 3. Convert to grayscale
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    
    # 4. Enhance contrast for handwriting on paper
    # Use CLAHE to even out lighting on the paper
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)
    
    # 5. Use Otsu's thresholding instead of Adaptive for handwriting
    # Handwriting on paper can be sensitive to adaptive block size
    # We'll also try a simpler blurred grayscale for EasyOCR as it handles raw well
    _, thresholded = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 6. Save a less aggressive crop for better detection
    h, w = thresholded.shape
    cropped = thresholded[int(h*0.05):int(h*0.95), int(w*0.05):int(w*0.95)]
    
    # Save processed image for dashboard visibility
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.basename(input_path)
    processed_filename = f"processed_{filename}"
    processed_path = os.path.join(output_dir, processed_filename)
    cv2.imwrite(processed_path, cropped)
    logger.info(f"processed image saved for handwriting: {processed_path}")
    
    # 7. Run EasyOCR
    try:
        # EasyOCR often performs better on grayscale/original than binary for handwriting
        # We pass the enhanced (non-binary) image to EasyOCR
        final_input = enhanced[int(h*0.05):int(h*0.95), int(w*0.05):int(w*0.95)]
        results = reader.readtext(final_input)
        logger.info(f"EasyOCR detection count: {len(results)}")
        
        # Sort results: top-to-bottom, then left-to-right
        # res[0] is the box [[x,y], [x,y], [x,y], [x,y]]
        # Sort by y-coordinate of top-left corner primarily
        results.sort(key=lambda x: (x[0][0][1], x[0][0][0]))
        
        combined_raw = "".join([res[1] for res in results]).upper()
        cleaned_raw = re.sub(r'[^A-Z0-9]', '', combined_raw)
        logger.info(f"Reconstructed string from handwriting: {cleaned_raw}")
        
        # Pattern Matcher (Strict 10 characters)
        def fix_plate_format(text):
            if len(text) < 10: return None
            
            # Correction maps for handwritten ambiguity
            to_digit = {'O': '0', 'D': '0', 'Q': '0', 'I': '1', 'L': '1', 'S': '5', 'B': '8', 'G': '6', 'Z': '2'}
            to_alpha = {'0': 'D', '1': 'I', '8': 'B', '5': 'S', '2': 'Z', '4': 'A', '6': 'G'}
            
            # Sliding window of 10 chars
            for i in range(len(text) - 9):
                candidate = list(text[i:i+10])
                
                # Format: LL DD LL DDDD
                try:
                    # Fix Alphas (0,1,4,5)
                    for j in [0, 1, 4, 5]:
                        if candidate[j] in to_alpha: candidate[j] = to_alpha[candidate[j]]
                    
                    # Fix Digits (2,3,6,7,8,9)
                    for j in [2, 3, 6, 7, 8, 9]:
                        if candidate[j] in to_digit: candidate[j] = to_digit[candidate[j]]
                    
                    candidate_str = "".join(candidate)
                    if re.match(r'^[A-Z]{2}[0-9]{2}[A-Z]{2}[0-9]{4}$', candidate_str):
                        return candidate_str
                except Exception: continue
            return None

        final_plate = fix_plate_format(cleaned_raw)
        
        # CLEANUP: Ensure NO numpy types (np.float32, np.int64) return to Flask/DB
        # easyocr confidence is often np.float32 which crashes psycopg2
        avg_conf = 0.0
        if results:
            total_conf = 0.0
            for res in results:
                total_conf += float(res[2])
            avg_conf = total_conf / len(results)
            
        return {
            'original_path': input_path,
            'processed_path': processed_path,
            'plate_text': str(final_plate) if final_plate else "",
            'raw_text': str(cleaned_raw),
            'confidence': float(avg_conf),
            'is_valid': bool(final_plate),
            'notes': "EasyOCR optimized for Handwriting"
        }
    except Exception as e:
        logger.error(f"Handwriting OCR Error: {e}")
        return None

def process_mobile_capture(input_path, reader, output_dir='static/processed'):
    # Point to the unified direct processing method
    return process_image(input_path, reader, output_dir)

if __name__ == '__main__':
    # For testing if run directly
    import sys
    import easyocr
    if len(sys.argv) > 1:
        test_reader = easyocr.Reader(['en'], gpu=False)
        print(process_image(sys.argv[1], test_reader))
    else:
        print("Usage: python plate_processor.py <image_path>")
