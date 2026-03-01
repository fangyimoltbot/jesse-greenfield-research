# Jesse Greenfield Research Lab

Automated nightly strategy research using Jesse framework.

## What this does
- Pulls recent BTCUSDT 1m candles from Binance public API
- Runs a grid of Jesse backtests across multiple strategies
- Writes JSON results + Markdown report under `reports/`

## Strategies
- `EMACross`
- `RSIReversion`
- `BreakoutATR`

## Run
```bash
python3 scripts/nightly_research.py
```
