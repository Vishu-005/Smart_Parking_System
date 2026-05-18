import psycopg2
from psycopg2 import sql

# Connect directly to PostgreSQL
conn = psycopg2.connect(
    database="parking_db",
    user="postgres",
    password="Vishu005!",
    host="localhost",
    port="5432"
)

cursor = conn.cursor()

try:
    # Add the slot_type column if it doesn't exist
    cursor.execute("""
        ALTER TABLE slot 
        ADD COLUMN slot_type VARCHAR(50) DEFAULT 'regular'
    """)
    conn.commit()
    print("✅ Column slot_type added successfully!")
except psycopg2.errors.DuplicateColumn:
    print("✅ Column slot_type already exists")
    conn.rollback()
except Exception as e:
    print(f"❌ Error: {e}")
    conn.rollback()

try:
    # Update slot types based on slot_number
    cursor.execute("""
        UPDATE slot SET slot_type = 'handicapped' 
        WHERE slot_number IN (1, 2, 3)
    """)
    
    cursor.execute("""
        UPDATE slot SET slot_type = 'ev' 
        WHERE slot_number IN (6, 8, 10)
    """)
    
    cursor.execute("""
        UPDATE slot SET slot_type = 'regular' 
        WHERE slot_type IS NULL OR slot_type = ''
    """)
    
    conn.commit()
    print("✅ Slot types updated successfully!")
    
    # Show updated slots
    cursor.execute("SELECT slot_number, slot_type FROM slot ORDER BY slot_number")
    rows = cursor.fetchall()
    print("\nUpdated slots:")
    for row in rows:
        print(f"  Slot {row[0]}: {row[1]}")
    
except Exception as e:
    print(f"❌ Update error: {e}")
    conn.rollback()

cursor.close()
conn.close()
