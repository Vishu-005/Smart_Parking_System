from app import app, db, Booking, PlateImage
from datetime import datetime

with app.app_context():
    print("--- Active Bookings ---")
    now = datetime.now()
    bookings = Booking.query.filter(Booking.status == 'active').all()
    for b in bookings:
        print(f"ID: {b.id}, Vehicle: {b.vehicle_number}, Status: {b.status}, End: {b.end_time}")
    
    print("\n--- Recent Plate Images ---")
    plates = PlateImage.query.order_by(PlateImage.created_at.desc()).limit(5).all()
    for p in plates:
        print(f"ID: {p.id}, Text: '{p.plate_text}', Created: {p.created_at}, Notes: {p.notes}")
