#!/usr/bin/python3
"""
Handle config data for the app
"""

import tkinter as tk
import sys # for sys.exit
import yaml
from pathlib import Path

APP_NAME = "Azure Backlog Sorter"

def get_user_config_path():
    base = Path.home() / "Library" / "Application Support" / APP_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base / "config.yml"

def load_config():
    cfg_path = get_user_config_path()
    with open(cfg_path, "r") as f:
        return yaml.safe_load(f)

def save_config(entries, win, root):
    cfg_path = get_user_config_path()
    cfg = load_config()

    for key, widget in entries.items():
        cfg[key] = widget.get()

    with open(cfg_path, "w") as f:
        yaml.safe_dump(cfg, f)

    root.rebuild_dropdown(cfg)
    win.destroy()

def open_config_window(root):
    cfg = load_config()

    win = tk.Toplevel()
    win.title("Configuration")
    if cfg is None: 
        return
    
    entries = {}
    row = 0
    for key, value in cfg.items():
        if key == "version":
            continue
        label = tk.Label(win, text=f"{key}:")
        label.grid(row=row, column=0, sticky="e", padx=10, pady=5)

        entry = tk.Entry(win, width=30)
        entry.insert(0, str(value))
        entry.grid(row=row, column=1, sticky="w", padx=10, pady=5)

        entries[key] = entry
        row += 1

    save_btn = tk.Button(win, text="Save", command=lambda: save_config(entries, win, root))
    save_btn.grid(row=row, column=0, columnspan=2, pady=15)

def check_config(config):
    error_msgs = ""
    if not config['organization']:
        error_msgs += "'organization', "
    if not config['project']:
        error_msgs += "'project', "  
    if not config['team']:
        error_msgs += "'team', "
    if not config['pat'] or len(config['pat']) < 64:
        error_msgs += "'pat', "
    if not config['field_priority']:
        error_msgs += "'field_priority', "
    if not config['field_stackrank']:
        error_msgs += "'field_stackrank', "

    error_msgs = error_msgs.removesuffix(", ")

    return error_msgs