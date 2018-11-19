#!/usr/bin/env python3
import os
import subprocess
from time import strftime, sleep
import signal
import json
import urllib

from selenium import webdriver
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile

REPEATS_BY_CONFIG = 200
BLOG_URL = "http://10.0.0.2:8080/blog"
COMPONENTS = ["ethif-encoding", "ethif-decoding",
              # "arpv4-encoding", "arpv4-decoding",
              "ipv4-encoding", "ipv4-decoding",
              "tcp-encoding", "tcp-decoding",
              # "udp-encoding", "udp-decoding"
]

def prefixes(s):
    for i in range(len(s) + 1):
        yield s[:i]

# def capture_har(fname):
#     # Start chrome like this:
#     # google-chrome --remote-debugging-port=9222 --enable-benchmarking --enable-net-benchmarking
#     os.makedirs(HARS_DIR, exist_ok=True)
#     fpath = os.path.join(HARS_DIR, fname)
#     subprocess.check_call(["chrome-har-capturer", "--output", fpath, "http://10.0.0.2:8080/blog"],
#                           stdout=subprocess.DEVNULL)

class WGet():
    ID = "wget"

    @staticmethod
    def read_wget_time(path):
        d = {}
        with open(os.path.join(path, "wget.time")) as f:
            for line in f:
                line = line.strip()
                if line != "":
                    label, time = line.split()
                    d[label] = 1000 * float(time)
        with open(os.path.join(path, "wget.out")) as f:
            d["out"] = f.read()
        return d

    def capture(self, dirpath, url):
        os.chdir(dirpath)
        os.environ["TIMEFORMAT"] = '\nreal\t%3R\nuser\t%3U\nsys\t%3S'
        CMD = "time (wget --no-verbose --page-requisites {} 2> wget.out) 2> wget.time"
        subprocess.check_call(["bash", "-c", CMD.format(url)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return WGet.read_wget_time(dirpath)

    def quit(self):
        pass

class Firefox():
    ID = "firefox"
    BINARY = FirefoxBinary('/usr/bin/firefox')

    def __init__(self):
        profile = FirefoxProfile()
        profile.set_preference("browser.cache.disk.enable", False)
        profile.set_preference("browser.cache.memory.enable", False)
        profile.set_preference("browser.cache.offline.enable", False)
        profile.set_preference("network.http.use-cache", False)
        self.driver = webdriver.Firefox(firefox_binary=Firefox.BINARY, firefox_profile=profile)

    @staticmethod
    def timings_delta(timings, start, end):
        return timings[end] - timings[start]

    @staticmethod
    def page_download_time(timings):
        return Firefox.timings_delta(timings, "connectStart", "responseEnd")

    @staticmethod
    def page_load_time(timings):
        return Firefox.timings_delta(timings, "fetchStart", "loadEventEnd")

    @staticmethod
    def page_dl_time_ratio(timings):
        dl = Firefox.timings_delta(timings, "fetchStart", "responseEnd")
        tl = Firefox.timings_delta(timings, "fetchStart", "loadEventEnd")
        return dl / tl

    def capture(self, _dirpath, url):
        self.driver.get(url)
        timings = self.driver.execute_script("return window.performance.timing")
        pl, dl = Firefox.page_load_time(timings), Firefox.page_download_time(timings)
        return { 'raw': timings, 'real': pl, 'dl': dl }

    def quit(self):
        self.driver.quit()

DRIVER = Firefox

def benchmark(driver, config, bin_path, basedir):
    with open("/tmp/fiat4mirage.config", mode="w") as out:
        out.write(" ".join(config) + "\n")

    with open(os.path.join(basedir, "mirage.log"), mode="w") as server_out:
        webserver = subprocess.Popen([bin_path], stdout=server_out, stderr=subprocess.STDOUT)
        sleep(2)
        try:
            for repeat in range(REPEATS_BY_CONFIG):
                dirpath = os.path.join(basedir, str(repeat))
                os.makedirs(dirpath, exist_ok=True)
                cap = driver.capture(dirpath, BLOG_URL)
                print(repeat, cap["real"], config)
                yield cap
        finally:
            webserver.send_signal(signal.SIGINT)
            try:
                webserver.wait(timeout=1)
            except subprocess.TimeoutExpired:
                print("Server didn't exit on Ctrl+C")
                webserver.kill()

def ensure_disconnected():
    try:
        urllib.request.urlopen('http://example.com', timeout=0.5)
        assert False, "Please disconnect from the Internet before running benchmarks."
    except urllib.error.URLError:
        pass

def main():
    ensure_disconnected()
    bin_path = os.path.abspath("./main.native")

    rel_root = os.path.join("..", DRIVER.ID + "-logs", strftime("%Y-%m-%d-%H-%M-%S"))
    root = os.path.abspath(rel_root)
    os.makedirs(root)

    driver = DRIVER()
    try:
        measurements = {}
        for config in prefixes(COMPONENTS):
            confstr = "+".join(config)

            configdir = os.path.join(root, confstr or "none")
            os.makedirs(configdir, exist_ok=True)

            print("\n# Benchmarking {}, saving to {}...".format(config, configdir))
            measurements[confstr] = list(benchmark(driver, config, bin_path, configdir))
    finally:
        driver.quit()

    with open(os.path.join(root, "all.json"), mode="w") as out:
        json.dump(measurements, out, sort_keys=True, indent=2)

if __name__ == '__main__':
    main()
