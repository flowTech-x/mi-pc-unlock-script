import subprocess
import sys
import os
import platform
import random
import argparse

# Server lists
ntp_servers = [
    "ntp0.ntp-servers.net", "ntp1.ntp-servers.net", "ntp2.ntp-servers.net",
    "ntp3.ntp-servers.net", "ntp4.ntp-servers.net", "ntp5.ntp-servers.net",
    "ntp6.ntp-servers.net"
]

# Parse command line arguments
parser = argparse.ArgumentParser(description='Xiaomi Bootloader Unlock Script - FIXED')
parser.add_argument('--test', action='store_true', help='Test mode: Send requests NOW (no waiting)')
parser.add_argument('--token', type=int, help='Token line number')
args = parser.parse_args()

# Dependency installation
def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

required_packages = ["ntplib", "pytz", "urllib3", "icmplib", "colorama", "linecache"]
for package in required_packages:
    try:
        __import__(package)
    except ImportError:
        print(f"Installing package {package}...")
        install_package(package)

os.system('cls' if os.name == 'nt' else 'clear')

import hashlib
import linecache
import time
from datetime import datetime, timezone, timedelta
import ntplib
import pytz
import urllib3
import json
from icmplib import ping
from colorama import init, Fore, Style

# Color configuration
init(autoreset=True)
col_g = Fore.GREEN
col_gb = Style.BRIGHT + Fore.GREEN
col_b = Fore.BLUE
col_bb = Style.BRIGHT + Fore.BLUE
col_y = Fore.YELLOW
col_yb = Style.BRIGHT + Fore.YELLOW
col_r = Fore.RED
col_rb = Style.BRIGHT + Fore.RED

scriptversion = "flow-fixed-v2-9:30PM"

# Token input
if args.token:
    token_number = args.token
else:
    token_number = int(input(col_g + "[Token line number]: " + Fore.RESET))

os.system('cls' if os.name == 'nt' else 'clear')

print(col_yb + f"{scriptversion}_token_#{token_number}:")
if args.test:
    print(col_yb + "[TEST MODE ACTIVE - SENDS NOW]" + Fore.RESET)
print(col_y + "Checking account status..." + Fore.RESET)

def load_token_feed(token_num):
    token = linecache.getline("token.txt", token_num).strip()
    try:
        feedtime = float(linecache.getline("timeshift.txt", token_num).strip())
    except:
        feedtime = 0.0
    return token, feedtime / 1000  # Convert ms to seconds

token, feed_time_shift = load_token_feed(token_number)

# User agents for rotation
user_agents = [
    'okhttp/4.12.0',
    'okhttp/4.11.0 (Linux; Android 14)',
    'Dalvik/2.1.0 (Linux; U; Android 14)'
]

def generate_device_id():
    random_data = f"{random.random()}-{time.time()}-{random.randint(1,10000)}"
    return hashlib.sha1(random_data.encode('utf-8')).hexdigest().upper()

def get_initial_beijing_time():
    client = ntplib.NTPClient()
    beijing_tz = pytz.timezone("Asia/Shanghai")
    for server in ntp_servers:
        try:
            print(col_y + "\nGetting Beijing time from NTP..." + Fore.RESET)
            response = client.request(server, version=3)
            ntp_time = datetime.fromtimestamp(response.tx_time, timezone.utc)
            beijing_time = ntp_time.astimezone(beijing_tz)
            print(col_gb + "[Beijing time]: " + Fore.RESET + f"{beijing_time.strftime('%Y-%m-%d %H:%M:%S.%f')}")
            return beijing_time
        except Exception as e:
            print(col_y + f"Failed {server}: {e}" + Fore.RESET)
    print(col_rb + "❌ NO NTP servers available!" + Fore.RESET)
    return None

def get_synchronized_beijing_time(start_beijing_time, start_timestamp):
    elapsed = time.time() - start_timestamp
    return start_beijing_time + timedelta(seconds=elapsed)

