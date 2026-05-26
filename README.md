# Discord Username Checker

A fast, multi-threaded Discord username availability checker with proxy support and Discord webhook notifications.

## Features

- Multi-threaded — checks up to 10 usernames at the same time
- Proxy support — avoids rate limits by rotating IP addresses
- Instantly sends available usernames to your Discord webhook with @everyone ping
- Saves all available usernames to `available.txt`
- Automatically waits and retries when rate limited

## Setup

### 1. Install Python
Download from https://python.org/downloads — make sure to check **"Add to PATH"** during installation.

### 2. Install dependencies
```
pip install requests colorama
```

### 3. Add your usernames
Open `usernames.txt` and add the usernames you want to check, one per line:
```
shadow
frost
blade
```

### 4. Configure `checker.py`
Open `checker.py` and fill in your settings at the top of the file:

```python
WEBHOOK_URL = "https://discord.com/api/webhooks/..."  # Your Discord webhook URL
```

If you are using a proxy (recommended for large lists):
```python
WEBSHARE_USER     = "your_username"
WEBSHARE_PASS     = "your_password"
WEBSHARE_ENDPOINT = "your_proxy_endpoint:port"
```

### 5. Run
```
python checker.py
```

---

## What is a Proxy and Why Do You Need One?

When you send too many requests to Discord from the same IP address, Discord temporarily blocks you — this is called a **rate limit**. 

A proxy acts as a middleman between you and Discord. Instead of your requests coming from your own IP, they go through the proxy server's IP. With a **rotating proxy**, every single request uses a different IP address, so Discord never sees enough requests from one source to trigger a rate limit.

**Without proxy:** Rate limited after ~5 requests, slow, requires long waits between checks.  
**With proxy:** Checks 50,000 usernames in ~25 minutes with virtually no rate limits.

For large username lists, a rotating residential proxy is highly recommended. You can find proxy services online — prices usually start around $3–5/month.

---

## How to Get a Discord Webhook

1. Open Discord and go to a channel's settings
2. Click **Integrations → Webhooks → New Webhook**
3. Copy the webhook URL and paste it into `checker.py`

---

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `THREADS` | 10 | Number of parallel checks |
| `DELAY_SECONDS` | 0.3 | Delay between requests per thread |
| `WEBSHARE_USER` | empty | Proxy username |
| `WEBSHARE_PASS` | empty | Proxy password |

---

## Project Structure

```
discord-username-checker/
├── checker.py       # Main script
├── usernames.txt    # Usernames to check (one per line)
├── proxies.txt      # Optional static proxy list
└── available.txt    # Found available usernames (auto-generated)
```

`proxies.txt` supports the following formats:
```
ip:port
ip:port:username:password
http://ip:port
http://username:password@ip:port
```
