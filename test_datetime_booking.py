import requests
import json
from datetime import datetime, timedelta

def test_booking_with_datetime():
    session = requests.Session()

    # Login
    login_data = {'email': 'admin@gmail.com', 'password': 'admin123'}
    response = session.post('http://127.0.0.1:5000/login', data=login_data)
    print('Login status:', response.status_code)

    if response.status_code != 200:
        print("Login failed")
        return

    # Get main page to check modal is present
    response = session.get('http://127.0.0.1:5000/')
    print('Main page status:', response.status_code)
    print('Contains booking modal:', 'bookingModal' in response.text)
    print('Contains date input:', 'booking-date' in response.text)
    print('Contains time select:', 'start-time' in response.text)
    print('Contains duration select:', 'duration' in response.text)

    # Get slots
    response = session.get('http://127.0.0.1:5000/api/slots')
    slots = response.json()
    print(f'Found {len(slots)} slots')

    # Find available slot
    available_slot = None
    for slot in slots:
        if slot['available']:
            available_slot = slot
            break

    if available_slot:
        print(f'Testing booking for slot: {available_slot["location"]}')

        # Create booking for tomorrow at 10 AM for 2 hours
        tomorrow = datetime.now() + timedelta(days=1)
        start = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 10, 0, 0)
        end = start + timedelta(hours=2)

        booking_data = {
            "slot_id": available_slot['id'],
            "start": start.isoformat(),
            "end": end.isoformat()
        }

        print(f'Booking from {start} to {end}')

        response = session.post('http://127.0.0.1:5000/api/book',
                              json=booking_data,
                              headers={'Content-Type': 'application/json'})

        print(f'Booking response status: {response.status_code}')
        print(f'Booking response: {response.text}')

        if response.status_code == 200:
            result = response.json()
            if 'message' in result:
                print('✅ Booking successful!')
            else:
                print('❌ Booking failed with error:', result.get('error', 'Unknown'))
        else:
            print('❌ Booking request failed')
    else:
        print('No available slots found')

if __name__ == "__main__":
    test_booking_with_datetime()