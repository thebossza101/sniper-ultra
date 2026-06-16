"""
SNIPER ULTRA — Main Trading Bot
Exness XAUUSD | 1:2000 | All Modules Active | Telegram Notif
"""
import time
import sys
import os
import json
import MetaTrader5 as mt5
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    SYMBOL, SERVER as CFG_SERVER, LOGIN as CFG_LOGIN, MAGIC,
    SESSION_LONDON_START, SESSION_LONDON_END,
    SESSION_NY_START, SESSION_NY_END,
    ACCOUNT_BALANCE,
)
from engine.data import (
    mt5_connect, mt5_disconnect, get_multi_tf_data, get_symbol_info,
    get_open_positions, get_account_info, check_mt5_health
)
from engine.confluence import calculate_full_confluence
from trading.entry import execute_trade
from trading.trailing import manage_smart_trailing
from trading.risk import check_daily_limits
from trading.learning import init_db, log_trade_open, log_trade_close, analyze_performance, get_optimization_suggestions
from utils.logger import log


# ─── CREDENTIAL LOADER ───
def load_credentials():
    """Load credentials from credentials.json or env"""
    cred_file = os.path.join(os.path.dirname(__file__), 'credentials.json')
    if os.path.exists(cred_file):
        try:
            with open(cred_file) as f:
                cfg = json.load(f)
            return cfg
        except:
            pass
    return {}


def get_session():
    now = datetime.now(timezone.utc)
    t = now.time()
    if SESSION_LONDON_START <= t <= SESSION_LONDON_END:
        if SESSION_NY_START <= t <= SESSION_NY_END:
            return "NY_LONDON"
        return "LONDON"
    elif SESSION_NY_START <= t <= SESSION_NY_END:
        return "NY"
    return "ASIAN"


def print_analysis(confluence, session):
    b = confluence['breakdown']
    cdl = confluence['candle']
    al = confluence['alignment']

    print(f"\n{'='*55}")
    print(f"SNIPER ULTRA - {session}")
    print(f"{'='*55}")

    # CANDLE STATUS
    cdl_icon = '✅' if cdl['ok'] else '❌'
    print(f"CANDLE: {cdl_icon} {cdl['type']}({cdl['strength']}/3) {cdl['direction']}")

    # ALIGNMENT
    bull_bar = '#' * min(al['bull'], 10)
    bear_bar = '#' * min(al['bear'], 10)
    print(f"ALIGN: BUY [{bull_bar:<10}] {al['bull']}  SELL [{bear_bar:<10}] {al['bear']}")
    print(f"       >> {confluence['direction']}")

    # ZONE + ATR
    print(f"ZONE: {confluence['zone_status']} | ATR: ${confluence['atr']:.2f}")

    # Modul score 1 baris
    print(f"  SnD:{b['snd']['score']} SMC:{b['smc']['score']} Eli:{b['elliot']['score']} "
          f"Fib:{b['fib']['score']} Liq:{b['liq']['score']} "
          f"TS:{b['ts']['htf']}/{b['ts']['ltf']}")

    # KEPUTUSAN
    if confluence['recommendation'] == 'ENTRY':
        print(f"  >>> ENTRY {confluence['direction']}!")
    elif confluence['recommendation'] == 'NO_CANDLE':
        print(f"  >>> TUNGGU candle confirmation di M1...")
    elif confluence['recommendation'] == 'MISALIGNED':
        print(f"  >>> Candle {cdl['direction']} tapi mayoritas {confluence['direction']} - SKIP")
    else:
        print(f"  >>> WAIT...")


