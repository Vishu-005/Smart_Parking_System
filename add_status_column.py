#!/usr/bin/env python
"""
Script to add the 'status' column to the Booking table if it doesn't exist.
This handles the migration for cancelled booking tracking.
"""

from app import app, db

with app.app_context():
    try:
        # Check if status column exists by trying to query it
        from sqlalchemy import inspect
        from app import Booking
        
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('booking')]
        
        if 'status' in columns:
            print("✅ Status column already exists in booking table")
        else:
            print("Adding 'status' column to booking table...")
            # Add the column with default value
            db.session.execute('ALTER TABLE booking ADD COLUMN status VARCHAR(20) DEFAULT \'active\'')
            db.session.commit()
            print("✅ Status column added successfully!")
            
        # Verify all existing bookings have a status
        bookings = Booking.query.all()
        print(f"Total bookings: {len(bookings)}")
        
        # Set any NULL status values to 'active'
        if bookings:
            for booking in bookings:
                if booking.status is None:
                    booking.status = "active"
            db.session.commit()
            print("✅ All bookings have status set")
            
    except Exception as e:
        print(f"Status: {e}")
        if "already exists" in str(e).lower():
            print("✅ Status column already exists")
        else:
            print(f"Could not add status column: {e}")
            print("\nNote: Make sure PostgreSQL is running and the database connection is valid.")
