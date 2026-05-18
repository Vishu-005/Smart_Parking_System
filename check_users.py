import psycopg2

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
    # Check all users in the database
    cursor.execute('SELECT id, username, email FROM "user"')
    users = cursor.fetchall()
    
    if users:
        print("✅ Users in database:")
        for user in users:
            print(f"   ID: {user[0]}, Username: {user[1]}, Email: {user[2]}")
    else:
        print("❌ No users found in database")
        
except Exception as e:
    print(f"❌ Error: {e}")

cursor.close()
conn.close()
