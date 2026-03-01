import json, os, math, time, random, argparse
from datetime import datetime, timezone
import requests
import numpy as np
from itertools import product
from jesse.research import backtest

BASE = os.path.dirname(os.path.dirname(__file__))
REPORTS = os.path.join(BASE, 'reports')
os.makedirs(REPORTS, exist_ok=True)


def fetch_binance_1m(symbol='BTCUSDT', limit_batches=30):
    # ~30k minutes (~20 days)
    out = []
    end = None
    for _ in range(limit_batches):
        params = {'symbol': symbol, 'interval': '1m', 'limit': 1000}
        if end:
            params['endTime'] = end
        r = requests.get('https://api.binance.com/api/v3/klines', params=params, timeout=20)
        r.raise_for_status()
        rows = r.json()
        if not rows:
            break
        out = rows + out
        end = rows[0][0] - 1
        time.sleep(0.15)
    arr = []
    for k in out:
        ts = int(k[0])
        o,h,l,c,v = map(float,[k[1],k[2],k[3],k[4],k[5]])
        arr.append([ts,o,c,h,l,v])
    # dedupe sort
    arr = sorted({r[0]:r for r in arr}.values(), key=lambda x:x[0])
    return np.array(arr, dtype=np.float64)


def run_one(strategy, hp, candles, timeframe='1h'):
    config = {
        'starting_balance': 10_000,
        'fee': 0.0004,
        'type': 'futures',
        'futures_leverage': 2,
        'futures_leverage_mode': 'cross',
        'exchange': 'Binance',
        'warm_up_candles': 210,
    }
    routes = [{'exchange':'Binance','symbol':'BTC-USDT','timeframe':timeframe,'strategy':strategy}]
    data_routes = []
    candles_dict = {'Binance-BTC-USDT': {'exchange':'Binance','symbol':'BTC-USDT','candles':candles}}
    res = backtest(config, routes, data_routes, candles_dict, hyperparameters=hp, fast_mode=True)
    m = res.get('metrics', {})
    return {
        'strategy': strategy,
        'hp': hp,
        'total_trades': m.get('total', 0),
        'win_rate': m.get('win_rate', 0),
        'net_profit_percentage': m.get('net_profit_percentage', 0),
        'max_drawdown': m.get('max_drawdown', None),
        'sharpe': m.get('sharpe', None),
        'calmar': m.get('calmar', None),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--minutes', type=int, default=5, help='run budget in minutes')
    parser.add_argument('--batches', type=int, default=30, help='binance 1000-candle batches')
    parser.add_argument('--timeframe', type=str, default='1h', choices=['1h','4h','1d'], help='strategy trading timeframe')
    args = parser.parse_args()

    candles = fetch_binance_1m(limit_batches=args.batches)
    tests = []
    # base grid
    for f,s,tp,sl in product([9,12,15],[45,55,75],[0.018,0.025],[0.009,0.012]):
        if f < s:
            tests.append(('EMACross', {'fast':f,'slow':s,'risk':0.02,'tp':tp,'sl':sl}))
    for rsi,lo,hi in product([10,14],[25,30],[70,75]):
        tests.append(('RSIReversion', {'rsi':rsi,'low':lo,'high':hi,'risk':0.02,'tp':0.018,'sl':0.01}))
    for lb,k in product([16,24,36],[1.0,1.2,1.5]):
        tests.append(('BreakoutATR', {'lookback':lb,'atrp':14,'k':k,'risk':0.02}))

    # stochastic extensions for longer runs
    random.seed(42)
    for _ in range(600):
        tests.append(('EMACross', {
            'fast': random.choice([7,9,12,15,18,21]),
            'slow': random.choice([35,45,55,75,100]),
            'risk': random.choice([0.01,0.015,0.02]),
            'tp': random.choice([0.012,0.018,0.025,0.035]),
            'sl': random.choice([0.006,0.009,0.012,0.015])
        }))
        tests.append(('RSIReversion', {
            'rsi': random.choice([8,10,12,14,16,18]),
            'low': random.choice([20,25,30,35]),
            'high': random.choice([65,70,75,80]),
            'risk': random.choice([0.01,0.015,0.02]),
            'tp': random.choice([0.012,0.018,0.024]),
            'sl': random.choice([0.006,0.01,0.014])
        }))
        tests.append(('BreakoutATR', {
            'lookback': random.choice([12,16,24,36,48]),
            'atrp': random.choice([7,10,14,21]),
            'k': random.choice([0.8,1.0,1.2,1.5,1.8]),
            'risk': random.choice([0.01,0.015,0.02])
        }))

    results = []
    deadline = time.time() + (args.minutes * 60)
    for i,(name,hp) in enumerate(tests,1):
        if time.time() > deadline:
            break
        if name == 'EMACross' and hp.get('fast', 1) >= hp.get('slow', 2):
            continue
        try:
            r = run_one(name, hp, candles, timeframe=args.timeframe)
            results.append(r)
        except Exception as e:
            results.append({'strategy':name,'hp':hp,'error':str(e)})

    valids = [r for r in results if 'error' not in r]
    valids.sort(key=lambda x: (x.get('net_profit_percentage') or -999), reverse=True)

    now = datetime.now(timezone.utc).strftime('%Y-%m-%d_%H%MUTC')
    raw_path = os.path.join(REPORTS, f'run_{now}.json')
    with open(raw_path,'w') as f:
        json.dump({'generated_at_utc': now, 'count': len(results), 'results': results}, f, indent=2)

    top = valids[:10]
    bottom = sorted(valids, key=lambda x: (x.get('net_profit_percentage') or 999))[:5]
    md = []
    md.append(f"# Jesse Nightly Research Report ({now})")
    md.append('')
    md.append(f"- Universe: BTC-USDT 1m candles (~{len(candles)} rows) from Binance API")
    md.append(f"- Strategy timeframe: {args.timeframe}")
    md.append(f"- Backtests attempted: {len(results)}")
    md.append(f"- Run budget: {args.minutes} minute(s)")
    md.append(f"- Successful: {len(valids)}")
    md.append('')
    md.append('## Top 10 Strategies by Net Profit %')
    for r in top:
        md.append(f"- {r['strategy']} hp={r['hp']} | net={r['net_profit_percentage']:.2f}% | win={r['win_rate']:.1f}% | trades={r['total_trades']}")
    md.append('')
    md.append('## Bottom 5 (for failure analysis)')
    for r in bottom:
        md.append(f"- {r['strategy']} hp={r['hp']} | net={r['net_profit_percentage']:.2f}% | win={r['win_rate']:.1f}% | trades={r['total_trades']}")
    md.append('')
    md.append('## Improvement Ideas (auto)')
    md.append('- Segment by regime (trend vs chop) and route strategy accordingly.')
    md.append('- Introduce volatility filter to avoid low-ATR whipsaw periods.')
    md.append('- Add walk-forward split (train/validate/test) to reduce overfitting risk.')
    md.append('')
    md.append(f"Raw results JSON: `{os.path.basename(raw_path)}`")

    report_path = os.path.join(REPORTS, f'report_{now}.md')
    with open(report_path,'w') as f:
        f.write('\n'.join(md))

    print(report_path)

if __name__ == '__main__':
    main()
