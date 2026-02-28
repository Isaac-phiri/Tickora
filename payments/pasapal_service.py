import uuid
import requests
from django.conf import settings

class PesaPalService:
    def __init__(self):
        self.env = settings.PESAPAL_ENV  # 'sandbox' or 'live'
        self.base_url = "https://cybqa.pesapal.com/pesapalv3/api/" #if self.env == "sandbox" else "https://pay.pesapal.com/v3/api/"
        self.consumer_key = settings.PESAPAL_CONSUMER_KEY
        self.consumer_secret = settings.PESAPAL_CONSUMER_SECRET
        self.token = None
    def get_access_token(self, force_refresh=False):
        if self.token and not force_refresh:
            return self.token
            
        url = self.base_url + "Auth/RequestToken"
        headers = {
            "Accept": "application/json", 
            "Content-Type": "application/json"
        }
        data = {
            "consumer_key": self.consumer_key,
            "consumer_secret": self.consumer_secret
        }
        
        try:
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            self.token = response.json().get("token")
            
            if not self.token:
                raise ValueError("No token received from PesaPal")
                
            return self.token
            
        except Exception as e:
            print(f"PesaPal Auth Failed: {str(e)}")
            print(f"Using Key: {self.consumer_key[:5]}...")
            print(f"Using Secret: {self.consumer_secret[:5]}...")
            raise
    
    def register_ipn(self, ipn_url):
        """Register IPN URL with Pesapal"""
        if not self.token:
            self.get_access_token()
            
        url = self.base_url + "URLSetup/RegisterIPN"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        data = {
            "url": ipn_url,
            "ipn_notification_type": "GET"
        }
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()
    
    def get_ipn_list(self):
        try:
            if not self.token:
                self.get_access_token()
                
            url = self.base_url + "URLSetup/GetIpnList"
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers)
            
            # Check for expired token
            if response.status_code == 401:
                self.get_access_token(force_refresh=True)
                headers['Authorization'] = f"Bearer {self.token}"
                response = requests.get(url, headers=headers)
                
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"Failed to get IPN list: {str(e)}")
            return []  # Return empty list instead of failing
            
    def submit_order(self, ticket, callback_url, ipn_id):
        """Submit payment order for a ticket"""
        if not self.token:
            self.get_access_token()
            
        url = self.base_url + "Transactions/SubmitOrderRequest"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        data = {
            "id": ticket.ticket_id,  # Using your ticket's unique ID
            "currency": "ZMW",  # Changed from ZMK to ZMW (Zambian Kwacha)
            "amount": float(ticket.total_price),
            "description": f"Ticket for {ticket.event.event_name} - {ticket.ticket_type}",
            "callback_url": callback_url,
            "redirect_mode": "TOP_WINDOW",
            "notification_id": ipn_id,
            "branch": "Online Ticketing",
            "billing_address": {
                "email_address": ticket.user.email,
                "phone_number": "",  # You might want to add phone to User model
                "country_code": "ZM",
                "first_name": ticket.user.first_name,
                "middle_name": "",
                "last_name": ticket.user.last_name,
                "line_1": "",
                "line_2": "",
                "city": "",
                "state": "",
                "postal_code": "",
                "zip_code": ""
            }
        }
        
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()
    
    def check_payment_status(self, order_tracking_id):
        """Check payment status"""
        if not self.token:
            self.get_access_token()
            
        url = self.base_url + f"Transactions/GetTransactionStatus?orderTrackingId={order_tracking_id}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()