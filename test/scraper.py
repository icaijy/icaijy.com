import requests

url = "https://orac2.info/hub/leaderboards/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

r = requests.get(url, headers=headers, verify=False)  # verify=False 跳过 SSL 验证

print("Status:", r.status_code)
print(r.text[:800])

