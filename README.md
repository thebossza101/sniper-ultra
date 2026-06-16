# SNIPER ULTRA v1.0

Bot trading forex XAUUSD (Gold) untuk Exness MT5.
**7 modul analisis → Confluence Score 200pt → 4-Gate Entry → Smart Trailing.**

Dibuat berdasarkan framework analisis chart lengkap (SnD, SMC, Elliot Wave, Fibonacci, Liquidity, 89 pola Candlestick, Triple Screen Elder).

---

## 📋 FITUR

| Fitur | Detail |
|-------|--------|
| **Pair** | XAUUSD (Gold) |
| **Broker** | Exness (MT5) |
| **Leverage** | 1:2000 |
| **Modal** | $500 (bisa disesuaikan) |
| **Analisis** | 7 modul: SnD, SMC, Elliot Wave, Fibonacci, Liquidity, Candlestick, Triple Screen |
| **Skor** | Confluence 0-200 (min entry: 120) |
| **Entry** | 4-Gate System (Score + Zone + Confirmation + Strength) |
| **Trailing** | 8-stage, 25% increments |
| **Risk** | 1.5% per trade, circuit breaker, max 2 posisi |
| **Self-Learning** | Otomatis analisis performance tiap 100 trade |
| **Notifikasi** | Telegram (real-time) |

---

## 🚀 CARA INSTALASI (WINDOWS)

### 1. Install Python 3.11+

