from app import app, db, Booking

with app.app_context():
    with open('bookings_dump.txt', 'w') as f:
        bookings = Booking.query.filter_by(status='active').all()
        for b in bookings:
            f.write(f"V: {b.vehicle_number}, Start: {b.start_time}\n")
