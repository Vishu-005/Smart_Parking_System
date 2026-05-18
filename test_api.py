import requests

# Test the API endpoint
try:
    response = requests.get('http://127.0.0.1:5000/api/slots')
    if response.status_code == 200:
        data = response.json()
        print("API Response:")
        print(data)
        if len(data) > 0:
            print("\nFirst slot data structure:")
            print(data[0])
    else:
        print(f"API Error: {response.status_code}")
except Exception as e:
    print(f"Connection error: {e}")