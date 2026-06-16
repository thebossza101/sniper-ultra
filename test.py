"""
SNIPER ULTRA — TEST MODE (Offline, tanpa MT5)
Gunakan data Binance untuk testing analisis
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
import pandas as pd
import numpy as np
from datetime import datetime

def fetch_binance_ohlcv(symbol="XAUUSDT", interval="1h", limit=100):
    """Fetch OHLCV from Binance (no auth needed)"""
    url = f"https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    resp = requests.get(url, params=params, timeout=15)
    data = resp.json()
    df = pd.DataFrame(data, columns=[
        'time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'qav', 'trades', 'tbbv', 'tbqv', 'ignore'
    ])
    df['time'] = pd.to_datetime(df['time'], unit='ms')
    for col in ['open','high','low','close','volume']:
        df[col] = df[col].astype(float)
    df.attrs['tf'] = interval
    return df[['time','open','high','low','close','volume']]

def fetch_multi_tf():
    """Fetch H1, M15, M5, M1 data from Binance"""
    print("Fetching data from Binance...")
    result = {}
    for tf, limit in [("1h", 200), ("15m", 200), ("5m", 150), ("1m", 100)]:
        try:
            df = fetch_binance_ohlcv("XAUUSDT", tf, limit)
            tf_key = {"1h": "H1", "15m": "M15", "5m": "M5", "1m": "M1"}[tf]
            result[tf_key] = df
            print(f"  [OK] {tf_key}: {len(df)} candles")
        except Exception as e:
            print(f"  [X] {tf}: {e}")
    return result

def run_test():
    print("\n" + "="*55)
    print("  SNIPER ULTRA — TEST MODE (OFFLINE)")
    print("="*55 + "\n")

    # Fetch data
    data_dict = fetch_multi_tf()
    if data_dict.get('H1') is None or data_dict['H1'].empty:
        print("[X] Failed to fetch data. Check internet or try again.")
        return

    current_price = float(data_dict['H1'].iloc[-1]['close'])
    print(f"\nCurrent XAUUSD: ${current_price:.2f}")
    print("-"*55)

    # Run all modules
    from engine.snd import analyze_snd
    from engine.smc import analyze_smc
    from engine.elliot_wave import analyze_elliot
    from engine.fibonacci import analyze_fib
    from engine.liquidity import analyze_liquidity
    from engine.candlestick import analyze_candles
    from engine.triple_screen import analyze_triple_screen
    from engine.confluence import calculate_full_confluence
    from engine.data import calc_atr
    from utils.logger import log

    # Individual module tests
    print("\n[1/7] SnD Analysis...")
    snd = analyze_snd(data_dict['H1'], current_price)
    print(f"  Zones: {len(snd['zones'])} | Buy: {len(snd['buy_zones'])} | Sell: {len(snd['sell_zones'])}")
    print(f"  Zone Status: {snd['zone_status']} | In Zone: {snd['in_zone']}")
    print(f"  MPL: {snd['mpl']} | Score: {snd['score']}/30")

    print("\n[2/7] SMC Analysis...")
    smc = analyze_smc(data_dict['M15'], current_price)
    print(f"  Structure: {smc['structure']['trend']} | BOS: {smc['bos_choch']['bos_detected']}")
    print(f"  AMD: {smc['amd']['phase']} | Score: {smc['score']}/45")
    print(f"  Bull OB: {len(smc['bullish_obs'])} | Bear OB: {len(smc['bearish_obs'])}")
    print(f"  Bull FVG: {len(smc['bullish_fvgs'])} | Bear FVG: {len(smc['bearish_fvgs'])}")

    print("\n[3/7] Elliot Wave...")
    elliot = analyze_elliot(data_dict['H1'])
    print(f"  Detected: {elliot['detected']} | Alignment: {elliot['alignment']}")
    print(f"  Wave: {elliot['wave_count']['in_wave']} | Score: {elliot['score']}/20")

    print("\n[4/7] Fibonacci...")
    fib = analyze_fib(data_dict['M15'])
    print(f"  In OTE: {fib['in_ote']} | Ratio: {fib['current_ratio']:.2%}")
    print(f"  Cluster: {len(fib['cluster'].get('cluster_levels',[]))} | Harmonic: {fib['harmonic']['detected']}")
    print(f"  Score: {fib['score']}/20")

    print("\n[5/7] Liquidity...")
    liq = analyze_liquidity(data_dict['M5'], current_price)
    print(f"  BSL Zones: {len(liq['bsl_zones'])} | SSL Zones: {len(liq['ssl_zones'])}")
    print(f"  Sweep: {liq['has_recent_sweep']} | Inducement: {liq['inducement'].get('detected', False)}")
    print(f"  Score: {liq['score']}/25")

    print("\n[6/7] Candlestick...")
    candle = analyze_candles(data_dict['M1'])
    print(f"  Confirmed: {candle['confirmed']} | Type: {candle['type']}")
    print(f"  Direction: {candle['direction']} | Strength: {candle['strength']}/3")
    print(f"  Reliability: {candle['reliability']}/4")

    print("\n[7/7] Triple Screen...")
    ts = analyze_triple_screen(data_dict)
    print(f"  HTF Impulse: {ts['htf_impulse']['signal']}")
    print(f"  LTF Impulse: {ts['ltf_impulse']['signal']}")
    print(f"  Alignment: {ts['triple_screen']['alignment']}")
    print(f"  RSI HTF: {ts['rsi_htf']} | Score: {ts['score']}/30")

    # Confluence
    print("\n" + "="*55)
    print("  FINAL CONFLUENCE SCORE")
    print("="*55)
    confluence = calculate_full_confluence(data_dict, current_price)
    print(f"\n  TOTAL SCORE: {confluence['total_score']}/200")
    print(f"  Direction: {confluence['direction']}")
    print(f"  Zone: {confluence['zone_status']}")
    print(f"  ATR: ${confluence['atr']:.2f}")
    print(f"\n  GATES: ", end="")
    for k, v in confluence['gates'].items():
        status = "[OK]" if v else "[X]"
        print(f"{status} {k}", end="  ")
    print(f"\n\n  RECOMMENDATION: {confluence['recommendation']}")

    if confluence['entry_signal']:
        es = confluence['entry_signal']
        print(f"\n  >>> ENTRY SIGNAL: {es['direction']} @ ${es['price']:.2f}")
        print(f"      Pattern: {es['candle_pattern']} | Reliability: {es['reliability']}")

    # Save report
    report = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'price': current_price,
        'score': confluence['total_score'],
        'direction': confluence['direction'],
        'zone': confluence['zone_status'],
        'gates': confluence['gates'],
        'recommendation': confluence['recommendation'],
        'modules': {
            'snd': snd['score'], 'smc': smc['score'],
            'elliot': elliot['score'], 'fib': fib['score'],
            'liquidity': liq['score'], 'candlestick': candle['strength']*10 if candle['confirmed'] else 0,
            'triple_screen': ts['score'],
        }
    }
    with open('test_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\n  Report saved: test_report.json")
    print("="*55 + "\n")

if __name__ == "__main__":
    run_test()
