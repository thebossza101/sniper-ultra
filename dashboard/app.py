"""
SNIPER ULTRA — Dashboard Flask App
Dual mode: Local (state.json) or VPS (POST from bot)
"""
import os
import sys
import json
import glob
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# ─── VPS MODE: In-memory state (received from bot via POST) ───
_vps_state = {'bot_running': False}
_vps_logs = []
_vps_trades = []


def load_state():
    """Load state: VPS mode uses memory, local mode uses state.json"""
    if _vps_state.get('_vps_mode'):
        return {k: v for k, v in _vps_state.items() if not k.startswith('_')}
    state_file = os.path.join(BASE_DIR, 'state.json')
    if os.path.exists(state_file):
        try:
            with open(state_file) as f:
                return json.load(f)
        except:
            pass
    return {}


def load_db_stats():
    """Load trade stats: VPS mode from memory, local from SQLite"""
    if _vps_state.get('_vps_mode') and _vps_trades:
        total = len(_vps_trades)
        wins = sum(1 for t in _vps_trades if t.get('result') == 'WIN')
        losses = sum(1 for t in _vps_trades if t.get('result') == 'LOSS')
        total_pnl = sum(t.get('net_pnl', 0) for t in _vps_trades)
        return {
            'total_trades': total,
            'wins': wins, 'losses': losses,
            'total_pnl': round(total_pnl, 2),
            'winrate': round(wins / total * 100, 1) if total > 0 else 0,
            'history': _vps_trades[-20:],
        }

    # Local mode: read from SQLite
    db_path = os.path.join(BASE_DIR, 'trades.db')
    if not os.path.exists(db_path):
        return {'total_trades': 0, 'wins': 0, 'losses': 0, 'total_pnl': 0}

    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END) as wins,
               SUM(CASE WHEN result='LOSS' THEN 1 ELSE 0 END) as losses,
               COALESCE(SUM(net_pnl), 0) as total_pnl
        FROM trades WHERE result IS NOT NULL
    """).fetchone()
    recent = conn.execute("""
        SELECT * FROM trades WHERE result IS NOT NULL 
        ORDER BY entry_time DESC LIMIT 20
    """).fetchall()
    conn.close()
    return {
        'total_trades': row['total'] or 0,
        'wins': row['wins'] or 0,
        'losses': row['losses'] or 0,
        'total_pnl': round(row['total_pnl'] or 0, 2),
        'winrate': round(row['wins'] / row['total'] * 100, 1) if row['total'] > 0 else 0,
        'history': [dict(r) for r in recent],
    }


# ─── API ROUTES ───

@app.route('/')
def dashboard():
    return render_template('dashboard.html')


@app.route('/api/all')
def api_all():
    state = load_state()
    stats = load_db_stats()
    logs = _vps_logs[-50:] if _vps_state.get('_vps_mode') else []
    return jsonify({
        'state': state,
        'stats': stats,
        'logs': logs,
        'timestamp': datetime.now().strftime('%H:%M:%S'),
    })


# ─── VPS POST ENDPOINTS ───

@app.route('/api/update', methods=['POST'])
def api_update():
    """Receive bot state from Windows bot"""
    data = request.get_json(force=True, silent=True)
    if data:
        data['_vps_mode'] = True
        data['last_seen'] = datetime.now().strftime('%H:%M:%S')
        _vps_state.clear()
        _vps_state.update(data)
        # Also save to state.json for persistence
        save_data = {k: v for k, v in data.items() if not k.startswith('_')}
        try:
            with open(os.path.join(BASE_DIR, 'state.json'), 'w') as f:
                json.dump(save_data, f, indent=2)
        except:
            pass
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'error', 'message': 'no data'}), 400


@app.route('/api/log', methods=['POST'])
def api_log():
    """Receive log line from bot"""
    data = request.get_json(force=True, silent=True)
    if data:
        msg = f"{data.get('timestamp','')}|{data.get('level','')}|{data.get('message','')}"
        _vps_logs.append(msg)
        if len(_vps_logs) > 500:
            _vps_logs[:100] = []  # Trim
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'error'}), 400


@app.route('/api/trade', methods=['POST'])
def api_trade():
    """Receive trade record from bot"""
    data = request.get_json(force=True, silent=True)
    if data:
        _vps_trades.append(data)
        if len(_vps_trades) > 200:
            _vps_trades[:50] = []
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'error'}), 400


# ─── HELPERS ───

def start_vps():
    """Mark as VPS mode and start"""
    _vps_state['_vps_mode'] = True
    print("[VPS] Dashboard menunggu data dari bot...")
    print("[VPS] Buka http://43.228.214.239:5000 dari HP atau browser")


if __name__ == '__main__':
    # Parse args: optional port, --vps flag
    port = 5000
    for arg in sys.argv[1:]:
        if arg == '--vps':
            start_vps()
        else:
            try:
                port = int(arg)
            except ValueError:
                pass

    print(f"[DASHBOARD] http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
