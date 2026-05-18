import os
import sys

# Ensure at the root of project
sys.path.append(os.getcwd())

import sqlite3 # Wait, is it postgres?
from app import app, db, PlateImage

def main():
    with app.app_context():
        plates = PlateImage.query.order_by(PlateImage.id.desc()).limit(15).all()
        with open('plate_output_log.txt', 'w') as f:
            f.write("--- RECENT OCR CAPTURES ---\n")
            for p in plates:
                f.write(f"ID: {p.id}, Text: '{p.plate_text}', Created: {p.created_at}\n")

if __name__ == "__main__":
    main()
