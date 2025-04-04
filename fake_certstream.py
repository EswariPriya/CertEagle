#!/usr/bin/env python3
"""Fake CertStream server generating mock certificate data for testing purposes."""

import asyncio
import websockets
import json
import time
import random
import uuid
import datetime
import os
import sys
import platform
import signal

# Add some domains that will match what's in your domains.yaml
COMMON_DOMAINS = [
    "example.com", "test.com", "fake-domain.org", "mydomain.net", 
    "testsite.io", "sample.co", "mockup.dev", "testing.app",
]

# Occasionally include domains that should match your monitored domains
def get_custom_domains():
    """Load custom domains from domains.yaml if available."""
    try:
        import yaml
        with open(r'C:\Users\Eswari priya\Desktop\CertEagle\CertEagleLocal\domains.yaml', 'r', encoding='utf-8') as f:            
            domain_list = yaml.safe_load(f)
            return [f"{word}-test.com" for word in domain_list.get('domains', [])]
    except (FileNotFoundError, ImportError, AttributeError) as e:
        print(f"Warning: Could not load custom domains - {e}")
        return []

CUSTOM_DOMAINS = get_custom_domains()
TLDS = ["com", "org", "net", "io", "app", "dev", "co", "info", "biz"]

def generate_fake_cert_data():
    """Generate a fake certificate data structure similar to certstream format."""
    # Sometimes use a domain that should trigger a match
    if CUSTOM_DOMAINS and random.random() > 0.7:
        domain = random.choice(CUSTOM_DOMAINS)
    else:
        domain = random.choice(COMMON_DOMAINS)
    
    # Sometimes generate a random subdomain
    if random.random() > 0.5:
        subdomain = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=random.randint(3, 10)))
        domain = f"{subdomain}.{domain}"
    
    # Sometimes generate a completely random domain
    if random.random() > 0.8:
        random_domain = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=random.randint(5, 15)))
        random_tld = random.choice(TLDS)
        domain = f"{random_domain}.{random_tld}"
    
    # Create list of all domains (sometimes with multiple SANs)
    domains = [domain]
    if random.random() > 0.7:
        for _ in range(random.randint(1, 5)):
            alt_domain = f"{''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=random.randint(3, 10)))}.{random.choice(TLDS)}"
            domains.append(alt_domain)
    
    # Generate a fake certificate data structure
    cert_data = {
        "message_type": "certificate_update",
        "data": {
            "update_type": "PrecertLogEntry" if random.random() > 0.5 else "X509LogEntry",
            "leaf_cert": {
                "subject": {
                    "aggregated": f"/CN={domain}"
                },
                "extensions": {
                    "subjectAltName": [f"DNS:{d}" for d in domains]
                },
                "not_before": (datetime.datetime.now() - datetime.timedelta(days=random.randint(1, 30))).isoformat(),
                "not_after": (datetime.datetime.now() + datetime.timedelta(days=random.randint(30, 365))).isoformat(),
                "serial_number": ':'.join([f"{random.randint(0, 255):02x}" for _ in range(8)]),
                "fingerprint": "".join(random.choices("0123456789abcdef", k=40)),
                "as_der": "".join(random.choices("0123456789abcdef", k=160))
            },
            "cert_index": random.randint(100000, 999999),
            "cert_link": f"http://ct.googleapis.com/logs/argon2023/{uuid.uuid4().hex}",
            "seen": time.time()
        }
    }
    
    return cert_data

async def fake_certstream_server(websocket):
    """Send fake certificate data to connected clients."""
    print(f"Client connected from {websocket.remote_address}")
    try:
        while True:
            # Generate a fake cert and send it
            cert_data = generate_fake_cert_data()
            await websocket.send(json.dumps(cert_data))
            
            # Wait a random amount of time before sending the next one
            await asyncio.sleep(random.uniform(0.5, 3.0))
    except websockets.exceptions.ConnectionClosed:
        print(f"Client disconnected from {websocket.remote_address}")

async def main():
    """Start the fake CertStream server."""
    port = int(os.getenv("CERTSTREAM_PORT", 8080))  # Configurable port
    server = await websockets.serve(
        fake_certstream_server, 
        "127.0.0.1", 
        port
    )
    
    print(f"🚀 Fake CertStream server running at ws://127.0.0.1:{port}")
    print("Press Ctrl+C to exit")
    
    # Handle graceful shutdown
    loop = asyncio.get_event_loop()
    stop = loop.create_future()

    # Platform-specific signal handling
    if platform.system() != "Windows":
        # Unix-like systems: use add_signal_handler
        loop.add_signal_handler(signal.SIGINT, stop.set_result, None)
        loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)
    else:
        # Windows: use signal.signal for Ctrl+C
        def stop_loop(signum, frame):
            print("\nReceived shutdown signal")
            stop.set_result(None)
        signal.signal(signal.SIGINT, stop_loop)
        # SIGTERM is not fully supported on Windows, but we can add it for completeness
        signal.signal(signal.SIGTERM, stop_loop if hasattr(signal, 'SIGTERM') else signal.SIGINT)

    await stop
    server.close()
    await server.wait_closed()
    print("\nServer shut down gracefully")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting by user request")