def write_state(confluence, session, info, bot_running=True):
    """Write real-time state for web dashboard"""
    b = confluence['breakdown']
    cdl = confluence['candle']
    al = confluence['alignment']
    state = {
        'bot_running': bot_running,
        'timestamp': datetime.now(timezone.utc).strftime('%H:%M:%S'),
        'current_price': info['bid'] if info else 0,
        'spread': info['spread'] if info else 0,
        'session': session,
        'atr': confluence.get('atr', 0),
        'direction': confluence['direction'],
        'zone_status': confluence['zone_status'],
        'recommendation': confluence['recommendation'],
        'candle': {'ok': cdl['ok'], 'type': cdl['type'], 'strength': cdl['strength'], 'direction': cdl['direction']},
        'alignment': {'bull': al['bull'], 'bear': al['bear']},
        'breakdown': {
            'snd': {'score': b['snd']['score'], 'max': 30},
            'smc': {'score': b['smc']['score'], 'max': 45},
            'elliot': {'score': b['elliot']['score'], 'max': 20},
            'fib': {'score': b['fib']['score'], 'max': 20},
            'liquidity': {'score': b['liquidity']['score'], 'max': 25},
            'candlestick': {
                'score': b['candlestick']['score'],
                'max': 30,
                'confirmed': b['candlestick']['confirmed'],
                'type': b['candlestick']['type'],
                'strength': b['candlestick']['strength'],
            },
            'triple_screen': {
                'score': b['triple_screen']['score'],
                'max': 30,
                'htf_impulse': b['triple_screen']['htf_impulse'],
                'ltf_impulse': b['triple_screen']['ltf_impulse'],
            },
        },
    }
    try:
        state_path = os.path.join(os.path.dirname(__file__), 'state.json')
        with open(state_path, 'w') as f:
            json.dump(state, f, indent=2)
    except:
        pass


def check_symbols():
    """Print available symbols for debugging"""
    if not mt5.initialize():
        print(f"MT5 init failed: {mt5.last_error()}")
        return
    symbols = mt5.symbols_get()
    gold = [s.name for s in symbols if 'xau' in s.name.lower()]
    print(f"Total symbols: {len(symbols)}")
    print(f"Gold symbols: {gold}")
    for g in gold:
        info = mt5.symbol_info(g)
        if info:
            print(f"  {g}: spread={info.spread} digits={info.digits} contract={info.trade_contract_size}")
    mt5.shutdown()


def print_report(days=30):
    """Print performance report"""
    analysis = analyze_performance(days)
    if analysis['total_trades'] == 0:
        print("No trades found in the last {} days.".format(days))
        return
    print(f"\n{'='*50}")
    print(f"PERFORMANCE REPORT (last {days} days)")
    print(f"{'='*50}")
    print(f"Total Trades: {analysis['total_trades']}")
    print(f"Wins: {analysis['wins']} | Losses: {analysis['losses']} | BE: {analysis['be']}")
    print(f"Winrate: {analysis['winrate']}%")
    print(f"Total PnL: ${analysis['total_pnl']}")
    print(f"Profit Factor: {analysis['profit_factor']}")
    print(f"Max Consecutive Losses: {analysis['max_consecutive_losses']}")
    print(f"\nSuggestions:")
    for s in get_optimization_suggestions(analysis):
        print(f"  -> {s}")


