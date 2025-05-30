import requests
import json

# Replace with your actual Tracktry API key
api_key = "wfarfffa-zr6k-gw28-fy73-ulmazt5mo3j7"

# Replace with the actual JT Express tracking number
tracking_number = "1234567890"

# Use the appropriate carrier code for JT Express (e.g., "jtexpress" or "jt-express-th")
carrier_code = "jtexpress"

# API endpoint for real-time tracking
url = "https://api.trackingmore.com/v4/trackings/create"

# Set the headers with the API key
headers = {
    "Content-Type": "application/json",
    "Tracking-Api-Key": api_key
}

# Prepare the request data 
data = {
    "tracking_number": tracking_number,
    "courier_code": carrier_code
}

# Send the POST request
response = requests.post(url, headers=headers, json=data)

# Check if the request was successful
if response.status_code == 200:
    # Print the tracking information
    print(json.dumps(response.json(), indent=4))
else:
    # Handle errors
    print(f"Error: {response.status_code}, {response.text}")