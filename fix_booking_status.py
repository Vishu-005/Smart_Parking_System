#!/usr/bin/env python
"""
Fix all bookings to have proper status field
"""
from app import app, db, Booking
from sqlalchemy import text

with app.app_context():
    try:
        # Set all NULL status bookings to 'active'
        db.session.execute(text("UPDATE booking SET status = 'active' WHERE status IS NULL"))
        db.session.commit()
        
        # Verify
        bookings = Booking.query.all()
        print(f'✅ Total bookings: {len(bookings)}')
        for b in bookings[:5]:
            print(f'  Booking {b.id}: Slot {b.slot_id}, Status = {b.status}')
        print('✅ All bookings now have proper status!')
    except Exception as e:
        print(f'Error: {e}')