def main():
    log.info("=" * 50)
    log.info("SNIPER ULTRA v1.0 - STARTING")
    log.info(f"Symbol: {SYMBOL} | Balance: ${ACCOUNT_BALANCE} | Leverage: 1:2000")
    log.info("=" * 50)

    # ─── CLI COMMANDS ───
    if '--check-symbols' in sys.argv:
        check_symbols()
        return
    if '--report' in sys.argv:
        init_db()
        days = 30
        if len(sys.argv) > sys.argv.index('--report') + 1:
            try:
                days = int(sys.argv[sys.argv.index('--report') + 1])
            except:
                pass
        print_report(days)
        return

    # ─── LOAD CREDENTIALS ───
    creds = load_credentials()
    login = int(creds.get('login', CFG_LOGIN))
    password = creds.get('password', '')
    server = creds.get('server', CFG_SERVER)

    # Override from CLI args
    if '--login' in sys.argv:
        try:
            idx = sys.argv.index('--login')
            login = int(sys.argv[idx + 1])
            password = sys.argv[sys.argv.index('--pass') + 1]
            server = sys.argv[sys.argv.index('--server') + 1] if '--server' in sys.argv else server
        except (IndexError, ValueError):
            log.error("Usage: python bot.py --login 123456 --pass PASS --server Exness-MT5Trial14")
            return

    if not password:
        log.error("No credentials found! Buat credentials.json atau pake --login --pass --server")
        log.info("Contoh: python bot.py --login 12345678 --pass PASSWORD --server Exness-MT5Trial14")
        return

    # ─── CONNECT MT5 ───
    ok, msg = mt5_connect(login, password, server)
    if not ok:
        log.error(f"MT5|{msg}")
        return
    log.info(f"MT5|{msg}")

    # ─── VPS MODE ───
    vps_mode = '--vps' in sys.argv
    vps_sender_available = False
    if vps_mode:
        try:
            from utils.vps_sender import send_state, send_log
            vps_sender_available = True
            log.info("VPS|Dashboard mode AKTIF. Data dikirim ke http://43.228.214.239:5000")
        except ImportError as e:
            log.warn(f"VPS|GAGAL! Install requests dulu: pip install requests")
            log.warn(f"VPS|Error: {e}")
        except Exception as e:
            log.warn(f"VPS|Error: {e}")
    else:
        log.info("VPS|Dashboard mode NONAKTIF. Gunakan --vps untuk kirim data ke dashboard")
        log.info("VPS|Contoh: python bot.py --login ... --pass ... --server ... --vps")

    # ─── INIT ───
    init_db()
    from utils.notifier import send_msg, signal_alert, entry_alert, close_alert, error_alert
    send_msg(f"<b>SNIPER ULTRA STARTED</b>\n{server} | {SYMBOL} | $500")

    daily_state = {
        'daily_pnl': 0.0, 'daily_losses': 0,
        'consecutive_losses': 0, 'trades_today': 0,
        'last_analysis_time': 0, 'analysis_cache': None,
        'last_entry_prices': {},  # ticket -> entry_price tracking
    }

    # ─── MAIN LOOP ───
    loop_count = 0
    last_trail_time = 0
    last_tg_time = 0
    last_signal_tg = ''  # Avoid spam same signal

    try:
        while True:
            loop_count += 1
            now = time.time()

            # MT5 health
            if not check_mt5_health():
                log.warn("MT5|Reconnecting...")
                send_msg("<b>⚠️ MT5 Disconnected</b> - Reconnecting...")
                mt5_disconnect()
                time.sleep(5)
                continue

            session = get_session()
            info = get_symbol_info()

            if info:
                log.info(f"[{loop_count}] Price: {info['bid']:.2f}/{info['ask']:.2f} | Spread: {info['spread']} | Session: {session}")

            # 1. Fetch data
            data_dict = get_multi_tf_data()
            if (data_dict.get('H1') is None or data_dict['H1'].empty) and \
               (data_dict.get('M15') is None or data_dict['M15'].empty):
                time.sleep(10)
                continue

            # Get current price safely
            m1_data = data_dict.get('M1')
            m15_data = data_dict.get('M15')
            price_df = None
            if m1_data is not None and not m1_data.empty:
                price_df = m1_data
            elif m15_data is not None and not m15_data.empty:
                price_df = m15_data

            if price_df is None:
                time.sleep(5)
                continue

            current_price = float(price_df.iloc[-1]['close'])

            # 2. Confluence
            confluence = calculate_full_confluence(data_dict, current_price)
            daily_state['analysis_cache'] = confluence

            # 2b. Write state for dashboard (every cycle)
            write_state(confluence, session, info, bot_running=True)
            daily_state['open_positions'] = len([p for p in (get_open_positions() or []) if p.magic == MAGIC])

            # 2c. VPS mode: send data to cloud dashboard
            if vps_mode and vps_sender_available:
                try:
                    send_state(confluence, session, info, bot_running=True)
                except Exception as e:
                    if loop_count % 30 == 0:  # Log error every 30 loops
                        log.warn(f"VPS|Send error: {e}")

            # 3. Print every 10 loops or on ENTRY/NO_CANDLE
            if loop_count % 10 == 0 or confluence['recommendation'] in ('ENTRY', 'NO_CANDLE'):
                print_analysis(confluence, session)

            # TG signal notification (max every 60s, avoid spam)
            if confluence['recommendation'] == 'ENTRY' and now - last_tg_time > 60:
                signal_key = f"{confluence['direction']}_{confluence['total_score']}"
                if signal_key != last_signal_tg:
                    send_msg(signal_alert(confluence))
                    last_signal_tg = signal_key
                    last_tg_time = now

            # 4. Execute trade
            positions = get_open_positions()
            bot_positions = [p for p in positions if p.magic == MAGIC]
            active_count = len(bot_positions)

            if active_count < 2 and confluence['recommendation'] == 'ENTRY':
                result = execute_trade(confluence, data_dict, daily_state)
                if result['executed']:
                    log.info(f"TRADE|[OK] Ticket {result['ticket']} opened")
                    daily_state['last_entry_prices'][result['ticket']] = result['price']

                    log_trade_open(
                        result['ticket'], confluence['direction'],
                        result['price'], result['sl'], result['tp'],
                        result['lot'], confluence['total_score'],
                        confluence['zone_status'],
                        confluence['breakdown']['candlestick']['type'],
                        confluence['breakdown']['triple_screen']['htf_impulse'],
                        confluence['atr'], info['spread'] if info else 0, session
                    )

                    send_msg(entry_alert(result, confluence['direction']))
                    last_tg_time = now
                else:
                    log.warn(f"TRADE|[X] {result['error']}")

            # 5. Check closed positions
            for pos in bot_positions:
                ticket = pos.ticket
                # Check if position still in MT5 but PnL changed significantly -> closed
                # We use a simple check: if position was tracked but now gone, check via history
                if ticket not in daily_state['last_entry_prices']:
                    daily_state['last_entry_prices'][ticket] = pos.price_open

            # 6. Trailing
            if now - last_trail_time > 5:
                modified = manage_smart_trailing(data_dict)
                if modified > 0:
                    log.info(f"TRAIL|{modified} positions updated")
                last_trail_time = now

            # 7. Check MT5 history for closed positions (every 20 loops)
            if loop_count % 20 == 0:
                try:
                    from datetime import timedelta
                    history = mt5.history_deals_get(
                        datetime.now(timezone.utc) - timedelta(hours=2),
                        datetime.now(timezone.utc)
                    )
                    if history:
                        recent = [d for d in history if d.magic == MAGIC and d.comment.startswith("SU_")]
                        for deal in recent:
                            if deal.deal_type == 1 and deal.profit != 0:  # DEAL_TYPE_SELL (close BUY)
                                result_type = log_trade_close(
                                    deal.position_id, deal.price, deal.profit, 'TP/SL'
                                )
                                entry_p = daily_state['last_entry_prices'].get(deal.position_id, 0)
                                direction = 'BUY' if deal.type == 1 else 'SELL'

                                # Update daily state
                                daily_state['daily_pnl'] += deal.profit
                                if deal.profit < 0:
                                    daily_state['daily_losses'] += 1
                                    daily_state['consecutive_losses'] += 1
                                else:
                                    daily_state['consecutive_losses'] = 0

                                # Clean up tracking
                                daily_state['last_entry_prices'].pop(deal.position_id, None)

                                # TG notification
                                send_msg(close_alert(
                                    deal.position_id, direction,
                                    entry_p, deal.price, deal.profit, result_type
                                ))
                                log.info(f"CLOSE|Ticket {deal.position_id}: ${deal.profit:.2f} ({result_type})")

                                # Check circuit breaker
                                limits = check_daily_limits(
                                    daily_state['daily_pnl'],
                                    daily_state['daily_losses'],
                                    daily_state['consecutive_losses'],
                                )
                                if not limits['can_trade']:
                                    log.warn(f"CIRCUIT|{limits['reason']}")
                                    send_msg(f"<b>⛔ CIRCUIT BREAKER</b>\n{limits['reason']}")

                except Exception as e:
                    log.warn(f"HISTORY|Check error: {e}")

            # 8. Periodic performance (every 100 loops)
            if loop_count % 100 == 0:
                analysis = analyze_performance(days=7)
                if analysis['total_trades'] >= 3:
                    log.info(f"PERF|{analysis['total_trades']} trades | WR: {analysis['winrate']}% | PnL: ${analysis['total_pnl']}")
                    for s in get_optimization_suggestions(analysis):
                        log.info(f"OPTIM|{s}")

                # TG daily report every 500 loops (~15 min)
                if loop_count % 500 == 0:
                    from utils.notifier import daily_report as dr
                    stats = {
                        'trades_today': daily_state['trades_today'],
                        'daily_pnl': daily_state['daily_pnl'],
                        'winrate': analysis.get('winrate', 0) if analysis['total_trades'] > 0 else 0,
                    }
                    send_msg(dr(stats))

            time.sleep(2)

    except KeyboardInterrupt:
        log.info("Bot stopped by user")
        send_msg("<b>🛑 SNIPER ULTRA STOPPED</b>")
    except Exception as e:
        log.error(f"Bot crashed: {e}")
        import traceback
        traceback.print_exc()
        try:
            send_msg(f"<b>⚠️ BOT CRASH</b>\n{e}")
            # Update dashboard state
            with open(os.path.join(os.path.dirname(__file__), 'state.json'), 'w') as f:
                json.dump({'bot_running': False, 'error': str(e)}, f)
        except:
            pass
    finally:
        mt5_disconnect()
        log.info("MT5 disconnected")


if __name__ == "__main__":
    main()