Download dari [python.org](https://www.python.org/downloads/) — **centang "Add Python to PATH"** pas instalasi.

### 2. Install MetaTrader 5

Download dari [metatrader5.com](https://www.metatrader5.com/) atau website Exness.
- Login pake akun Exness demo/real lo
- Pastikan **AutoTrading** aktif (tombol hijau di toolbar MT5, atau Ctrl+E)
- Cek symbol XAUUSDm ada di Market Watch

### 3. Download SNIPER ULTRA

**Opsi A — Download ZIP dari GitHub:**
```bash
# Atau download langsung dari repo
```
Link: https://github.com/alipun09/hermes/tree/master/sniper-ultra

**Opsi B — Pake git:**
```bash
git clone https://github.com/alipun09/hermes.git
cd hermes/sniper-ultra
```

### 4. Install Dependencies

Buka **PowerShell** atau **Command Prompt** di folder `sniper-ultra/`:

```powershell
pip install MetaTrader5 pandas numpy requests
```

### 5. Setup Credentials

Ada 2 cara:

**CARA 1 — Config file (REKOMENDASI):**
Bikin file `credentials.json`:
```json
{
    "login": 12345678,
    "password": "password_exness_lo",
    "server": "Exness-MT5Trial14",
    "telegram_bot_token": "TOKEN_BOT_TG",
    "telegram_chat_id": "ID_CHAT_TG"
}
```

**CARA 2 — Argumen CLI (cepat):**
Langsung jalanin pake argumen:
```powershell
python bot.py --login 12345678 --pass PASSWORD --server Exness-MT5Trial14
```

### 6. Cek Symbol Name

Exness kadang beda server beda nama symbol. Cek dulu:
```powershell
python bot.py --check-symbols
```

Biasanya: `XAUUSDm` (Trial14) atau `XAUUSD` (Trial7)

### 7. JALANKAN!

```powershell
python bot.py --login 12345678 --pass PASSWORD --server Exness-MT5Trial14
```

Atau double-click `run.bat` (edit dulu credentialnya).

---

## 🧪 MODE TESTING (TANPA MT5)

Mau test analisisnya dulu tanpa modal? Pake data Binance:

```powershell
python test.py
```

Ini bakal jalanin analisis lengkap pake data real XAUUSD dari Binance.
Melihat hasil score, zone, dan rekomendasi tanpa perlu konek MT5.

---

## 📊 PERINTAH

| Perintah | Fungsi |
|----------|--------|
| `python bot.py --login ID --pass PW --server SRV` | Jalanin bot real |
| `python test.py` | Mode testing offline |
| `python bot.py --check-symbols` | Cek daftar symbol Exness |
| `python bot.py --report` | Liat performance report |
| `run.bat` | Jalanin bot (double-click) |
| `report.bat` | Liat report (double-click) |

---

## 🏗️ STRUKTUR PROYEK

```
sniper-ultra/
├── bot.py                 # Main loop trading
├── test.py                # Mode testing offline
├── config.py              # Semua parameter trading
├── credentials.json       # Login Exness + Telegram (bikin sendiri)
├── requirements.txt       # Dependencies
├── .gitignore
├── README.md              # File ini
├── run.bat                # Launcher Windows
├── report.bat             # Report generator
├── engine/
│   ├── snd.py             # Supply & Demand (RBR/RBD/DBR/DBD, MPL)
│   ├── smc.py             # SMC (BOS/CHoCH, OB, FVG, AMD Cycle)
│   ├── elliot_wave.py     # Elliot Wave (1-2-3-4-5 + ABC)
│   ├── fibonacci.py       # Fibonacci (Retracement, Extension, Harmonic)
│   ├── liquidity.py       # Liquidity (Sweeps, Pools, Inducement)
│   ├── candlestick.py     # 89 Candlestick Patterns (4-Level)
│   ├── triple_screen.py   # Elder Triple Screen + Impulse System
│   └── confluence.py      # Scoring Engine (7 modul -> 200pt)
├── trading/
│   ├── entry.py           # 4-Gate Entry + MT5 Execution
│   ├── risk.py            # Risk Management ($500, 1:2000)
│   ├── trailing.py        # Smart Trailing (25% increments)
│   └── learning.py        # Self-Learning (SQLite)
└── utils/
    ├── logger.py           # ASCII-safe logging
    └── notifier.py         # Telegram notifikasi
```

---

## ⚙️ KONFIGURASI UTAMA (config.py)

| Parameter | Default | Fungsi |
|-----------|---------|--------|
| `SYMBOL` | XAUUSDm | Pair trading |
| `RISK_PER_TRADE` | 0.015 (1.5%) | Risiko per trade |
| `MAX_OPEN_TRADES` | 2 | Maksimal posisi bersamaan |
| `SCORE_MIN` | 120 | Minimal confluence score |
| `TP_MIN_RR` | 2.5 | Minimal Risk:Reward ratio |
| `CIRCUIT_BREAKER_LOSSES` | 3 | Stop setelah N loss beruntun |
| `DAILY_MAX_LOSS` | $25 | Stop setelah loss harian |

Semua parameter bisa diubah di `config.py`.

---

## 🔬 ANALISIS 7 MODUL

### 1. Supply & Demand (30pt)
Deteksi zona RBR, RBD, DBR, DBD + MPL (Maximum Pain Level).
Zona FRESH = belum pernah disentuh harga = paling valid.

### 2. SMC (45pt)
- **BOS/CHoCH:** Break of Structure, Change of Character
- **Order Block:** Candle terakhir institusi sebelum impulse
- **FVG:** Fair Value Gap (imbalance) dengan tracking mitigation
- **AMD:** Accumulation → Manipulation → Distribution cycle

### 3. Elliot Wave (20pt)
Deteksi 5-wave impulsive (1-2-3-4-5) + corrective ABC.
Rules: Wave 2 != low dr Wave 1, Wave 3 != terpendek, Wave 4 != overlap.

### 4. Fibonacci (20pt)
Retracement (0.236-0.786) + Extension (0.382-2.618).
**OTE Zone:** 0.618-0.786 = sweet spot entry.
Harmonic patterns: Gartley, Bat, Butterfly, Crab.

### 5. Liquidity (25pt)
- **BSL:** Buy Stops Liquidity (equal highs)
- **SSL:** Sell Stops Liquidity (equal lows)
- **Sweep detection:** Stop hunt + reversal
- **Inducement:** Fake trap detection

### 6. Candlestick (30pt)
89 pola dengan 4 level reliability.
Level 1 (paling reliable): Engulfing, Morning/Evening Star, Dark Cloud Cover, Piercing Line, Kicker.
Level 4: Three Soldiers/Crows, Stick Sandwich.

### 7. Triple Screen (30pt)
Elder's system:
- Screen 1: HTF trend (H1)
- Screen 2: LTF entry (M15)
- Screen 3: M1 timing
- **Impulse System:** GREEN (long only) / RED (short only) / BLUE (transition)

---

## 🚪 4-GATE ENTRY SYSTEM

SEMUA 4 gate harus lolos sebelum entry:

| Gate | Syarat | Deskripsi |
|------|--------|-----------|
| 1 | Score >= 120 | Confluence dari 7 modul |
| 2 | Di Zona | OB / FVG / SnD zone |
| 3 | M1 Confirmed | Candlestick pattern valid |
| 4 | Strength >= 2/3 | Pattern strength cukup |

---

## 📈 RISK MANAGEMENT

- **Risk per trade:** 1.5% ($7.50 dari $500)
- **Max posisi:** 2 bersamaan
- **Max loss harian:** $25 (5%)
- **Circuit breaker:** Berhenti setelah 3 loss beruntun
- **Min RR:** 1:2.5 (target 2.5x lipat risiko)
- **Ideal RR:** 1:2.8

### Trailing Stop (25% increments)

| Profit | Trailing | ATR Multiplier |
|--------|----------|----------------|
| 25% | Breakeven | - |
| 50% | Konservatif | 3.0x ATR |
| 75% | Moderate | 2.5x ATR |
| 100% | Normal | 2.0x ATR |
| 125% | Agresif | 1.5x ATR |
| 150% | Ketat | 1.2x ATR |
| 175% | Sangat ketat | 1.0x ATR |
| 200% | Maksimal | 0.8x ATR |

---

## 🔔 TELEGRAM NOTIFIKASI

Bot otomatis kirim notif ke Telegram lo pas:
- ✅ **Signal ditemukan** — ada potensi entry bagus
- ✅ **Order terisi** — konfirmasi entry + harga
- ✅ **Order closed** — hasil WIN/LOSS + profit
- ✅ **Daily report** — ringkasan harian
- ⚠️ **Error/Crash** — bot masalah

**Setup:** Taruh `telegram_bot_token` dan `telegram_chat_id` di `credentials.json`

Cara dapetin:
1. Chat `@BotFather` di Telegram → `/newbot` → dapet token
2. Chat `@userinfobot` → dapet chat ID lo

---

## 🧠 SELF-LEARNING

Bot otomatis nyimpen history trade di SQLite (`trades.db`).
Tiap 100 loop, bot analisis:
- Winrate, Profit Factor, Avg Win/Loss
- Performance per setup type (Engulfing, Hammer, dll)
- Performance per session (London, NY, Asian)
- Saran optimasi parameter

**Manual report:**
```powershell
python bot.py --report
```
Atau double-click `report.bat`

---

## ⚠️ PENTING!

1. **DEMO DULU!** Jangan langsung real account. Test di demo minimal 1 minggu.
2. **Awasi 30 menit pertama** — pastikan analisis masuk akal.
3. **Jangan tinggal bot jalan tanpa diawasi** — koneksi bisa putus, error bisa terjadi.
4. **Risiko trading tetap ada** — bot cuma alat bantu analisis, bukan jaminan profit.
5. **Pair: XAUUSDm** — kalo error "symbol not found", cek pake `--check-symbols`

---

## 🐛 TROUBLESHOOTING

| Masalah | Solusi |
|---------|--------|
| `symbol not found` | Cek nama symbol: `python bot.py --check-symbols` |
| `AutoTrading disabled` | Klik tombol AutoTrading di MT5 (Ctrl+E) |
| `No module named MetaTrader5` | `pip install MetaTrader5` |
| `cannot connect to MT5` | Buka MT5 dulu, pastikan udah login |
| `UnicodeEncodeError` | Udah di-handle (ASCII-safe logging) |

---

## 📜 LISENSI

MIT — bebas dipake, dimodifikasi, disebarkan.
Dibuat oleh Nur Alip Cahya Firdaus (@alipun09).

---

*"Dari 7 modul analisis, lewat 4 gate, profit maksimal loss minimal."*
