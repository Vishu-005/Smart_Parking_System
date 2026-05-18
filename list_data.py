import os
from app import app, db, Booking, Slot

with app.app_context():
    print("Listing all Bookings:")
    bookings = Booking.query.all()
    if not bookings:
        print("No bookings found in database.")
    for b in bookings:
        print(f"ID: {b.id}, Vehicle: '{b.vehicle_number}', Status: '{b.status}', Date: {b.start_time}")
    
    print("\nListing all Slots:")
    slots = Slot.query.all()
    for s in slots:
        print(f"Slot {s.slot_number}: {s.status}")
