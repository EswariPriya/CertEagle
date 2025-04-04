import json
import time

def process_cert_data(message):
    if message['message_type'] == "certificate_update":
        for domain in message['data']['leaf_cert']['all_domains']:
            print(f"New Certificate Detected: {domain}")

while True:
    fake_cert_data = {
        "message_type": "certificate_update",
        "data": {
            "leaf_cert": {
                "all_domains": ["localhost", "secure.localhost"]
            }
        }
    }
    process_cert_data(fake_cert_data)
    time.sleep(5)

