import urllib.request
try:
    req = urllib.request.Request("https://proxymazegmora.duckdns.org/debug/test-post?url=https://evaluator.torchproxies.com/")
    with urllib.request.urlopen(req) as resp:
        print(resp.read().decode())
except Exception as e:
    print(e)
