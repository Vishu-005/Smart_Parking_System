from app import app, db
from sqlalchemy import text

with app.app_context():
    try:
        # Try to add the column if it doesn't exist
        with db.engine.connect() as connection:
            connection.execute(text("ALTER TABLE slot ADD COLUMN slot_type VARCHAR(50) DEFAULT 'regular'"))
            connection.commit()
        print("✅ Column slot_type added successfully!")
    except Exception as e:
        if 'already exists' in str(e):
            print("✅ Column slot_type already exists")
        else:
            print(f"Error: {e}")
    
    # Update slot types and prices for 6 slots
    try:
        with db.engine.connect() as connection:
            # Initialize all slots as "available" by default
            connection.execute(text("UPDATE slot SET status = 'available'"))
            
            # Set slot types for slots 1-6
            connection.execute(text("UPDATE slot SET slot_type = 'handicapped' WHERE slot_number IN (1, 2)"))
            connection.execute(text("UPDATE slot SET slot_type = 'regular' WHERE slot_number IN (3, 4)"))
            connection.execute(text("UPDATE slot SET slot_type = 'ev' WHERE slot_number IN (5, 6)"))
            
            # Set prices for each slot type
            connection.execute(text("UPDATE slot SET price_per_hour = 4.5 WHERE slot_type = 'handicapped'"))
            connection.execute(text("UPDATE slot SET price_per_hour = 4.5 WHERE slot_type = 'regular'"))
            connection.execute(text("UPDATE slot SET price_per_hour = 8.0 WHERE slot_type = 'ev'"))
            
            # Delete slots beyond slot 6
            connection.execute(text("DELETE FROM booking WHERE slot_id IN (SELECT id FROM slot WHERE slot_number > 6)"))
            connection.execute(text("DELETE FROM slot WHERE slot_number > 6"))
            
            connection.commit()
        print("✅ Slot types and prices updated successfully!")
        print("   - Slots 1-2: Handicapped ($4.5/hour)")
        print("   - Slots 3-4: Regular ($4.5/hour)")
        print("   - Slots 5-6: EV ($8/hour)")
    except Exception as e:
        print(f"Update error: {e}")