def wait_until_target_window(start_beijing_time, start_timestamp):
    next_day = start_beijing_time + timedelta(days=1)
    print(col_y + "\n🎯 Targeting EXACT China 00:00:00 (India 9:30 PM IST)" + Fore.RESET)
    print(col_gb + "[Offset]: " + Fore.RESET + f"{feed_time_shift*1000:.0f}ms from timeshift.txt")
    
    # FIXED: EXACT 9:30PM IST = China 00:00 minus ONLY feed_time_shift (NO +5 buffer)
    target_window_start = next_day.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(seconds=feed_time_shift)
    print(col_gb + "[FLOOD STARTS]: " + Fore.RESET + f"{target_window_start.strftime('%Y-%m-%d %H:%M:%S.%f')} Beijing")
    print(col_yb + "⏳ Waiting... Do NOT close window!" + Fore.RESET)
    
    while True:
        current_time = get_synchronized_beijing_time(start_beijing_time, start_timestamp)
        time_diff = target_window_start - current_time
        
        if time_diff.total_seconds() > 1:
            time.sleep(min(0.1, time_diff.total_seconds() - 0.9))  # Tighter polling
        elif current_time >= target_window_start:
            print(col_gb + "🚀 FLOOD WINDOW OPEN - BURSTING..." + Fore.RESET)
            return current_time
        else:
            time.sleep(0.001)  # 1ms tight loop

def print_full_response(response_data, request_time):
    print(col_g + f"[📡 REQ {request_time.strftime('%H:%M:%S.%f')}]" + Fore.RESET)
    try:
        print(col_g + "[FULL RESPONSE]:" + Fore.RESET)
        print(json.dumps(response_data, indent=2, ensure_ascii=False))
        return response_data
    except:
        print(col_g + f"[RAW]: {response_data}" + Fore.RESET)
        return response_data

def check_unlock_status(session, cookie_value, device_id):
    url = "https://sgp-api.buy.mi.com/bbs/api/global/user/bl-switch/state"
    headers = {
        "Cookie": f"new_bbs_serviceToken={cookie_value};versionCode=500411;versionName=5.4.11;deviceId={device_id};"
    }
    
    try:
        response = session.make_request('GET', url, headers=headers)
        if response is None:
            print(col_r + "❌ Network error - status unavailable" + Fore.RESET)
            return False

        response_data = json.loads(response.data.decode('utf-8'))
        response.release_conn()

        if response_data.get("code") == 100004:
            print(col_rb + "❌ COOKIE EXPIRED - STOPPING (NO LOOP)" + Fore.RESET)
            return False  # FIXED: NO infinite loop on expiry

        data = response_data.get("data", {})
        is_pass = data.get("is_pass")
        button_state = data.get("button_state")

        print(col_g + f"[Account]: is_pass={is_pass}, button_state={button_state}" + Fore.RESET)
        print(col_g + "[FULL STATUS]:" + Fore.RESET)
        print(json.dumps(response_data, indent=2))

        if is_pass == 4 and button_state in [1, 2, 3]:
            print(col_gb + "✅ READY TO SEND REQUESTS!" + Fore.RESET)
            return True
        
        print(col_r + "❌ Account not ready - exiting" + Fore.RESET)
        return False
        
    except Exception as e:
        print(col_r + f"❌ Status check failed: {e}" + Fore.RESET)
        return False

