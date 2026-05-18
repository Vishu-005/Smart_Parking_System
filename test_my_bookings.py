import requests
from datetime import datetime, timedelta

def test_my_bookings():
    session = requests.Session()

    # Login as admin
    login_data = {'email': 'admin@gmail.com', 'password': 'admin123'}
    response = session.post('http://127.0.0.1:5000/login', data=login_data)
    print('Login status:', response.status_code)

    if response.status_code != 200:
        print("Login failed")
        return

    # Get my bookings (should be empty initially)
    response = session.get('http://127.0.0.1:5000/api/my_bookings')
    print('My bookings API status:', response.status_code)
    if response.status_code == 200:
        bookings = response.json()
        print(f'Initial bookings count: {len(bookings)}')

    # Get available slots
    response = session.get('http://127.0.0.1:5000/api/slots')
    print('Slots API status:', response.status_code)
    if response.status_code == 200:
        slots = response.json()
        available_slots = [s for s in slots if s['available']]
        if available_slots:
            slot_id = available_slots[0]['id']
            print(f'Booking slot {slot_id}')

            # Book a slot
            start_time = datetime.now() + timedelta(hours=1)
            end_time = start_time + timedelta(hours=2)
            booking_data = {
                'slot_id': slot_id,
                'start': start_time.isoformat(),
                'end': end_time.isoformat()
            }
            response = session.post('http://127.0.0.1:5000/api/book', json=booking_data)
            print('Booking status:', response.status_code)
            if response.status_code == 200:
                print('Booking successful')

                # Check my bookings again
                response = session.get('http://127.0.0.1:5000/api/my_bookings')
                print('My bookings API status after booking:', response.status_code)
                if response.status_code == 200:
                    bookings = response.json()
                    print(f'Bookings count after booking: {len(bookings)}')
                    if bookings:
                        print(f'Booking details: {bookings[0]}')
            else:
                print('Booking failed:', response.json())
        else:
            print('No available slots')

if __name__ == "__main__":
    test_my_bookings()