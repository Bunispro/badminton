import urllib.request
import urllib.error

url = "http://127.0.0.1:8001/api/player/54897/stats?event=MS&model=elo"
print(f"Requesting URL: {url}")
try:
    with urllib.request.urlopen(url) as response:
        html = response.read().decode('utf-8')
        print(f"Status Code: {response.status}")
        print("Response Body:")
        print(html[:500])
except urllib.error.HTTPError as e:
    print(f"HTTPError: {e.code} - {e.reason}")
    print("Response Body:")
    print(e.read().decode('utf-8'))
except Exception as e:
    print(f"Exception: {e}")
