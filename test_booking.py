import requests
import json

# Test the booking API endpoint
try:
    # First, get available slots
    response = requests.get('http://127.0.0.1:5000/api/slots')
    if response.status_code == 200:
        slots = response.json()
        print("Available slots:")
        for slot in slots:
            if slot['available']:
                print(f"  Slot {slot['id']}: {slot['location']} - ${slot['price_per_hour']}/hour")

        # Test booking the first available slot
        if slots and slots[0]['available']:
            booking_data = {
                "slot_id": slots[0]['id'],
                "date": "2024-01-15",
                "duration": 2,
                "start_time": "10:00",
                "payment_method": "card"
            }

            print(f"\nTesting booking with data: {booking_data}")

            # Note: This will fail because we need authentication, but let's see the response
            book_response = requests.post(
                'http://127.0.0.1:5000/api/book',
                json=booking_data,
                headers={'Content-Type': 'application/json'}
            )

            print(f"Booking response status: {book_response.status_code}")
            print(f"Booking response: {book_response.text}")
        else:
            print("No available slots found")
    else:
        print(f"API Error getting slots: {response.status_code}")

except Exception as e:
    print(f"Connection error: {e}")