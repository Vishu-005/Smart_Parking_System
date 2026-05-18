import psycopg2

conn = psycopg2.connect(
    database='parking_db',
    user='postgres',
    password='Vishu005!',
    host='localhost',
    port='5432'
)

cursor = conn.cursor()

# Insert remaining slots (5-10)
slots_to_add = [
    (5, "smart_parking_slot_5", 4.5, "empty", 17.6875, 83.2175, "regular"),
    (6, "smart_parking_slot_6", 8.0, "empty", 17.6865, 83.2180, "ev"),
    (7, "smart_parking_slot_7", 4.5, "empty", 17.6872, 83.2188, "regular"),
    (8, "smart_parking_slot_8", 8.0, "empty", 17.6860, 83.2192, "ev"),
    (9, "smart_parking_slot_9", 4.5, "empty", 17.6878, 83.2182, "regular"),
    (10, "smart_parking_slot_10", 8.0, "empty", 17.6863, 83.2186, "ev"),
]

try:
    for slot in slots_to_add:
        cursor.execute("""
            INSERT INTO slot (slot_number, location, price_per_hour, status, latitude, longitude, slot_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, slot)
    
    conn.commit()
    print("✅ Successfully added 6 new slots (5-10)")
    
    # Verify
    cursor.execute('SELECT COUNT(*) FROM slot')
    count = cursor.fetchone()[0]
    print(f"Total slots now: {count}")
    
    cursor.execute('SELECT id, slot_number, slot_type FROM slot ORDER BY slot_number')
    rows = cursor.fetchall()
    print("\nAll slots:")
    for row in rows:
        print(f'  Slot {row[1]}: {row[2]}')
    
except Exception as e:
    print(f"❌ Error: {e}")
    conn.rollback()

cursor.close()
conn.close()
