import requests
import time
import random
from datetime import datetime
import json

# Configuration
URLS = [
    'https://umbrella-free-pdf.onrender.com',
    'https://umbrella-free-pdf.onrender.com/api/health',
    'https://umbrella-free-pdf.onrender.com/status'
]

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15'
]

def simulate_request(url, delay=0):
    time.sleep(delay)
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
        'Cache-Control': 'no-cache'
    }
    
    try:
        print(f"🌐 [{datetime.now().isoformat()}] Pinging: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        print(f"✅ Status: {response.status_code} | Size: {len(response.content)} bytes")
        return response.status_code
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

def simulate_traffic():
    print(f"\n🚀 Starting keep-alive simulation at {datetime.now().isoformat()}\n")
    print(f"📊 Will ping {len(URLS)} URLs\n")
    
    for i, url in enumerate(URLS):
        simulate_request(url, delay=i*2)
    
    print(f"\n✅ Session completed at {datetime.now().isoformat()}\n")
    print('─' * 60)

if __name__ == "__main__":
    simulate_traffic()
