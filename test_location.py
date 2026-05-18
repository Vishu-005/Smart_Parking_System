import requests

def test_location_system():
    session = requests.Session()

    # Login
    login_data = {'email': 'admin@gmail.com', 'password': 'admin123'}
    response = session.post('http://127.0.0.1:5000/login', data=login_data)
    print('Login status:', response.status_code)

    if response.status_code != 200:
        print("Login failed")
        return

    # Get main page
    response = session.get('http://127.0.0.1:5000/')
    print('Main page status:', response.status_code)
    print('Contains location detection:', 'Detect My Location' in response.text)
    print('Contains show all slots:', 'Show All Slots' in response.text)
    print('Contains clear location:', 'Clear Location' in response.text)
    print('Contains Book This Slot buttons:', 'Book This Slot' in response.text)

    # Test slots API
    response = session.get('http://127.0.0.1:5000/api/slots')
    print('Slots API status:', response.status_code)
    if response.status_code == 200:
        slots = response.json()
        print(f'Found {len(slots)} slots')
        if slots:
            print(f'First slot: {slots[0]["location"]} - ${slots[0]["price_per_hour"]}/hour')

if __name__ == "__main__":
    test_location_system()