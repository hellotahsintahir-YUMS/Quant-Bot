"""
============================================
📋 PER-USER WATCHLIST STORAGE
============================================
Each user's custom watchlist is saved in data/watchlists.json
"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
WATCHLISTS_FILE = DATA_DIR / "watchlists.json"
PLANS_FILE = DATA_DIR / "plans.json"

# Default 20 stocks shown to every new user
DEFAULT_WATCHLIST = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",   # Tech
    "TSLA", "META", "AMD", "INTC", "DIS",      # Tech/Media
    "JPM", "BAC", "V", "MA",                   # Finance
    "JNJ", "UNH",                              # Healthcare
    "WMT", "KO", "MCD", "NFLX"                 # Consumer
]


def _load_all():
    if not WATCHLISTS_FILE.exists():
        return {}
    try:
        with open(WATCHLISTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_all(all_lists):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(WATCHLISTS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_lists, f, indent=2)


def get_watchlist(email):
    """Get a user's watchlist (or the default 20)"""
    return _load_all().get(email, list(DEFAULT_WATCHLIST))


def save_watchlist(email, tickers):
    """Save a user's watchlist"""
    all_lists = _load_all()
    all_lists[email] = tickers
    _save_all(all_lists)


def _load_plans():
    if not PLANS_FILE.exists():
        return {}
    try:
        with open(PLANS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def get_plan(email):
    """Get a user's saved investment plan."""
    return _load_plans().get(email, {})


def save_plan(email, plan):
    """Save a user's investment plan."""
    plans = _load_plans()
    plans[email] = plan
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PLANS_FILE, "w", encoding="utf-8") as f:
        json.dump(plans, f, indent=2)