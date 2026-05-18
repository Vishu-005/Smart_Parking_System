import psycopg2
from werkzeug.security import generate_password_hash

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
    # Check if admin already exists
    cursor.execute('SELECT * FROM "user" WHERE email = %s', ("admin01@gmail.com",))
    if cursor.fetchone():
        print("✅ Admin account already exists")
    else:
        # Create admin user
        hashed_password = generate_password_hash("Vishu005!", method="pbkdf2:sha256")
        cursor.execute(
            'INSERT INTO "user" (username, email, password, gender, role) VALUES (%s, %s, %s, %s, %s)',
            ("admin01", "admin01@gmail.com", hashed_password, "male", "admin")
        )
        conn.commit()
        print("✅ Admin account created successfully!")
        print("   Email: admin01@gmail.com")
        print("   Password: Vishu005!")
        print("   Role: admin")
except Exception as e:
    print(f"❌ Error: {e}")
    conn.rollback()

cursor.close()
conn.close()
