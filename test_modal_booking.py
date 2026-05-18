import requests
import json

def test_modal_booking():
    session = requests.Session()

    # Login first
    login_data = {'email': 'admin@gmail.com', 'password': 'admin123'}
    response = session.post('http://127.0.0.1:5000/login', data=login_data)
    print(f"Login status: {response.status_code}")

    if response.status_code != 200:
        print("Login failed")
        return

    # Get available slots
    response = session.get('http://127.0.0.1:5000/api/slots')
    print(f"Slots API status: {response.status_code}")

    if response.status_code == 200:
        slots = response.json()
        print(f"Found {len(slots)} slots")

        # Find an available slot
        available_slot = None
        for slot in slots:
            if slot['available']:
                available_slot = slot
                break

        if available_slot:
            print(f"Testing booking for slot: {available_slot['location']}")

            # Test booking with new API format
            booking_data = {
                "slot_id": available_slot['id'],
                "date": "2025-12-31",  # Current date
                "duration": 2,
                "start_time": "14:00",
                "payment_method": "card"
            }

            response = session.post('http://127.0.0.1:5000/api/book',
                                  json=booking_data,
                                  headers={'Content-Type': 'application/json'})

            print(f"Booking response status: {response.status_code}")
            print(f"Booking response: {response.text}")

            if response.status_code == 200:
                result = response.json()
                print(f"✅ Booking successful! ID: {result.get('booking_id', 'N/A')}")
            else:
                print("❌ Booking failed")
        else:
            print("No available slots found")
    else:
        print("Failed to get slots")

if __name__ == "__main__":
    test_modal_booking()