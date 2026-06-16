"""
SNIPER ULTRA — VPS Data Sender
Kirim data bot real-time dari Windows ke VPS dashboard
"""
import requests
import json
import threading
import time

VPS_URL = "http://43.228.214.239:5000"

# Thread-safe cache of last sent data
_last_sent = {}
_last_send_time = 0


def send_state(confluence, session, info, bot_running=True):
    """Send bot state to VPS dashboard (non-blocking)"""
    global _last_sent, _last_send_time

    now = time.time()
    if now - _last_send_time < 1.5:
        return False  # Rate limit: max every 1.5s
    _last_send_time = now

    # Build state dict (same format as bot.py write_state)
    b = confluence['breakdown']
    state = {
        'bot_running': bot_running,
        'timestamp': __import__('datetime').datetime.now().strftime('%H:%M:%S'),
        'current_price': info['bid'] if info else 0,
        'spread': info['spread'] if info else 0,
        'session': session,
        'atr': confluence.get('atr', 0),
        'total_score': confluence['total_score'],
        'direction': confluence['direction'],
        'zone_status': confluence['zone_status'],
        'recommendation': confluence['recommendation'],
        'open_positions': 0,
        'candle': confluence.get('candle', {}),
        'alignment': confluence.get('alignment', {'bull': 0, 'bear': 0}),
        'breakdown': {
            'snd': {'score': b['snd']['score'], 'max': 30},
            'smc': {'score': b['smc']['score'], 'max': 45},
            'elliot': {'score': b['elliot']['score'], 'max': 20},
            'fib': {'score': b['fib']['score'], 'max': 20},
            'liquidity': {'score': b['liquidity']['score'], 'max': 25},
            'candlestick': {
                'score': b['candlestick']['score'], 'max': 30,
                'confirmed': b['candlestick']['confirmed'],
                'type': b['candlestick']['type'],
                'strength': b['candlestick']['strength'],
            },
            'triple_screen': {
                'score': b['triple_screen']['score'], 'max': 30,
                'htf_impulse': b['triple_screen']['htf_impulse'],
                'ltf_impulse': b['triple_screen']['ltf_impulse'],
            },
        },
    }

    _last_sent = state

    # Send in background thread (non-blocking)
    def _do_send():
        try:
            requests.post(f"{VPS_URL}/api/update", json=state, timeout=3)
        except:
            pass  # VPS offline? No problem, next cycle will try again

    threading.Thread(target=_do_send, daemon=True).start()
    return True


def send_log(level, message):
    """Send a single log line to VPS"""
    def _do_send():
        try:
            requests.post(f"{VPS_URL}/api/log", json={
                'level': level,
                'message': str(message),
                'timestamp': __import__('datetime').datetime.now().strftime('%H:%M:%S'),
            }, timeout=2)
        except:
            pass
    threading.Thread(target=_do_send, daemon=True).start()


def send_trade(trade_data):
    """Send trade data to VPS"""
    def _do_send():
        try:
            requests.post(f"{VPS_URL}/api/trade", json=trade_data, timeout=2)
        except:
            pass
    threading.Thread(target=_do_send, daemon=True).start()
