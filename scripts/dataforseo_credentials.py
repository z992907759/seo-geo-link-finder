#!/usr/bin/env python3
"""Retrieve DataForSEO credentials from environment, macOS Keychain, or an interactive prompt."""

from __future__ import annotations

import getpass
import os
import subprocess
import sys


KEYCHAIN_SERVICE = "seo-geo-link-finder-dataforseo"


def get_credentials() -> tuple[str, str]:
    login = os.environ.get("DATAFORSEO_LOGIN", "").strip()
    password = os.environ.get("DATAFORSEO_PASSWORD", "")
    if login and not password:
        try:
            result = subprocess.run(
                ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", login, "-w"],
                check=True, capture_output=True, text=True,
            )
            password = result.stdout.strip()
        except (FileNotFoundError, subprocess.CalledProcessError):
            password = ""
    if login and password:
        return login, password
    if not sys.stdin.isatty():
        raise RuntimeError(
            "DataForSEO credentials unavailable. Set DATAFORSEO_LOGIN and store its password "
            f"in macOS Keychain service {KEYCHAIN_SERVICE!r}, or set DATAFORSEO_PASSWORD."
        )
    login = input("DataForSEO API login: ").strip()
    password = getpass.getpass("DataForSEO API password: ")
    if not login or not password:
        raise RuntimeError("DataForSEO login and password are required")
    return login, password
