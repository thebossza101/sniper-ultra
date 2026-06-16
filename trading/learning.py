"""
SNIPER ULTRA — Self-Learning Engine (Trade History + Performance Analysis)
"""
import sqlite3
import json
import os
from datetime import datetime, timezone
from config import LEARNING_DB, LEARNING_ANALYZE_EVERY
from utils.logger import log


def get_db_path():
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), LEARNING_DB)


def init_db():
    """Create trade database if not exists"""
    db = get_db_path()
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket INTEGER UNIQUE,
            entry_time TEXT,
            exit_time TEXT,
            direction TEXT,
            entry_price REAL,
            exit_price REAL,
            sl REAL,
            tp REAL,
            lot REAL,
            net_pnl REAL,
            result TEXT,
            score INTEGER,
            zone_status TEXT,
            candle_pattern TEXT,
            htf_impulse TEXT,
            entry_reason TEXT,
            exit_reason TEXT,
            atr REAL,
            spread INTEGER,
            session TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_stats (
            date TEXT PRIMARY KEY,
            trades INTEGER,
            wins INTEGER,
            losses INTEGER,
            net_pnl REAL,
            max_drawdown REAL
        )
    """)
    conn.commit()
    conn.close()


def log_trade_close(ticket, exit_price, net_pnl, exit_reason):
    """Update trade record on close"""
    db = get_db_path()
    conn = sqlite3.connect(db)
    result = 'WIN' if net_pnl > 0 else 'LOSS' if net_pnl < 0 else 'BE'
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    conn.execute("""
        UPDATE trades SET
            exit_time=?, exit_price=?, net_pnl=?, result=?, exit_reason=?
        WHERE ticket=?
    """, (now, exit_price, net_pnl, result, exit_reason, ticket))
    conn.commit()

    # Update daily stats
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    conn.execute("""
        INSERT INTO daily_stats (date, trades, wins, losses, net_pnl)
        VALUES (?, 1, ?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET
            trades = trades + 1,
            wins = wins + excluded.wins,
            losses = losses + excluded.losses,
            net_pnl = net_pnl + excluded.net_pnl
    """, (today, 1 if net_pnl > 0 else 0, 1 if net_pnl < 0 else 0, net_pnl))
    conn.commit()

    conn.close()
    return result


def log_trade_open(ticket, direction, entry_price, sl, tp, lot, score, zone_status,
                   candle_pattern, htf_impulse, atr, spread, session):
    """Record new trade"""
    db = get_db_path()
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    conn = sqlite3.connect(db)
    conn.execute("""
        INSERT OR IGNORE INTO trades 
        (ticket, entry_time, direction, entry_price, sl, tp, lot, score,
         zone_status, candle_pattern, htf_impulse, atr, spread, session)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (ticket, now, direction, entry_price, sl, tp, lot, score,
          zone_status, candle_pattern, htf_impulse, atr, spread, session))
    conn.commit()
    conn.close()


