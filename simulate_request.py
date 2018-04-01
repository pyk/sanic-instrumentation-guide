"""
This script is to simulate a user requests.

Run:
    python simlate_request.py

"""
import random

import requests


def main():
    # Generate a random number of requests
    while True:
        n = random.randint(1, 10)
        for _ in range(n):
            requests.get("http://localhost:8080")
        m = random.randint(1, 5)
        for _ in range(m):
            requests.get("http://localhost:8080/products")
        requests.post("http://localhost:8080/order", data={"test": "value"})


if __name__ == '__main__':
    main()
