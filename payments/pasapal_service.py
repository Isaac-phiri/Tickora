import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

ipn_id = settings.PESAPAL_IPN_ID
callback_url = settings.PESAPAL_CALLBACK_URL

class PesaPalService:
    def __init__(self):
        self.env = settings.PESAPAL_ENV  # 'sandbox' or 'live'
        # Use sandbox URL for testing, live URL for production
        if self.env == "sandbox":
            self.base_url = "https://cybqa.pesapal.com/pesapalv3/api/"
        else:
            self.base_url = "https://pay.pesapal.com/v3/api/"
            
        self.consumer_key = settings.PESAPAL_CONSUMER_KEY
        self.consumer_secret = settings.PESAPAL_CONSUMER_SECRET
        self.token = None
        
    def get_access_token(self, force_refresh=False):
        """Get access token from PesaPal"""
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
        print("\n========== TOKEN REQUEST ==========")
        print("URL:", url)
        print("Payload:", data)
        
        try:
            logger.info(f"Requesting token from {url}")
            response = requests.post(url, json=data, headers=headers)

            print("Status Code:", response.status_code)
            print("Response Text:", response.text)

            response.raise_for_status()
            result = response.json()
            self.token = result.get("token")

            print("Extracted Token:", self.token)
            print("===================================\n")
            
            if not self.token:
                raise ValueError("No token received from PesaPal")
                
            logger.info("Successfully obtained PesaPal token")
            return self.token
            
        except Exception as e:
            logger.error(f"PesaPal Auth Failed: {str(e)}")
            logger.error(f"Using Key: {self.consumer_key[:5]}...")
            logger.error(f"Using Secret: {self.consumer_secret[:5]}...")
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
        print("\n========== REGISTER IPN ==========")
        print("IPN URL:", ipn_url)
        
        logger.info(f"Registering IPN: {ipn_url}")
        response = requests.post(url, json=data, headers=headers)

        print("Status Code:", response.status_code)
        print("Response Text:", response.text)
        print("==================================\n")

        response.raise_for_status()
        return response.json()
    
    def get_ipn_list(self):
        """Get list of registered IPNs"""
        try:
            if not self.token:
                self.get_access_token()
                
            url = self.base_url + "URLSetup/GetIpnList"
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            
            logger.info("Getting IPN list")
            response = requests.get(url, headers=headers)

            print("Status Code:", response.status_code)
            print("Response Text:", response.text)
            print("==================================\n")
            
            # Check for expired token
            if response.status_code == 401:
                logger.info("Token expired, refreshing...")
                self.get_access_token(force_refresh=True)
                headers['Authorization'] = f"Bearer {self.token}"
                response = requests.get(url, headers=headers)
                
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to get IPN list: {str(e)}")
            return []  # Return empty list instead of failing
            
    def submit_order(self, order, ipn_id=None, callback_url=None):
        """Submit payment order to PesaPal"""
        if not self.token:
            self.get_access_token()
            
        url = self.base_url + "Transactions/SubmitOrderRequest"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        # Get first order item for description
        order_item = order.order_items.first()
        ticket_type = order_item.ticket_type if order_item else None
        
        # Use order.id as merchant reference
        merchant_reference = str(order.id)
        
        # Get customer names
        first_name = order.user.first_name or "Customer"
        last_name = order.user.last_name or ""
        
        data = {
            "id": merchant_reference,  # Using order ID as merchant reference
            "currency": "ZMW",
            "amount": float(order.total_amount),
            "description": f"Ticket for {order.event.title} - {ticket_type.name if ticket_type else 'Event'}",
            "callback_url": callback_url,
            "redirect_mode": "TOP_WINDOW",
            "notification_id": ipn_id,
            "branch": "Online Ticketing",
            "billing_address": {
                "email_address": order.user.email,
                "phone_number": order.phone_number or "",
                "country_code": "ZM",
                "first_name": first_name,
                "last_name": last_name,
            }
        }
        
        print("\n========== SUBMIT ORDER ==========")
        print("Payload:", data)

        logger.info(f"Submitting order to PesaPal: {merchant_reference}")
        response = requests.post(url, json=data, headers=headers)

        print("Status Code:", response.status_code)
        print("Response Text:", response.text)
        print("==================================\n")

        response.raise_for_status()
        result = response.json()
        logger.info(f"PesaPal order submission response: {result}")
        return result
    
    def check_payment_status(self, order_tracking_id):
        """Check payment status from PesaPal"""
        if not self.token:
            self.get_access_token()
            
        url = self.base_url + f"Transactions/GetTransactionStatus?orderTrackingId={order_tracking_id}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        print("\n========== CHECK STATUS ==========")
        print("Tracking ID:", order_tracking_id)
        
        logger.info(f"Checking payment status for: {order_tracking_id}")
        response = requests.get(url, headers=headers)

        print("Status Code:", response.status_code)
        print("Response Text:", response.text)
        print("==================================\n")   

        response.raise_for_status()
        return response.json()



