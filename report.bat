@echo off
:: SNIPER ULTRA — Report Generator
python -c "
from trading.learning import analyze_performance, get_optimization_suggestions
import json

analysis = analyze_performance(days=30)
print(json.dumps(analysis, indent=2))
print()
suggestions = get_optimization_suggestions(analysis)
for s in suggestions:
    print(f'  -> {s}')
"
pause
