#!/usr/bin/env python3
import os
import subprocess
import time
import urllib.request, urllib.error

COMPONENTS = "ethif arpv4 ipv4 tcp udp".split()

def prefixes(s):
    for i in range(len(s) + 1):
        yield s[:i]

def ensure_disconnected():
    try:
        urllib.request.urlopen('http://example.com', timeout=0.5)
        assert False, "Please disconnect from the Internet before running benchmarks."
    except urllib.error.URLError:
        pass

HARS_DIR = "hars"
REPEATS_BY_CONFIG = 10

def capture_har(fname):
    os.makedirs(HARS_DIR, exist_ok=True)
    fpath = os.path.join(HARS_DIR, fname)
    subprocess.check_call(["chrome-har-capturer", "--output", fpath, "http://10.0.0.2:8080/blog"],
                          stdout=subprocess.DEVNULL)

def benchmark(config):
    with open("config.fiat4mirage", mode="w") as out:
        out.write(" ".join(config) + "\n")

    webserver = subprocess.Popen(["./mir-www"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(1)
        for repeat in range(REPEATS_BY_CONFIG):
            capture_har("{}--{}".format("-".join(config), repeat))
    finally:
        webserver.kill()

def main():
    ensure_disconnected()
    for config in prefixes(COMPONENTS):
        print("\n# Benchmarking {}...".format(config))
        benchmark(config)

if __name__ == '__main__':
    main()
