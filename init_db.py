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
    # Drop the existing User table to recreate with new schema
    cursor.execute("DROP TABLE IF EXISTS \"user\" CASCADE")
    conn.commit()
    print("✅ Dropped old user table")
except Exception as e:
    print(f"❌ Error dropping table: {e}")
    conn.rollback()

try:
    # Create new User table with username and gender columns
    cursor.execute("""
        CREATE TABLE "user" (
            id SERIAL PRIMARY KEY,
            username VARCHAR(150) UNIQUE NOT NULL,
            email VARCHAR(150) UNIQUE NOT NULL,
            password VARCHAR(150) NOT NULL,
            gender VARCHAR(50),
            role VARCHAR(50) NOT NULL
        )
    """)
    conn.commit()
    print("✅ User table created successfully with new schema!")
except Exception as e:
    print(f"❌ Error creating table: {e}")
    conn.rollback()

cursor.close()
conn.close()
