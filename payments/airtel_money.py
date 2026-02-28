import requests
import uuid
import json

class AirtelMoneyService:
    def __init__(self):
        self.client_id = "*****************************"
        self.client_secret = "*****************************"
        self.token_url = "https://openapiuat.airtel.africa/auth/oauth2/token"
        self.collection_payments_url = "https://openapiuat.airtel.africa/merchant/v1/payments/"
        self.collection_refund_url = "https://openapiuat.airtel.africa/standard/v1/payments/refund"
        self.collection_txn_enquiry = "https://openapiuat.airtel.africa/standard/v1/payments/"
        self.country = "ZM"
        self.currency = "ZMW"

    def get_auth_token(self):
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }
        headers = {
            'Content-Type': 'application/json',
            'Accept': '*/*'
        }
        response = requests.post(self.token_url, json=data, headers=headers)
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            return None

    def make_collection_payment(self, access_token, reference, phone_number, amount):
        transaction_id = str(uuid.uuid4())  # Unique transaction ID
        data = {
            "reference": reference,
            "subscriber": {
                "country": self.country,
                "currency": self.currency,
                "msisdn": phone_number
            },
            "transaction": {
                "amount": amount,
                "country": self.country,
                "currency": self.currency,
                "id": transaction_id
            }
        }
        headers = {
            'Content-Type': 'application/json',
            'Accept': '*/*',
            'X-Country': self.country,
            'X-Currency': self.currency,
            'Authorization': f'Bearer {access_token}'
        }
        response = requests.post(self.collection_payments_url, json=data, headers=headers)
        return response.json()

    def check_collection_status(self, access_token, transaction_id):
        url = f'{self.collection_txn_enquiry}{transaction_id}'
        headers = {
            'Content-Type': 'application/json',
            'Accept': '*/*',
            'X-Country': self.country,
            'X-Currency': self.currency,
            'Authorization': f'Bearer {access_token}'
        }
        response = requests.get(url, headers=headers)
        return response.json()
