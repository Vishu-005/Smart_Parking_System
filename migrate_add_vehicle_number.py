import sqlalchemy as sa
from sqlalchemy import create_engine, text
import os

# Database URI - Update 'your_db_name' with your actual database name
DATABASE_URI = 'postgresql://postgres:Vishu005!@localhost:5432/parking_db'

def add_vehicle_number_column():
    """Add vehicle_number column to booking table if it doesn't exist"""
    try:
        engine = create_engine(DATABASE_URI)
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
            print('✓ Connection to PostgreSQL successful!')
            
            # Check if column already exists
            result = conn.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name='booking' AND column_name='vehicle_number'
            """))
            
            if result.fetchone():
                print('✓ Column vehicle_number already exists in booking table')
                return True
            
            # Add the column
            conn.execute(text('ALTER TABLE booking ADD COLUMN vehicle_number VARCHAR(20)'))
            conn.commit()
            print('✓ vehicle_number column added to booking table successfully!')
            return True
            
    except Exception as e:
        print(f'✗ Migration failed: {e}')
        print('Make sure:')
        print('  1. PostgreSQL is running on localhost:5432')
        print('  2. Username is "postgres"')
        print('  3. Password is "Vishu005!"')
        print('  4. Replace "your_db_name" with your actual database name')
        return False

if __name__ == '__main__':
    print('Starting migration...')
    success = add_vehicle_number_column()
    if not success:
        print('\nPlease fix the configuration and try again.')
    else:
        print('\nMigration complete! You can now run your app.')
