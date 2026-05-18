import requests
from datetime import datetime, timedelta

# this script demonstrates the expiry job and can be executed manually
# it assumes the Flask app is running locally on port 5000 and database is reachable

# 1. create a booking that ended a minute ago using the public API (requires login/cookies)
#    for simplicity we directly call the internal job via HTTP after booking

print("✳️ ensure the server is running before executing this test script")

# POST a booking via API could be done if you have an authenticated session,
# but here we rely on the scheduler job already being installed on the server.
#
# After creating a booking in the past, run the job by making a GET request:
#
response = requests.get('http://127.0.0.1:5000/trigger_expiry')
print('trigger expiry endpoint status', response.status_code, response.text)

# then verify the booking status changed by querying /api/my_bookings or directly
# in a real unit test you would access the database model and assert the status.

print("📌 check the server logs for output of the expiry job")