def analyze_performance(days=7):
    """Analyze trade performance and return insights"""
    db = get_db_path()
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row

    from datetime import datetime, timedelta
    cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')

    rows = conn.execute("""
        SELECT * FROM trades 
        WHERE exit_time IS NOT NULL
        AND entry_time >= ?
        ORDER BY entry_time DESC
    """, (cutoff,)).fetchall()

    if not rows:
        conn.close()
        return {'total_trades': 0, 'message': 'No trades found'}

    total = len(rows)
    wins = sum(1 for r in rows if r['result'] == 'WIN')
    losses = sum(1 for r in rows if r['result'] == 'LOSS')
    be = sum(1 for r in rows if r['result'] == 'BE')

    winrate = wins / total * 100 if total > 0 else 0
    total_pnl = sum(r['net_pnl'] for r in rows if r['net_pnl'] is not None)
    avg_win = sum(r['net_pnl'] for r in rows if r['result'] == 'WIN') / wins if wins > 0 else 0
    avg_loss = sum(r['net_pnl'] for r in rows if r['result'] == 'LOSS') / losses if losses > 0 else 0

    # Performance by setup type
    setup_perf = {}
    for r in rows:
        pattern = r['candle_pattern'] or 'UNKNOWN'
        if pattern not in setup_perf:
            setup_perf[pattern] = {'wins': 0, 'losses': 0, 'pnl': 0}
        if r['result'] == 'WIN':
            setup_perf[pattern]['wins'] += 1
        elif r['result'] == 'LOSS':
            setup_perf[pattern]['losses'] += 1
        if r['net_pnl']:
            setup_perf[pattern]['pnl'] += r['net_pnl']

    # Performance by session
    session_perf = {}
    for r in rows:
        sess = r['session'] or 'UNKNOWN'
        if sess not in session_perf:
            session_perf[sess] = {'wins': 0, 'losses': 0, 'pnl': 0}
        if r['result'] == 'WIN':
            session_perf[sess]['wins'] += 1
        elif r['result'] == 'LOSS':
            session_perf[sess]['losses'] += 1
        if r['net_pnl']:
            session_perf[sess]['pnl'] += r['net_pnl']

    # Consecutive losses
    results_list = [r['result'] for r in rows if r['result'] in ('WIN', 'LOSS')]
    max_consec_losses = 0
    current = 0
    for res in results_list:
        if res == 'LOSS':
            current += 1
            max_consec_losses = max(max_consec_losses, current)
        else:
            current = 0

    # Best/worst entry score range
    score_ranges = {}
    for r in rows:
        s = (r['score'] or 0) // 20 * 20
        key = f"{s}-{s+20}"
        if key not in score_ranges:
            score_ranges[key] = {'wins': 0, 'losses': 0}
        if r['result'] == 'WIN':
            score_ranges[key]['wins'] += 1
        elif r['result'] == 'LOSS':
            score_ranges[key]['losses'] += 1

    conn.close()

    return {
        'total_trades': total,
        'wins': wins,
        'losses': losses,
        'be': be,
        'winrate': round(winrate, 1),
        'total_pnl': round(total_pnl, 2),
        'avg_win': round(avg_win, 2),
        'avg_loss': round(avg_loss, 2),
        'profit_factor': round(abs(avg_win * wins / (avg_loss * losses)), 2) if avg_loss * losses > 0 else 0,
        'max_consecutive_losses': max_consec_losses,
        'setup_performance': setup_perf,
        'session_performance': session_perf,
        'score_range_performance': score_ranges,
    }


def get_optimization_suggestions(analysis):
    """Generate optimization suggestions based on performance"""
    suggestions = []

    if analysis['total_trades'] < 10:
        return ['Not enough data (min 10 trades for analysis)']

    if analysis['winrate'] < 40:
        suggestions.append("Winrate below 40%: Increase SCORE_MIN or require higher candlestick reliability")

    if analysis['max_consecutive_losses'] >= 4:
        suggestions.append(f"High consecutive losses ({analysis['max_consecutive_losses']}): Reduce CIRCUIT_BREAKER_LOSSES")

    # Check session performance
    for session, perf in analysis.get('session_performance', {}).items():
        total = perf['wins'] + perf['losses']
        if total >= 5:
            wr = perf['wins'] / total * 100
            if wr < 30:
                suggestions.append(f"Poor performance in {session} ({wr:.0f}%): Consider skipping this session")

    # Check setup performance
    for setup, perf in analysis.get('setup_performance', {}).items():
        total = perf['wins'] + perf['losses']
        if total >= 5:
            wr = perf['wins'] / total * 100
            if wr > 70:
                suggestions.append(f"Strong setup: {setup} ({wr:.0f}% winrate) - Boost weight")
            elif wr < 30:
                suggestions.append(f"Weak setup: {setup} ({wr:.0f}% winrate) - Reduce weight or ignore")

    return suggestions if suggestions else ['Performance looks healthy. No changes needed.']
