# certstream_monitor.py
import os
import yaml
import json
import time
import requests
import asyncio
import websockets
import random

# Create necessary files and directories if they don't exist
os.makedirs('output', exist_ok=True)
if not os.path.exists('already-seen.log'):
    with open('already-seen.log', 'w') as f:
        f.write('')

# Load domains to monitor
with open('domains.yaml', 'r') as f:
    domain_list = yaml.safe_load(f)

# Load Slack Webhook config
with open('config.yaml', 'r') as f:
    webhook = yaml.safe_load(f)

found_domains_path = 'output/found-domains.log'
already_seen_path = 'already-seen.log'

# Function to send Slack notifications
def slack_notifier(subdomain):
    webhook_url = webhook['SLACK_WEBHOOK']
    slack_data = {
        'username': 'CertEagle-LocalBot',
        'channel': '#subdomain-monitor',
        'text': f"🔴 CertEagle Alert:\n✔️ Detected Domain: {subdomain}"
    }

    response = requests.post(webhook_url, json=slack_data, headers={'Content-Type': 'application/json'})
    print(f"📨 Slack Notification Sent: {subdomain}" if response.status_code == 200 else "⚠️ Failed to send Slack notification")

# Function to check and log matched domains
def parse_results(all_domains_found):
    for subdomain in all_domains_found:
        if any(word in subdomain for word in domain_list['domains']):
            if subdomain.startswith("*"):
                subdomain = subdomain[2:]

            print(f"\u001b[32m[MATCH]\u001b[0m: {subdomain}")

            # Log the matched domain
            with open(found_domains_path, 'a') as f:
                f.write(f"{time.strftime('%Y-%m-%d')} {subdomain}\n")

            # Check if already seen
            with open(already_seen_path, 'r') as f:
                already_seen = f.read().splitlines()

            if subdomain not in already_seen:
                slack_notifier(subdomain)
                with open(already_seen_path, 'a') as f:
                    f.write(subdomain + "\n")

# Function to extract domains from certificate data
async def process_cert_event(cert_data):
    if cert_data.get('message_type') != 'certificate_update':
        return
    
    # Extract all domains from the certificate
    all_domains = []
    
    # Get the main domain from the subject
    leaf_cert = cert_data.get('data', {}).get('leaf_cert', {})
    subject = leaf_cert.get('subject', {}).get('aggregated', '')
    if '/CN=' in subject:
        domain = subject.split('/CN=')[-1]
        all_domains.append(domain)
    
    # Get alternative domain names
    extensions = leaf_cert.get('extensions', {})
    alt_names = extensions.get('subjectAltName', [])
    
    for name in alt_names:
        if name.startswith('DNS:'):
            domain = name[4:]  # Remove 'DNS:' prefix
            all_domains.append(domain)
    
    # Process the domains
    if all_domains:
        parse_results(all_domains)

# Async function to listen to the local CertStream
async def listen_to_certstream():
    print("🚀 Listening for certificate events...")
    
    # Configuration
    max_retries = 5
    retry_count = 0
    base_delay = 2  # Base delay in seconds
    use_fake_server = True  # Set to True to use local fake server
    
    while retry_count < max_retries:
        try:
            # Use the same URL format in both client and server
            url = "ws://127.0.0.1:8080" if use_fake_server else "wss://certstream.calidog.io/"
            
            async with websockets.connect(url) as websocket:
                print(f"Connected to {'fake' if use_fake_server else 'real'} certstream server")
                retry_count = 0  # Reset retry count on successful connection
                
                while True:
                    try:
                        message = await websocket.recv()
                        await process_cert_event(json.loads(message))
                    except websockets.exceptions.ConnectionClosed as e:
                        print(f"Connection closed: {e}")
                        break
                    except json.JSONDecodeError:
                        print("Failed to parse message as JSON")
                        continue
        
        except (websockets.exceptions.ConnectionClosedError, 
                websockets.exceptions.InvalidStatusCode,
                websockets.exceptions.InvalidURI,
                ConnectionRefusedError) as e:
            retry_count += 1
            delay = base_delay * (2 ** (retry_count - 1)) * (0.5 + random.random())  # Exponential backoff with jitter
            
            print(f"Connection error: {e}")
            print(f"Retrying in {delay:.2f} seconds... (Attempt {retry_count}/{max_retries})")
            
            if retry_count == max_retries and not use_fake_server:
                print("Multiple connection failures. Switching to local fake server...")
                use_fake_server = True
                retry_count = 0
                # Make sure fake_certstream.py is running before continuing
                print("Please start fake_certstream.py in another terminal with: python fake_certstream.py")
                time.sleep(5)  # Give user time to start fake server
            elif retry_count == max_retries and use_fake_server:
                print("Failed to connect to both real and fake servers. Exiting.")
                return
            
            time.sleep(delay)

# Make sure necessary files exist before starting
if not os.path.exists('domains.yaml'):
    print("⚠️ domains.yaml not found. Creating a sample file...")
    with open('domains.yaml', 'w') as f:
        f.write("domains:\n  - example\n  - test\n  - yourcompany")
    
if not os.path.exists('config.yaml'):
    print("⚠️ config.yaml not found. Creating a sample file...")
    with open('config.yaml', 'w') as f:
        f.write("SLACK_WEBHOOK: 'https://hooks.slack.com/services/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'")

# Run the main function
if __name__ == "__main__":
    asyncio.run(listen_to_certstream())
