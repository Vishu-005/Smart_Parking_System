import psycopg2

conn = psycopg2.connect(
    database='parking_db',
    user='postgres',
    password='Vishu005!',
    host='localhost',
    port='5432'
)

cursor = conn.cursor()
cursor.execute('SELECT id, slot_number, slot_type FROM slot ORDER BY slot_number')
rows = cursor.fetchall()

print(f'Slots in database:')
for row in rows:
    print(f'  ID: {row[0]}, Slot: {row[1]}, Type: {row[2]}')

cursor.execute('SELECT COUNT(*) FROM slot')
count = cursor.fetchone()[0]
print(f'\nTotal slots: {count}')

cursor.close()
conn.close()
