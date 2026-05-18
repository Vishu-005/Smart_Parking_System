from app import app, db, PlateImage
import logging

with app.app_context():
    plates = PlateImage.query.order_by(PlateImage.id.desc()).limit(15).all()
    print("--- RECENT OCR CAPTURES ---")
    for p in plates:
        print(f"ID: {p.id}, Text: '{p.plate_text}', Created: {p.created_at}")
