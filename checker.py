import requests
import time
import os
import threading
import random
import string
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================================
#   AYARLAR
# ============================================================

WEBHOOK_URL    = "YOUR_DISCORD_WEBHOOK_URL"
USERNAMES_FILE = "usernames.txt"
PROXIES_FILE   = "proxies.txt"

# --- Webshare Rotating Residential ayarları ---
# Webshare aldıysan buraya kullanıcı adı ve şifreni yaz.
# proxies.txt'i boş bırak, ikisini aynı anda kullanma.
WEBSHARE_USER     = ""   # Your proxy username
WEBSHARE_PASS     = ""   # Your proxy password
WEBSHARE_ENDPOINT = "p.webshare.io:80"

# --- Hız ayarları ---
THREADS       = 10    # Paralel thread sayısı
DELAY_SECONDS = 0.3   # Her thread'in istekler arası bekleme süresi

# ============================================================

DISCORD_REGISTER = "https://discord.com/api/v9/auth/register"

HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "X-Super-Properties": (
        "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX"
        "2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbm"
        "Rvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGl"
        "rZSBHZWNrbykgQ2hyb21lLzEyNC4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJz"
        "aW9uIjoiMTI0LjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwIn0="
    ),
    "Origin": "https://discord.com",
    "Referer": "https://discord.com/register",
}

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
GRAY   = "\033[90m"
RESET  = "\033[0m"

print_lock   = threading.Lock()
results_lock = threading.Lock()
webhook_lock = threading.Lock()
counter_lock = threading.Lock()

checked_count   = 0
available_list  = []
total_usernames = 0


def load_file(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def random_email():
    """Her istek için benzersiz sahte email üretir."""
    rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=20))
    return f"{rand}@discard.email"


def parse_proxy(proxy_str):
    proxy_str = proxy_str.strip()
    if not proxy_str:
        return None
    if proxy_str.startswith("http://") or proxy_str.startswith("https://"):
        return {"http": proxy_str, "https": proxy_str}
    parts = proxy_str.split(":")
    if len(parts) == 2:
        url = f"http://{parts[0]}:{parts[1]}"
    elif len(parts) == 4:
        ip, port, user, password = parts
        url = f"http://{user}:{password}@{ip}:{port}"
    else:
        return None
    return {"http": url, "https": url}


def get_rotating_proxy():
    if not WEBSHARE_USER or not WEBSHARE_PASS:
        return None
    url = f"http://{WEBSHARE_USER}:{WEBSHARE_PASS}@{WEBSHARE_ENDPOINT}"
    return {"http": url, "https": url}


def safe_print(msg):
    with print_lock:
        print(msg)


def send_webhook(username):
    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    payload = {
        "content": "@everyone",
        "embeds": [
            {
                "title": "✅ Müsait Username Bulundu!",
                "description": f"**`{username}`** Discord'da müsait!",
                "color": 0x00FF7F,
                "fields": [
                    {"name": "📋 Username", "value": f"`{username}`", "inline": True},
                    {"name": "🕐 Zaman",    "value": timestamp,       "inline": True},
                ],
                "footer": {"text": "Discord Username Checker"},
            }
        ]
    }
    with webhook_lock:
        try:
            r = requests.post(WEBHOOK_URL, json=payload, timeout=10)
            if r.status_code not in (200, 204):
                safe_print(f"{YELLOW}[WEBHOOK] Gönderilemedi: {r.status_code}{RESET}")
        except Exception as e:
            safe_print(f"{YELLOW}[WEBHOOK] Hata: {e}{RESET}")


