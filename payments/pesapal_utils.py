import requests
from django.conf import settings

def get_pesapal_access_token():
    # Prepare the request payload
    payload = {
        'consumer_key': settings.PESAPAL_CONSUMER_KEY,
        'consumer_secret': settings.PESAPAL_CONSUMER_SECRET
    }
    
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    # Make the POST request to get the token
    response = requests.post(settings.PESAPAL_SANDBOX_URL, json=payload, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        return data.get('token'), data.get('expiryDate')  # Return token and expiry time
    else:
        raise Exception(f"Error getting token: {response.text}")