class HTTP11Session:
    def __init__(self):
        self.http = urllib3.PoolManager(
            maxsize=5,
            retries=urllib3.Retry(total=1, backoff_factor=0.1),
            timeout=urllib3.Timeout(connect=1.5, read=5.0)
        )

    def make_request(self, method, url, headers=None, body=None):
        try:
            request_headers = headers or {}
            request_headers.update({
                'Content-Type': 'application/json; charset=utf-8',
                'Accept': 'application/json',
                'Accept-Encoding': 'gzip, deflate',
                'Origin': 'https://i.mi.com',
                'Referer': 'https://i.mi.com/forum/',
                'User-Agent': random.choice(user_agents),
                'Connection': 'close'
            })
            
            if method == 'POST':
                if body is None:
                    body = '{"is_retry":true}'.encode('utf-8')
                request_headers['Content-Length'] = str(len(body))
            
            response = self.http.request(method, url, headers=request_headers, body=body, preload_content=False)
            return response
        except Exception as e:
            print(col_r + f"🌐 Network error: {e}" + Fore.RESET)
            return None

def send_burst_requests(session, device_id, is_test=False):
    url = "https://sgp-api.buy.mi.com/bbs/api/global/apply/bl-auth"
    request_count = 0
    max_requests = 10
    
    mode = "TEST" if is_test else "LIVE"
    print(col_yb + f"\n{'🔥 TEST' if is_test else '🚀 LIVE'} BURST: {max_requests} requests max" + Fore.RESET)
    
    for i in range(max_requests):
        request_count = i + 1
        request_time = datetime.now(beijing_tz) if is_test else get_synchronized_beijing_time(start_beijing_time, start_timestamp)
        
        headers = {"Cookie": f"new_bbs_serviceToken={token};versionCode=500411;versionName=5.4.11;deviceId={device_id};"}
        response = session.make_request('POST', url, headers=headers)
        
        if not response:
            time.sleep(0.1 if is_test else random.uniform(0.005, 0.015))
            continue

        try:
            response_data = json.loads(response.data.decode('utf-8'))
            response.release_conn()
            print_full_response(response_data, request_time)
            
            code = response_data.get("code")
            data = response_data.get("data", {})
            apply_result = data.get("apply_result")

            if code == 0:
                if apply_result == 1:
                    print(col_gb + "🎉 APPROVED! Checking status..." + Fore.RESET)
                    return check_unlock_status(session, token, device_id)
                elif apply_result in [3, 4]:
                    deadline = data.get("deadline_format", "unknown")
                    print(col_y + f"⏰ Blocked until {deadline}" + Fore.RESET)
            
            elif code == 100003:
                print(col_y + "🔄 Possible approval - checking status..." + Fore.RESET)
                return check_unlock_status(session, token, device_id)
                
        except Exception as e:
            print(col_r + f"❌ Parse error: {e}" + Fore.RESET)
        
        time.sleep(0.1 if is_test else random.uniform(0.005, 0.015))
    
    print(col_g + f"✅ Burst complete: {request_count} requests sent" + Fore.RESET)
    return False

# Global vars for timing
start_beijing_time = None
start_timestamp = None
beijing_tz = pytz.timezone("Asia/Shanghai")

def main():
    global start_beijing_time, start_timestamp
    
    session = HTTP11Session()
    device_id = generate_device_id()
    
    # Single status check - NO LOOP ON COOKIE EXPIRY
    print(col_y + "\n🔍 Checking account status (1 attempt)..." + Fore.RESET)
    if not check_unlock_status(session, token, device_id):
        input(col_r + "\n❌ Status check failed. Press Enter to exit..." + Fore.RESET)
        return
    
    if args.test:
        print(col_yb + "\n=== 🚀 TEST MODE: Sending NOW ===" + Fore.RESET)
        send_burst_requests(session, device_id, is_test=True)
    else:
        # LIVE: Perfect 9:30PM timing
        start_beijing_time = get_initial_beijing_time()
        if start_beijing_time is None:
            input(col_rb + "\n❌ NTP failed - cannot sync time. Press Enter..." + Fore.RESET)
            return
        
        start_timestamp = time.time()
        flood_start_time = wait_until_target_window(start_beijing_time, start_timestamp)
        send_burst_requests(session, device_id, is_test=False)
    
    input(col_y + "\n👉 Press Enter to exit..." + Fore.RESET)

if __name__ == "__main__":
    main()
