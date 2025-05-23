import sys
import os
import subprocess
import time
import json
import signal
import random
import socks
import socket
from datetime import datetime, timezone, timedelta
import dns.resolver
import requests
import platform
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from webdriver_manager.firefox import GeckoDriverManager
from rich.console import Console
from rich.padding import Padding

console = Console()

def watchdog_update():
    """Checks for updates from GitHub and asks for confirmation before applying."""
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    python_executable = sys.executable
    script_path = os.path.abspath(__file__)

    try:
        # Return changes from remote without applying them yet
        subprocess.run(
            ["git", "-C", repo_dir, "fetch", "origin", "main"],
            capture_output=True, text=True
        )

        # Check if updates are available
        diff_result = subprocess.run(
            ["git", "-C", repo_dir, "diff", "HEAD..origin/main"],
            capture_output=True, text=True
        )

        if not diff_result.stdout:
            console.print("")
            console.print(Padding("[bold green]→ No updates found. Running the script normally...[/bold green]", (0, 0, 0, 4)))
            return

        # Show changes before updating
        console.print("")
        console.print(Padding("[bold yellow]→ Updates are available! Here are the changes:[/bold yellow]", (0, 0, 0, 4)))
        console.print(Padding(diff_result.stdout, (0, 0, 0, 4)))

        # Confirm first
        user_input = input("\n[?] Apply these updates? (y/n): ").strip().lower()
        if user_input != "y":
            console.print("")
            console.print(Padding("[bold cyan]→ Update skipped. Running the current version.[/bold cyan]", (0, 0, 0, 4)))
            return

        # Apply the update
        update_result = subprocess.run(
            ["git", "-C", repo_dir, "pull", "origin", "main"],
            capture_output=True, text=True
        )

        console.print("")
        console.print(Padding("[bold yellow]→ Update applied! Restarting script in 3 seconds...[/bold yellow]", (0, 0, 0, 4)))
        time.sleep(3)

        # Restart the script
        subprocess.Popen([python_executable, script_path] + sys.argv[1:])
        sys.exit(0)

    except Exception as e:
        console.print("")
        console.print(Padding(f"[bold red]→ Couldn't update from GitHub. Error: {e}[/bold red]", (0, 0, 0, 4)))

# Run auto-update first
watchdog_update()

def clear_screen():
    try:
        time.sleep(3)
        if sys.platform == "win32":
            os.system("cls")
        else:
            os.system("clear")
    except KeyboardInterrupt:
        console.print("")
        console.print(Padding("[bold red]\n[!] Script interrupted by user. Exiting cleanly...[/bold red]", (0, 0, 0, 4)))
        sys.exit(0)

load_dotenv()

clear_screen()

ascii_banner = r"""
 ______ ____ _____  __          __   _       _         _             
|  ____|  _ \_   _| \ \        / /  | |     | |       | |            
| |__  | |_) || |    \ \  /\  / /_ _| |_ ___| |__   __| | ___   __ _  
|  __| |  _ < | |     \ \/  \/ / _` | __/ __| '_ \ / _` |/ _ \ / _` |
| |    | |_) || |_     \  /\  / (_| | || (__| | | | (_| | (_) | (_| |
|_|    |____/_____|     \/  \/ \__,_|\__\___|_| |_|\__,_|\___/ \__, |
                                                                __/ |
                .--~~,__          Catching seizure banners...  |___/  
    :-....,-------`~~'._.'       before law enforcement...
    `-,,,  ,_      ;'~U'        even realizes they exist.
     _,-' ,'`-__; '--.
    (_/'~~      ''''(;                                                    

[bold blue]FBI Watchdog v2.1.0 by [link=https://darkwebinformer.com]Dark Web Informer[/link][/bold blue]
"""

console.print(Padding(f"[bold blue]{ascii_banner}[/bold blue]", (0, 0, 0, 4)))

# Domain list to monitor for seizure banners and DNS changes

domains = [
    "example.com," "example1.com," "example2.com"
]

onion_sites = [
     "dreadytofatroptsdj6io7l3xptbet6onoyno2yv7jicoxknyazubrad.onion", "breached26tezcofqla4adzyn22notfqwcac7gpbrleg4usehljwkgqd.onion",
]

