import time
import requests


def request_get(url):
    try:
        requests.get(url, timeout=1)
    except requests.exceptions.RequestException:
        pass


def http_request():
    start = time.time()
    request_get("https://www.google.com/")
    request_get("https://github.com/")
    request_get("https://cn.bing.com/")
    request_get("https://www.baidu.com/")
    request_get("https://docs.python.org/")
    request_get("https://flask.palletsprojects.com/")
    end = time.time()
    delta = round(end - start, 2)
    print(f"Execution time: {delta}s")


if __name__ == '__main__':
    http_request()