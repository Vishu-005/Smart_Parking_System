
from app import app, db, Booking
with app.app_context():
    bookings = Booking.query.filter_by(status='active').all()
    for b in bookings:
        print(f"Vehicle: {b.vehicle_number}, Status: {b.status}")
