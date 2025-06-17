"""Simple command-line tool to control the trading daemon."""

import argparse
import requests

from config import TRADING_DAEMON_URL


def start() -> None:
    resp = requests.post(f"{TRADING_DAEMON_URL}/start")
    print(resp.json())


def stop() -> None:
    resp = requests.post(f"{TRADING_DAEMON_URL}/stop")
    print(resp.json())


def status() -> None:
    resp = requests.get(f"{TRADING_DAEMON_URL}/status")
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

