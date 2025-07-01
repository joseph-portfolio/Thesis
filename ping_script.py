import requests
import schedule
import time
import logging

def ping_endpoints():
    endpoints = [
        "https://thesis-g13y.onrender.com/"  # Replace with your actual URLs
    ]
    
    for url in endpoints:
        try:
            response = requests.get(url, timeout=10)
            logging.info(f"Pinged {url}. Status code: {response.status_code}")
        except Exception as e:
            logging.error(f"Error pinging {url}: {e}")

def main():
    logging.basicConfig(level=logging.INFO)
    ping_endpoints()

if __name__ == "__main__":
    main()