# DNS records that will be checked for changes
dnsRecords = ["A", "AAAA", "CNAME", "MX", "NS", "SOA", "TXT"]

webhook_url = os.getenv("WEBHOOK")
alert_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
alert_chat_id = os.getenv("TELEGRAM_CHAT_ID")

# If any env variables are missing, the script will not start.
if not webhook_url or not alert_bot_token or not alert_chat_id:
    console.print(Padding(f"[red]→ Missing environment variable! You did not set a WEBHOOK, TELEGRAM_BOT_TOKEN, and TELEGRAM_CHAT_ID.[/red]", (0, 0, 0, 4)))
    exit(1)

# File to store previous DNS results
state_file = "fbi_watchdog_results.json"
previous_results = {}

def send_request(url, data=None, use_tor=False):
    """Send a request using Tor only for .onion sites, normal internet uses direct connection."""
    
    # ✅ Default: No proxy (use normal internet)
    proxies = None  

    # ✅ Use Tor proxy ONLY for .onion sites
    if use_tor:
        proxies = {
            "http": "socks5h://127.0.0.1:9050",
            "https": "socks5h://127.0.0.1:9050"
        }

    try:
        if data:
            response = requests.post(url, json=data, proxies=proxies, timeout=15)
        else:
            response = requests.get(url, proxies=proxies, timeout=15)

        response.raise_for_status()
        return response.text

    except requests.exceptions.ProxyError:
        console.print(Padding(f"[red]→ Proxy Error! Check if you're trying to route normal traffic through Tor.[/red]", (0, 0, 0, 4)))
        return None

    except requests.exceptions.RequestException as e:
        console.print(Padding(f"[red]→ Request failed: {e}[/red]", (0, 0, 0, 4)))
        return None