# import uuid
# import requests
# from django.conf import settings

# class PesaPalService:
#     def __init__(self):
#         self.env = settings.PESAPAL_ENV  # 'sandbox' or 'live'
#         self.base_url = "https://cybqa.pesapal.com/pesapalv3/api/" #if self.env == "sandbox" else "https://pay.pesapal.com/v3/api/"
#         self.consumer_key = settings.PESAPAL_CONSUMER_KEY
#         self.consumer_secret = settings.PESAPAL_CONSUMER_SECRET
#         self.token = None
#     def get_access_token(self, force_refresh=False):
#         if self.token and not force_refresh:
#             return self.token
            
#         url = self.base_url + "Auth/RequestToken"
#         headers = {
#             "Accept": "application/json", 
#             "Content-Type": "application/json"
#         }
#         data = {
#             "consumer_key": self.consumer_key,
#             "consumer_secret": self.consumer_secret
#         }
        
#         try:
#             response = requests.post(url, json=data, headers=headers)
#             response.raise_for_status()
#             self.token = response.json().get("token")
            
#             if not self.token:
#                 raise ValueError("No token received from PesaPal")
                
#             return self.token
            
#         except Exception as e:
#             print(f"PesaPal Auth Failed: {str(e)}")
#             print(f"Using Key: {self.consumer_key[:5]}...")
#             print(f"Using Secret: {self.consumer_secret[:5]}...")
#             raise
    
#     def register_ipn(self, ipn_url):
#         """Register IPN URL with Pesapal"""
#         if not self.token:
#             self.get_access_token()
            
#         url = self.base_url + "URLSetup/RegisterIPN"
#         headers = {
#             "Authorization": f"Bearer {self.token}",
#             "Content-Type": "application/json"
#         }
#         data = {
#             "url": ipn_url,
#             "ipn_notification_type": "GET"
#         }
#         response = requests.post(url, json=data, headers=headers)
#         response.raise_for_status()
#         return response.json()
    
#     def get_ipn_list(self):
#         try:
#             if not self.token:
#                 self.get_access_token()
                
#             url = self.base_url + "URLSetup/GetIpnList"
#             headers = {
#                 "Authorization": f"Bearer {self.token}",
#                 "Content-Type": "application/json"
#             }
            
#             response = requests.get(url, headers=headers)
            
#             # Check for expired token
#             if response.status_code == 401:
#                 self.get_access_token(force_refresh=True)
#                 headers['Authorization'] = f"Bearer {self.token}"
#                 response = requests.get(url, headers=headers)
                
#             response.raise_for_status()
#             return response.json()
            
#         except Exception as e:
#             print(f"Failed to get IPN list: {str(e)}")
#             return []  # Return empty list instead of failing
            
#     def submit_order(self, order, callback_url, ipn_id):
#         """Submit payment order for a ticket"""
#         if not self.token:
#             self.get_access_token()
            
#         url = self.base_url + "Transactions/SubmitOrderRequest"
#         headers = {
#             "Authorization": f"Bearer {self.token}",
#             "Accept": "application/json",
#             "Content-Type": "application/json"
#         }

#         data = {
#             "id": order.ticket_id,  # Using your ticket's unique ID
#             "currency": "ZMW",  # Changed from ZMK to ZMW (Zambian Kwacha)
#             "amount": float(order.total_price),
#             "description": f"Ticket for {order.event.event_name} - {order.ticket_type}",
#             "callback_url": callback_url,
#             "redirect_mode": "TOP_WINDOW",
#             "notification_id": ipn_id,
#             "branch": "Online Ticketing",
#             "billing_address": {
#                 "email_address": order.user.email,
#                 "phone_number": "",  # You might want to add phone to User model
#                 "country_code": "ZM",
#                 "first_name": order.user.first_name,
#                 "middle_name": "",
#                 "last_name": order.user.last_name,
#                 "line_1": "",
#                 "line_2": "",
#                 "city": "",
#                 "state": "",
#                 "postal_code": "",
#                 "zip_code": ""
#             }
#         }
        
#         response = requests.post(url, json=data, headers=headers)
#         response.raise_for_status()
#         return response.json()
    
#     def check_payment_status(self, order_tracking_id):
#         """Check payment status"""
#         if not self.token:
#             self.get_access_token()
            
#         url = self.base_url + f"Transactions/GetTransactionStatus?orderTrackingId={order_tracking_id}"
#         headers = {
#             "Authorization": f"Bearer {self.token}",
#             "Content-Type": "application/json"
#         }
#         response = requests.get(url, headers=headers)
#         response.raise_for_status()
#         return response.json()