def check_username(username, proxy):
    """
    Discord kayıt endpoint'i üzerinden username kontrolü.

    Mantık:
      - "USERNAME_ALREADY_TAKEN" hatası → alınmış
      - Username hatası yok, başka hata (email vb.) → müsait
      - 429 → rate limit
    """
    retries = 3
    for attempt in range(retries):
        try:
            payload = {
                "username": username,
                "password": "Tr0ub4dour&3xtraStr0ng!99",
                "email": random_email(),
                "consent": True,
                "date_of_birth": "2000-01-01",
                "captcha_key": None,
            }
            response = requests.post(
                DISCORD_REGISTER,
                json=payload,
                headers=HEADERS,
                proxies=proxy,
                timeout=10,
            )

            if response.status_code == 400:
                body = response.json()
                errors = body.get("errors", {})
                username_errors = errors.get("username", {}).get("_errors", [])
                codes = [e.get("code") for e in username_errors]

                if "USERNAME_ALREADY_TAKEN" in codes:
                    return False  # alınmış
                else:
                    return True   # müsait (username hatası yok, başka validasyon hatası)

            elif response.status_code == 201:
                # Gerçekten kayıt oldu? Bu olmamalı ama olursa müsaitti demek
                return True

            elif response.status_code == 429:
                retry_after = 10
                try:
                    retry_after = response.json().get("retry_after", 10)
                    retry_after = int(float(retry_after)) + 1
                except Exception:
                    pass
                return ("rate_limited", retry_after)

            else:
                if attempt < retries - 1:
                    time.sleep(2)
                    continue
                return "error"

        except requests.exceptions.ProxyError:
            return "proxy_error"
        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                time.sleep(2)
                continue
            return "timeout"
        except Exception:
            return "error"

    return "error"


def worker(username, proxy):
    global checked_count

    if len(username) < 2 or len(username) > 32:
        return

    result = check_username(username, proxy)

    # Rate limit gelirse bekle ve tekrar dene (aynı thread içinde)
    while isinstance(result, tuple) and result[0] == "rate_limited":
        retry_after = result[1]
        safe_print(f"{YELLOW}[RATE LIMIT] {retry_after}s bekleniyor...{RESET}")
        time.sleep(retry_after)
        result = check_username(username, proxy)

    with counter_lock:
        checked_count += 1
        current = checked_count

    if result is True:
        safe_print(f"{GREEN}[MÜSAİT] {username}  ({current}/{total_usernames}){RESET}")
        with results_lock:
            available_list.append(username)
        send_webhook(username)

    elif result is False:
        if current % 100 == 0:
            safe_print(f"{GRAY}[{current}/{total_usernames}] kontrol ediliyor...{RESET}")

    elif result == "proxy_error":
        safe_print(f"{YELLOW}[PROXY HATA] {username}{RESET}")

    else:
        safe_print(f"{YELLOW}[HATA] {username}{RESET}")

    time.sleep(DELAY_SECONDS)


def main():
    global total_usernames

    print(f"{CYAN}{'='*55}")
    print("   Discord Username Checker  —  Multi-Thread")
    print(f"{'='*55}{RESET}\n")

    usernames   = load_file(USERNAMES_FILE)
    proxies_raw = load_file(PROXIES_FILE)

    if not usernames:
        print(f"{RED}[HATA] {USERNAMES_FILE} dosyası bulunamadı veya boş!{RESET}")
        return

    total_usernames = len(usernames)

    rotating_proxy = get_rotating_proxy()
    if rotating_proxy:
        proxy_pool = [rotating_proxy] * THREADS
        print(f"🔄 Mod: Webshare Rotating Residential")
    elif proxies_raw:
        proxy_pool = [p for p in (parse_proxy(x) for x in proxies_raw) if p]
        print(f"🔄 Mod: Proxy listesi ({len(proxy_pool)} proxy)")
    else:
        proxy_pool = [None]
        print(f"🔄 Mod: Proxysiz")

    print(f"📋 Kontrol edilecek username : {total_usernames}")
    print(f"⚡ Thread sayısı             : {THREADS}")
    print(f"⏱️  Thread başına bekleme    : {DELAY_SECONDS}s")
    tahmini = (total_usernames / THREADS) * DELAY_SECONDS / 60
    print(f"🕐 Tahmini süre              : ~{tahmini:.0f} dakika\n")

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = [
            executor.submit(worker, username, proxy_pool[i % len(proxy_pool)])
            for i, username in enumerate(usernames)
        ]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception:
                pass

    elapsed = (time.time() - start_time) / 60

    print(f"\n{CYAN}{'='*55}")
    print(f"  Tamamlandı! {checked_count} username kontrol edildi.")
    print(f"  Geçen süre: {elapsed:.1f} dakika")
    print(f"  Bulunan müsait username: {len(available_list)}")
    if available_list:
        print(f"\n  ✅ Müsait olanlar:")
        for u in available_list:
            print(f"     - {u}")
    print(f"{'='*55}{RESET}")

    if available_list:
        with open("available.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(available_list))
        print(f"\n💾 'available.txt' dosyasına kaydedildi.")


if __name__ == "__main__":
    main()
