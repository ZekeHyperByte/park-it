#!/usr/bin/env python3
"""E-Parking v2 System Tray Indicator.

Shows a tray icon indicating system status with menu to start/stop/open.

Install deps:
    sudo apt install libappindicator3-1 gir1.2-appindicator3-0.1
    pip install -r scripts/tray-indicator-requirements.txt

Run:
    python scripts/tray-indicator.py
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("AppIndicator3", "0.1")

from gi.repository import AppIndicator3, GLib, Gtk

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
LOGS_DIR = PROJECT_ROOT / "logs"
PIDS_DIR = PROJECT_ROOT / "pids"


def check_service(url: str, timeout: float = 2.0) -> bool:
    """Check if a service is responding."""
    import urllib.request

    try:
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except Exception:
        return False


def get_status() -> dict:
    """Check status of all services."""
    return {
        "api": check_service("http://localhost:8000/api/health"),
        "frontend": check_service("http://localhost:3000"),
        "postgres": subprocess.call(
            ["docker", "compose", "exec", "-T", "postgres", "pg_isready", "-U", "parking"],
            cwd=PROJECT_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        == 0,
        "redis": subprocess.call(
            ["docker", "compose", "exec", "-T", "redis", "redis-cli", "ping"],
            cwd=PROJECT_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        == 0,
    }


def get_icon_name(status: dict) -> str:
    """Determine icon based on status."""
    if all(status.values()):
        return "emblem-default"  # Green check
    elif any(status.values()):
        return "dialog-warning"  # Yellow warning
    else:
        return "dialog-error"  # Red error


class TrayIndicator:
    def __init__(self):
        self.indicator = AppIndicator3.Indicator.new(
            "eparking-tray",
            "dialog-error",
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_menu(self.build_menu())
        self.update_status()

        # Poll every 5 seconds
        GLib.timeout_add_seconds(5, self.update_status)

    def build_menu(self):
        menu = Gtk.Menu()

        # Status label
        self.status_item = Gtk.MenuItem(label="Status: Checking...")
        self.status_item.set_sensitive(False)
        menu.append(self.status_item)

        menu.append(Gtk.SeparatorMenuItem())

        # Actions
        start_item = Gtk.MenuItem(label="Start E-Parking")
        start_item.connect("activate", self.on_start)
        menu.append(start_item)

        stop_item = Gtk.MenuItem(label="Stop E-Parking")
        stop_item.connect("activate", self.on_stop)
        menu.append(stop_item)

        menu.append(Gtk.SeparatorMenuItem())

        open_pos_item = Gtk.MenuItem(label="Open POS")
        open_pos_item.connect("activate", self.on_open_pos)
        menu.append(open_pos_item)

        view_logs_item = Gtk.MenuItem(label="View Logs")
        view_logs_item.connect("activate", self.on_view_logs)
        menu.append(view_logs_item)

        view_docs_item = Gtk.MenuItem(label="View API Docs")
        view_docs_item.connect("activate", self.on_view_docs)
        menu.append(view_docs_item)

        menu.append(Gtk.SeparatorMenuItem())

        exit_item = Gtk.MenuItem(label="Exit")
        exit_item.connect("activate", self.on_exit)
        menu.append(exit_item)

        menu.show_all()
        return menu

    def update_status(self):
        status = get_status()
        icon = get_icon_name(status)
        self.indicator.set_icon_full(icon, "E-Parking Status")

        running = [k for k, v in status.items() if v]
        if len(running) == 4:
            label = "Status: All systems running"
        elif running:
            label = f"Status: {', '.join(running)} running"
        else:
            label = "Status: Stopped"
        self.status_item.set_label(label)

        return True  # Continue polling

    def on_start(self, _):
        subprocess.Popen(
            ["x-terminal-emulator", "-e", f"{PROJECT_ROOT}/scripts/dev-start.sh"],
            cwd=PROJECT_ROOT,
        )

    def on_stop(self, _):
        subprocess.Popen(
            ["x-terminal-emulator", "-e", f"{PROJECT_ROOT}/scripts/dev-stop.sh"],
            cwd=PROJECT_ROOT,
        )

    def on_open_pos(self, _):
        subprocess.Popen(["xdg-open", "http://localhost:3000"])

    def on_view_logs(self, _):
        subprocess.Popen(["xdg-open", str(LOGS_DIR)])

    def on_view_docs(self, _):
        subprocess.Popen(["xdg-open", "http://localhost:8000/docs"])

    def on_exit(self, _):
        Gtk.main_quit()


def main():
    indicator = TrayIndicator()
    Gtk.main()


if __name__ == "__main__":
    main()
