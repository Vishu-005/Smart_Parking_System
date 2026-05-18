
import os
import easyocr
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
from plate_processor import process_image
import logging

# Set up logging for test
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

uploads_dir = "instance/uploads"
# Check if directory exists
if not os.path.exists(uploads_dir):
    print(f"Directory {uploads_dir} does not exist.")
    exit(1)

uploads = sorted([f for f in os.listdir(uploads_dir) if f.endswith(".jpg")])

if not uploads:
    print("No images found in uploads directory.")
    exit(1)

print("Initializing EasyOCR reader...")
reader = easyocr.Reader(['en'], gpu=False)

with open("easyocr_test_results.txt", "w") as f:
    for filename in uploads[-3:]:
        image_path = os.path.join(uploads_dir, filename)
        print(f"Processing: {filename}")
        result = process_image(image_path, reader)
        if result:
            f.write(f"File: {filename}\n")
            f.write(f"Plate Text (Valid Only): {result['plate_text']}\n")
            f.write(f"Raw Cleaned Text: {result['raw_text']}\n")
            f.write(f"Confidence: {result['confidence']:.2f}\n")
            f.write(f"Is Valid Format: {result['is_valid']}\n")
            f.write("-" * 20 + "\n")
        else:
            print(f"Processing failed for {filename}")
print("Test completed. Results saved in easyocr_test_results.txt")