# Send Telegram notification for DNS changes or seizure detection
def telegram_notify(domain, record_type, records, previous_records, seizure_capture=None):
    detected_time = (datetime.now(timezone.utc) + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S UTC")

    previous_records = previous_records if isinstance(previous_records, list) else []
    records = records if isinstance(records, list) else []

    previous_records_formatted = "\n".join(previous_records) if previous_records else "None"
    new_records_formatted = "\n".join(records) if records else "None"

    message = (
        "⚠️ *FBI Watchdog DNS Change Detected* ⚠️\n"
        "🔗 *DarkWebInformer.com - Cyber Threat Intelligence*\n\n"
        f"*Domain:* {domain}\n"
        f"*Record Type:* {record_type}\n"
        f"*Time Detected:* {detected_time}\n\n"
        f"*Previous Records:*\n```\n{previous_records_formatted}\n```\n"
        f"*New Records:*\n```\n{new_records_formatted}\n```"
    )

    send_request(f"https://api.telegram.org/bot{alert_bot_token}/sendMessage", 
                 data={"chat_id": alert_chat_id, "text": message, "parse_mode": "Markdown"},
                 use_tor=False)

    # ✅ Send Screenshot if Available
    if seizure_capture and os.path.exists(seizure_capture):
        console.print(Padding(f"→ Sending seizure image to Telegram for {domain}...", (0, 0, 0, 4)))
        with open(seizure_capture, 'rb') as photo:
            files = {"photo": photo}
            requests.post(f"https://api.telegram.org/bot{alert_bot_token}/sendPhoto",
                          data={"chat_id": alert_chat_id}, files=files)


# Send Discord notification for DNS changes or seizure detection
def discord_notify(domain, recordType, dnsRecords, prevEntry, screenshotPath=None):
    detected_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    prevEntry = prevEntry if isinstance(prevEntry, list) else []

    embed_data = {
        "embeds": [
            {
                "title": "⚠️ FBI Watchdog DNS Change Detected ⚠️",
                "description": (
                    "🔗 **DarkWebInformer.com - Cyber Threat Intelligence**\n\n"
                    f"**Domain:** `{domain}`\n"
                    f"**Record Type:** `{recordType}`\n"
                    f"**Time Detected:** {detected_time}\n\n"
                    f"**Previous Records:**\n```\n{'\n'.join(prevEntry) or 'None'}\n```\n"
                    f"**New Records:**\n```\n{'\n'.join(dnsRecords) or 'None'}\n```"
                ),
                "color": 16711680
            }
        ]
    }

    send_request(webhook_url, data=embed_data, use_tor=False)

    # ✅ Send Screenshot if Available
    if screenshotPath and os.path.exists(screenshotPath):
        console.print(Padding(f"→ Sending seizure image to Discord for {domain}...", (0, 0, 0, 4)))
        with open(screenshotPath, 'rb') as file:
            requests.post(webhook_url, files={"file": file})


def capture_seizure_image(domain, use_tor=False):
    """Capture a screenshot of a suspected seizure page using Firefox.
    
    - Uses **Tor (Firefox proxy settings)** for `.onion` sites.
    - Uses **Direct connection** for clearnet sites.
    """
    
    screenshot_filename = f"screenshots/{domain}_image.png"
    os.makedirs("screenshots", exist_ok=True)

    console.print(Padding(f"→ Capturing likely LEA seizure {domain}...", (0, 0, 0, 4)))

    try:
        options = FirefoxOptions()
        options.add_argument("--headless")
        options.add_argument("--window-size=2560,1440")  
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--disable-web-security")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # Automatically detect OS and set Firefox binary location
        if platform.system() == "Windows":
            options.binary_location = "C:\\Program Files\\Mozilla Firefox\\firefox.exe"
        elif platform.system() == "Linux":
            options.binary_location = "/usr/bin/firefox"
        elif platform.system() == "Darwin":  # macOS
            options.binary_location = "/Applications/Firefox.app/Contents/MacOS/firefox"
        else:
            raise Exception("Unsupported operating system: Cannot determine Firefox binary path.")

        if use_tor:
            console.print(Padding(f"→ Routing traffic through Tor for {domain}...", (0, 0, 0, 4)))

            options.set_preference("network.proxy.type", 1)
            options.set_preference("network.proxy.socks", "127.0.0.1")
            options.set_preference("network.proxy.socks_port", 9050)
            options.set_preference("network.proxy.socks_remote_dns", True)  # 🛠 Ensures Tor resolves .onion domains
            options.set_preference("network.http.referer.spoofSource", True)
            options.set_preference("privacy.resistFingerprinting", True)
            options.set_preference("network.dns.disableIPv6", True)  # 🔴 Prevents DNS leaks

        # ✅ Automatically download & update Geckodriver
        service = FirefoxService(GeckoDriverManager().install())  # Automatically finds & installs Geckodriver
        driver = webdriver.Firefox(service=service, options=options)

        try:
            url = f"http://{domain}" if not domain.startswith("http") else domain
            console.print(Padding(f"→ Attempting to load {url} via Selenium...", (0, 0, 0, 4)))

            driver.get(url)
            time.sleep(10)  # Wait for page to fully load

            # ✅ Print the page title for debugging
            console.print(Padding(f"→ Page Title: {driver.title}", (0, 0, 0, 4)))

        except Exception as e:
            console.print(Padding(f"→ Failed to access {domain}: {e}", (0, 0, 0, 4)))
            driver.quit()
            return None

        driver.save_screenshot(screenshot_filename)
        driver.quit()
        console.print(Padding(f"→ Seizure screenshot saved: {screenshot_filename}", (0, 0, 0, 4)))
        return screenshot_filename

    except Exception as e:
        console.print(Padding(f"→ Unable to save seizure screenshot. {domain}: {e}", (0, 0, 0, 4)))
        return None

onion_state_file = "onion_watchdog_results.json"
onion_results = {}  # Store `.onion` site statuses separately

def load_onion_results():
    """Load previous onion site results from a separate file at script startup."""
    global onion_results
    try:
        if os.path.exists(onion_state_file):
            with open(onion_state_file, "r", encoding="utf-8") as file:
                onion_results = json.load(file)
            console.print(Padding(f"[bold green]→ Loaded previous onion scan results.[/bold green]", (0, 0, 0, 4)))
        else:
            onion_results = {}
            console.print(Padding(f"[bold yellow]→ No previous onion scan results found, starting fresh.[/bold yellow]", (0, 0, 0, 4)))
    except Exception as e:
        console.print(Padding(f"[red]→ Error loading onion results: {e}[/red]", (0, 0, 0, 4)))
        onion_results = {}

def save_onion_results():
    """Save onion site results to a separate file to ensure persistence."""
    try:
        with open(onion_state_file, "w", encoding="utf-8") as file:
            json.dump(onion_results, file, indent=4, ensure_ascii=False)
        console.print(Padding(f"[bold green]→ Onion scan results saved successfully.[/bold green]", (0, 0, 0, 4)))
    except Exception as e:
        console.print(Padding(f"[red]→ Error saving onion results: {e}[/red]", (0, 0, 0, 4)))

def load_previous_results():
    global previous_results
    state_file = "fbi_watchdog_results.json"
    try:
        if os.path.exists(state_file):
            with open(state_file, "r", encoding="utf-8") as file:
                previous_results = json.load(file)
        else:
            previous_results = {}
    except Exception as e:
        console.print(Padding(f"[red]→ Error loading previous results: {e}[/red]", (0, 0, 0, 4)))
        previous_results = {}

# Save DNS scan results to JSON
def save_previous_results():
    state_file = "fbi_watchdog_results.json"
    try:
        with open(state_file, "w", encoding="utf-8") as file:
            json.dump(previous_results, file, indent=4, ensure_ascii=False)
        console.print(Padding(f"[bold green]→ All results have been successfully saved.[/bold green]", (0, 0, 0, 4)))
    except Exception as e:
        console.print("")
        console.print(Padding(f"[red]→ Error saving results: {e}[/red]", (0, 0, 0, 4)))

exit_flag = False

def signal_handler(sig, frame):
    global exit_flag
    if exit_flag:
        console.print("")
        console.print(Padding("[red]→ Force stopping...[/red]", (0, 0, 0, 4)))
        os._exit(1)
    exit_flag = True
    sys.stdout.write("\033[2K\r")
    sys.stdout.flush()
    console.print("")
    console.print(Padding("[red]→ Safely shutting down...[/red]", (0, 0, 0, 4)))
    save_previous_results()
    os._exit(0)

signal.signal(signal.SIGINT, signal_handler)

tor_status = True  # Global variable to store Tor connection status

def is_tor_running():
    """Checks if Tor is running and correctly routing traffic."""
    global tor_status

    # ✅ If tor_status is already True, don't check again
    if tor_status:
        return True  

    tor_ports = [9050, 9150]  # Check both common Tor ports

    for tor_port in tor_ports:
        try:
            socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", tor_port)
            socket.socket = socks.socksocket  # Redirect all sockets through Tor

            # ✅ First check: Try HTTPS version of Tor check page
            proxies = {"http": f"socks5h://127.0.0.1:{tor_port}", "https": f"socks5h://127.0.0.1:{tor_port}"}
            response = requests.get("https://check.torproject.org/", proxies=proxies, timeout=10)

            # ✅ Parse HTML to extract text properly
            soup = BeautifulSoup(response.text, "html.parser")
            if soup.find("h1", class_="not") and "Congratulations" in soup.find("h1", class_="not").text:
                tor_status = True
                console.print("")
                console.print(Padding(f"[bold green]→ Tor is running and routing traffic on port {tor_port}![/bold green]", (0, 0, 0, 4)))
                console.print("")
                return True
                
        except requests.exceptions.RequestException:
            console.print(Padding(f"[yellow]→ Tor check failed on port {tor_port}. Trying next port...[/yellow]", (0, 0, 0, 4)))
            continue  # Try the next port

    # ❌ If both checks fail, mark Tor as unavailable and log it
    tor_status = False
    console.print("")
    console.print(Padding("[bold red]→ Tor is NOT running or misconfigured! Skipping .onion scans.[/bold red]", (0, 0, 0, 4)))
    console.print("")
    return False

def check_onion_status(onion_url):
    """Check if a .onion site is seized by scanning for known seizure text in HTML."""
    global onion_results

    if not is_tor_running():  
        console.print(Padding(f"[red]→ Skipping {onion_url}: Tor is not running![/red]", (0, 0, 0, 4)))
        return False

    tor_proxy = "socks5h://127.0.0.1:9050"
    proxies = {"http": tor_proxy, "https": tor_proxy}

    last_status = onion_results.get(onion_url, {}).get("status", "unknown")

    try:
        response = requests.get(f"http://{onion_url}", proxies=proxies, timeout=30)  # Increased timeout
        html_content = response.text.lower()

        seizure_keywords = [
            "this hidden site has been seized", "fbi", "seized by", "department of justice",
            "europol", "nca", "interpol", "law enforcement", "this domain has been seized"
        ]

        is_seized = any(keyword in html_content for keyword in seizure_keywords)
        new_status = "seized" if is_seized else "active"

        if last_status == new_status:
            console.print(Padding(f"[cyan]→ No change detected for {onion_url}, skipping.[/cyan]", (0, 0, 0, 4)))
            return False

        if is_seized:
            console.print(Padding(f"[bold red]→ Seizure detected: {onion_url}[/bold red]", (0, 0, 0, 4)))
            seizure_capture = capture_seizure_image(onion_url, use_tor=True)

            onion_results[onion_url] = {"status": "seized", "last_checked": datetime.now(timezone.utc).isoformat()}
            save_onion_results()

            telegram_notify(onion_url, "Onion Seized", ["Seized"], ["Online"], seizure_capture)
            discord_notify(onion_url, "Onion Seized", ["Seized"], ["Online"], seizure_capture)

        else:
            console.print(Padding(f"[green]→ {onion_url} is active[/green]", (0, 0, 0, 4)))
            onion_results[onion_url] = {"status": "active", "last_checked": datetime.now(timezone.utc).isoformat()}
            save_onion_results()

        return is_seized

    except requests.exceptions.ConnectionError:
        console.print(Padding(f"[yellow]→ {onion_url} is unreachable. Connection refused.[/yellow]", (0, 0, 0, 4)))
        new_status = "unreachable"
    except requests.exceptions.Timeout:
        console.print(Padding(f"[yellow]→ {onion_url} timed out. Likely offline or slow.[/yellow]", (0, 0, 0, 4)))
        new_status = "unreachable"
    except requests.exceptions.RequestException as e:
        console.print(Padding(f"[yellow]→ {onion_url} is unreachable. Error: {e}[/yellow]", (0, 0, 0, 4)))
        new_status = "unreachable"

    if last_status == new_status:
        console.print(Padding(f"[cyan]→ No change detected for {onion_url}, skipping.[/cyan]", (0, 0, 0, 4)))
        return False

    onion_results[onion_url] = {"status": new_status, "last_checked": datetime.now(timezone.utc).isoformat()}
    save_onion_results()

    return False

def check_all_onion_sites():
    """Iterate through all .onion sites and check their status using a single Tor check."""
    global tor_status

    if not is_tor_running():
        console.print(Padding("[bold red]→ Skipping all .onion scans: Tor is not running![/bold red]", (0, 0, 0, 4)))
        return

    for onion_site in onion_sites:
        check_onion_status(onion_site)

    # ✅ Save results after all `.onion` sites are scanned
    save_onion_results()

    console.print(Padding("[bold green]→ Onion scan complete. Snoozing for 60 seconds...[/bold green]\n", (0, 0, 0, 4)))


# Monitor domains for DNS changes and possible seizures and send alerts when needed
def watch_dog():
    global exit_flag
    try:
        while not exit_flag:
            for i, domain in enumerate(domains, start=1):
                if exit_flag:
                    break
                console.print("")

                if i < len(domains):
                    console.print(Padding(f"[bold green]→ {(i / len(domains)) * 100:.0f}% complete[/bold green]", (0, 0, 0, 4)))

                for record_type in dnsRecords:
                    if exit_flag:
                        break
                    console.print(Padding(f"[bold cyan]→ Scanning {record_type:<5} records for {domain[:25]:<25}[/bold cyan]", (0, 0, 0, 4)))

                    # Check the DNS records for the current domain
                    try:
                        answers = dns.resolver.resolve(domain, record_type, lifetime=5)
                        records = [r.to_text() for r in answers]
                    except dns.resolver.NXDOMAIN:
                        continue
                    except dns.resolver.Timeout:
                        console.print(Padding(f"[red]→ DNS check timed out for {domain}[/red]", (0, 0, 0, 4)))
                        continue
                    except:
                        records = []

                    sorted_records = sorted(records)
                    prev_entry = previous_results.get(domain, {}).get(record_type, {"records": []})

                    # Ensure prev_entry is a dictionary before accessing keys
                    if not isinstance(prev_entry, dict):
                        prev_entry = {"records": []}

                    prev_sorted_records = sorted(prev_entry["records"])

                    if domain not in previous_results:
                        previous_results[domain] = {}

                    # Load history of previous record sets for this domain/record type
                    history = previous_results[domain].get(record_type, {}).get("history", [])

                    if sorted_records in history or exit_flag:
                        continue

                    console.print("")
                    console.print(Padding(f"→ Change detected: {domain} ({record_type})", (0, 0, 0, 4)))

                    formatted_previous = "\n".join(f"   - {entry}" for entry in history[-1]) if history else "   - None"
                    formatted_new = "\n".join(f"   - {entry}" for entry in sorted_records) or "   - None"

                    console.print("")
                    console.print(Padding(f"[yellow]→ Previous Records:[/yellow]\n[yellow]{formatted_previous}[/yellow]", (0, 0, 0, 4)))
                    console.print("")
                    console.print(Padding(f"[green]→ New Records:[/green]\n[green]{formatted_new}[/green]", (0, 0, 0, 4)))
                    console.print("")

                    seizure_capture = None
                    if record_type == "NS" and any(ns in sorted_records for ns in [
                        "ns1.fbi.seized.gov.", "ns2.fbi.seized.gov.",
                        "jocelyn.ns.cloudflare.com.", "plato.ns.cloudflare.com.",
                        "ns1.usssdomainseizure.com", "ns2.usssdomainseizure.com"
                    ]):
                        console.print(Padding(f"→ Taking seizure screenshot for {domain} (FBI Seized NS Detected)", (0, 0, 0, 4)))
                        seizure_capture = capture_seizure_image(domain)

                    discord_notify(domain, record_type, sorted_records, history[-1] if history else [], seizure_capture)
                    telegram_notify(domain, record_type, sorted_records, history[-1] if history else [], seizure_capture)

                    # Update stored results and append to history
                    history.append(sorted_records)
                    previous_results[domain][record_type] = {
                        "records": sorted_records,
                        "history": history[-10:]  # limit history to last 10 changes
                    }

            # ✅ Show this once after all domains are processed
            console.print(Padding("[bold green]→ 100% complete[/bold green]", (0, 0, 0, 4)))

            if is_tor_running():
                console.print("")
                console.print(Padding(f"→ Configuring Firefox to route traffic through Tor...", (0, 0, 0, 4)))
                console.print(Padding("[bold cyan]→ Checking .onion sites for seizures...[/bold cyan]", (0, 0, 0, 4)))
                console.print("")

                for onion_site in onion_sites:
                    check_onion_status(onion_site)

                console.print("")
                console.print(Padding("[bold green]→ Onion scan complete. Snoozing for 60 seconds...[/bold green]\n", (0, 0, 0, 4)))

            if not exit_flag:
                save_previous_results()
                console.print(Padding("[bold green]→ FBI Watchdog shift complete. Snoozing for 60 seconds...[/bold green]\n", (0, 0, 0, 4)))
                time.sleep(15)

    except KeyboardInterrupt:
        exit_flag = True
        console.print(Padding("[bold red]→ Monitoring interrupted by user. Exiting...[/bold red]", (0, 0, 0, 4)))
        save_previous_results()
        console.print(Padding("[bold green]→ FBI Watchdog Results saved successfully.[/bold green]", (0, 0, 0, 4)))
        exit(0)

if __name__ == "__main__":
    load_previous_results()  # ✅ Loads clearnet sites
    load_onion_results()  # ✅ Loads onion sites

    console.print(Padding("[bold cyan]→ Loading previous FBI Watchdog results...[/bold cyan]", (0, 0, 0, 4)))
    time.sleep(random.uniform(0.5, 1.2))

    console.print(Padding("[bold green]→ Previous FBI Watchdog results were successfully loaded...[/bold green]", (0, 0, 0, 4)))
    time.sleep(random.uniform(1.0, 2.0))

    console.print(Padding("[bold yellow]→ FBI Watchdog is starting to sniff for seizure records...[/bold yellow]\n", (0, 0, 0, 4)))
    time.sleep(random.uniform(1.5, 2.5))

    watch_dog()