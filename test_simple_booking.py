import requests
import json

def test_booking():
    session = requests.Session()

    # Login
    login_data = {'email': 'admin@gmail.com', 'password': 'admin123'}
    response = session.post('http://127.0.0.1:5000/login', data=login_data)
    print('Login status:', response.status_code)

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

        # Create booking data
        import datetime
        now = datetime.datetime.now()
        start = now.isoformat()
        end = (now + datetime.timedelta(hours=1)).isoformat()

        booking_data = {
            "slot_id": available_slot['id'],
            "start": start,
            "end": end
        }

        response = session.post('http://127.0.0.1:5000/api/book',
                              json=booking_data,
                              headers={'Content-Type': 'application/json'})

        print(f'Booking response status: {response.status_code}')
        print(f'Booking response: {response.text}')

        if response.status_code == 200:
            print('✅ Booking successful!')
        else:
            print('❌ Booking failed')
    else:
        print('No available slots found')

if __name__ == "__main__":
    test_booking()