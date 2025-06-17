"""Simple command-line tool to control the trading daemon."""

import argparse
import requests

API_BASE = "http://127.0.0.1:8000"


def start() -> None:
    resp = requests.post(f"{API_BASE}/start")
    print(resp.json())


def stop() -> None:
    resp = requests.post(f"{API_BASE}/stop")
    print(resp.json())


def status() -> None:
    resp = requests.get(f"{API_BASE}/status")
    print(resp.json())


def main() -> None:
    parser = argparse.ArgumentParser(description="Control the trading daemon")
    parser.add_argument("command", choices=["start", "stop", "status"])
    args = parser.parse_args()
    if args.command == "start":
        start()
    elif args.command == "stop":
        stop()
    elif args.command == "status":
        status()


if __name__ == "__main__":
    main()

