#!/usr/bin/env python3
"""Render the README terminal GIF: a short boot log, a tty login, then a
fastfetch-style panel with live GitHub stats.

Config lives in config/ and must be copied to ~/.config/gifos before this
runs; gifos only reads its settings from that path. Needs GITHUB_TOKEN for
the stats query.

    python3 scripts/gen_terminal.py

Writes terminal.gif to the working directory.
"""

import os
import re
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import gifos

USER = "Wong-WeiJun"
IGNORE_REPOS = ["Wong-WeiJun"]
TIMEZONE = ZoneInfo("Australia/Sydney")

WIDTH = 1000
HEIGHT = 560
PADDING = 15
HOLD_SHORT = 5
HOLD_LONG = 130

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCH_LOGO_SOURCE = os.path.join(REPO_ROOT, "assets", "arch.txt")

ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*m")

MAUVE = "\x1b[95m"
BLUE = "\x1b[94m"
TEXT = "\x1b[97m"
SUB = "\x1b[34m"
BANNER = "\x1b[30;105m"
RESET = "\x1b[0m"

DETAILS_COLUMN = 42
PROMPT = "%sweijun@omarchy%s ~> " % (MAUVE, RESET)


def visible_width(line):
    return len(ANSI_PATTERN.sub("", line))


def arch_logo():
    """The classic Arch Linux mountain, recoloured to match the profile palette.

    Vendored from fastfetch (MIT) at src/logo/ascii/a/arch3.txt. It is plain
    ASCII, which the latin-1 bitmap font renders without substitution -- the
    block-glyph Omarchy wordmark does not survive that font, so this variant
    is used instead.
    """
    with open(ARCH_LOGO_SOURCE, encoding="utf-8") as handle:
        lines = handle.read().rstrip("\n").split("\n")
    return [MAUVE + line.replace("$2", "") + RESET for line in lines]


def field(label, value):
    return "%s%s%s%s%s" % (BLUE, label.ljust(16), TEXT, value, RESET)


def stack_summary(languages_sorted, limit=3):
    top = languages_sorted[:limit] if languages_sorted else []
    return ", ".join("%s %.0f%%" % (name, pct) for name, pct in top) or "n/a"


def boot_screen(terminal):
    terminal.toggle_show_cursor(False)
    lines = [
        "Starting Omarchy Session Manager ...",
        "[  %sOK%s  ] Mounted /home/weijun" % (MAUVE, RESET),
        "[  %sOK%s  ] Started AWS credential agent" % (MAUVE, RESET),
        "[  %sOK%s  ] Started k3s homelab cluster" % (MAUVE, RESET),
        "[  %sOK%s  ] Reached target Cloud & Platform Engineering" % (MAUVE, RESET),
    ]
    terminal.gen_text(lines, 1, count=12)
    terminal.gen_text("", 6, count=HOLD_SHORT)


def login_screen(terminal, stamp):
    terminal.clear_frame()
    terminal.toggle_show_cursor(False)
    terminal.gen_text("%sArch Linux (Omarchy) 6.12 (tty1)%s" % (BLUE, RESET), 1, count=HOLD_SHORT)
    terminal.gen_text("omarchy login: ", 3, count=HOLD_SHORT)
    terminal.toggle_show_cursor(True)
    terminal.gen_typing_text(USER.lower().replace("wong-", ""), 3, contin=True)
    terminal.gen_text("", 4, count=HOLD_SHORT)
    terminal.toggle_show_cursor(False)
    terminal.gen_text("Password: ", 4, count=HOLD_SHORT)
    terminal.toggle_show_cursor(True)
    terminal.gen_typing_text("*" * 12, 4, contin=True)
    terminal.toggle_show_cursor(False)
    terminal.gen_text("Last login: %s on tty1" % stamp, 6, count=HOLD_SHORT)


def fetch_panel(terminal, stats, year):
    logo = arch_logo()

    details = [
        "%s weijun@omarchy %s" % (BANNER, RESET),
        "----------------",
        field("OS:", "Arch Linux (Omarchy)"),
        field("Host:", "University of Wollongong"),
        field("Editor:", "Neovim (LazyVim)"),
        field("Cloud:", "AWS"),
        field("Homelab:", "k3s"),
        field("IaC:", "Terraform"),
        field("AI Pair:", "Claude Code"),
        "",
        "%s GitHub Stats %s" % (BANNER, RESET),
        "----------------",
        field("Rank:", stats.user_rank.level),
        field("Stars:", stats.total_stargazers),
        field("Commits (%s):" % year, stats.total_commits_last_year),
        field("Pull Requests:", "%s merged of %s"
              % (stats.total_pull_requests_merged, stats.total_pull_requests_made)),
        field("Contributions:", stats.total_repo_contributions),
        field("Stack:", stack_summary(stats.languages_sorted)),
    ]

    terminal.clear_frame()
    terminal.set_prompt(PROMPT)
    terminal.gen_prompt(1)
    prompt_col = terminal.curr_col
    terminal.clone_frame(HOLD_SHORT * 2)
    terminal.toggle_show_cursor(True)
    terminal.gen_typing_text("fastfetch", 1, contin=True)
    terminal.toggle_show_cursor(False)

    for offset in range(max(len(logo), len(details))):
        art = logo[offset] if offset < len(logo) else ""
        info = details[offset] if offset < len(details) else ""
        gap = " " * max(1, DETAILS_COLUMN - visible_width(art))
        terminal.gen_text("%s%s%s" % (art, gap, info), 3 + offset)

    terminal.gen_text("", 3 + max(len(logo), len(details)), count=HOLD_SHORT)

    terminal.toggle_show_cursor(True)
    terminal.gen_prompt(terminal.curr_row + 2)
    terminal.gen_typing_text(
        "%s# built with Claude Code, shipped with Terraform %s" % (SUB, RESET),
        terminal.curr_row,
        contin=True,
    )
    terminal.gen_text("", terminal.curr_row, count=HOLD_LONG, contin=True)


def main():
    if not os.getenv("GITHUB_TOKEN"):
        sys.exit("GITHUB_TOKEN is required for the stats query")

    now = datetime.now(TIMEZONE)
    year = now.strftime("%Y")
    stamp = now.strftime("%a %b %d %I:%M:%S %p %Z %Y")

    stats = gifos.utils.fetch_github_stats(user_name=USER, ignore_repos=IGNORE_REPOS)

    terminal = gifos.Terminal(WIDTH, HEIGHT, PADDING, PADDING)
    boot_screen(terminal)
    login_screen(terminal, stamp)
    fetch_panel(terminal, stats, year)
    terminal.gen_gif()


if __name__ == "__main__":
    main()
