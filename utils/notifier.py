"""
SNIPER ULTRA — Notifikasi Telegram
Kirim alert signal, entry, close, error real-time
"""
import requests
import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials.json')

# Default disabled (set via credentials.json)
BOT_TOKEN = None
CHAT_ID = None

def load_config():
    """Load Telegram config from credentials.json"""
    global BOT_TOKEN, CHAT_ID
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE) as f:
                cfg = json.load(f)
            BOT_TOKEN = cfg.get('telegram_bot_token')
            CHAT_ID = cfg.get('telegram_chat_id')
            return BOT_TOKEN and CHAT_ID
    except:
        pass
    return False

def send_msg(text, parse_mode='HTML'):
    """Send message to Telegram"""
    if not BOT_TOKEN or not CHAT_ID:
        if not load_config():
            return False

    # ASCII-safe
    safe_text = text.encode('ascii', 'replace').decode('ascii')

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, json={
            'chat_id': CHAT_ID,
            'text': safe_text,
            'parse_mode': parse_mode,
        }, timeout=10)
        return resp.status_code == 200
    except:
        return False

# ─── FORMATTERS ───

def signal_alert(confluence):
    """Format signal detection"""
    b = confluence['breakdown']
    lines = [
        "<b>🔍 SIGNAL DETECTED</b>",
        f"Score: {confluence['total_score']}/200 | {confluence['direction']}",
        f"Zone: {confluence['zone_status']} | ATR: ${confluence['atr']:.2f}",
        f"",
        f"<b>Modules:</b>",
        f"SnD: {b['snd']['score']}/30 | SMC: {b['smc']['score']}/45",
        f"Cdl: {b['cdl']['type']}({b['cdl']['str']}/3)",
        f"TS: {b['ts']['htf']}/{b['ts']['ltf']}",
        f"",
        f"<b>Recommendation: {confluence['recommendation']}</b>",
    ]
    return '\\n'.join(lines)

def entry_alert(result, direction):
    """Format trade entry"""
    lines = [
        "<b>✅ ORDER EXECUTED</b>",
        f"{direction} {result['lot']} lot @ ${result['price']:.2f}",
        f"SL: ${result['sl']:.2f} | TP: ${result['tp']:.2f}",
        f"Ticket: {result['ticket']}",
    ]
    return '\n'.join(lines)

def close_alert(ticket, direction, entry, exit_p, pnl, result_type):
    """Format trade close"""
    emoji = '🟢' if result_type == 'WIN' else '🔴' if result_type == 'LOSS' else '🟡'
    lines = [
        f"<b>{emoji} POSITION CLOSED</b>",
        f"{direction} #{ticket}",
        f"Entry: ${entry:.2f} | Exit: ${exit_p:.2f}",
        f"PnL: <b>${pnl:.2f}</b> ({result_type})",
    ]
    return '\n'.join(lines)

def error_alert(msg):
    """Format error notification"""
    return f"<b>⚠️ BOT ERROR</b>\n{msg}"

def daily_report(stats):
    """Format daily performance"""
    lines = [
        "<b>📊 DAILY REPORT</b>",
        f"Trades: {stats['trades_today']}",
        f"PnL: ${stats['daily_pnl']:.2f}",
        f"Winrate: {stats.get('winrate', 'N/A')}%",
    ]
    return '\n'.join(lines)
