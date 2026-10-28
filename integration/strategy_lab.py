"""Causal indicator-filtered breakout research, with explicit trading costs."""
import math
from analytics import historical_breakouts
from advanced_indicators import advanced_snapshot
from indicator_lab import _validate

def compare_strategies(bars, side='LONG', fee_bps=5, slippage_bps=3, warmup=100):
    if side not in ('LONG','SHORT') or not (0<=fee_bps<=100 and 0<=slippage_bps<=100):
        raise ValueError('invalid strategy parameters')
    rows=_validate(bars)
    if len(rows)<warmup+40:raise ValueError('insufficient historical candles')
    base=historical_breakouts(rows,side)
    index={int(row['t']):i for i,row in enumerate(rows)}
    enriched=[]
    for trade in base['sample']:
        entry_idx=index.get(int(trade['entry_ms']))
        if entry_idx is None or entry_idx<warmup+1:continue
        signal_idx=entry_idx-1
        snapshot=advanced_snapshot(rows[:signal_idx+1])
        votes=snapshot['consensus']['votes']
        alignment=sum(v==(1 if side=='LONG' else -1) for v in votes.values())
        trs=[]
        for j in range(signal_idx-13,signal_idx+1):
            b=rows[j];prior=rows[j-1];h=float(b['h']);l=float(b['l']);c=float(prior['c'])
            trs.append(max(h-l,abs(h-c),abs(l-c)))
        stop_distance=1.5*sum(trs)/len(trs)
        cost_r=(2*(fee_bps+slippage_bps)/10000)*float(trade['entry'])/stop_distance if stop_distance>0 else 0
        enriched.append({'entry_ms':trade['entry_ms'],'gross_r':trade['r'],'net_r':trade['r']-cost_r,'alignment':alignment,'indicator_bias':snapshot['consensus']['bias']})
    def stats(items):
        net=[t['net_r'] for t in items]
        equity=0;peak=0;max_dd=0
        for r in net:
            equity+=r;peak=max(peak,equity);max_dd=max(max_dd,peak-equity)
        return {'trades':len(net),'net_total_r':round(sum(net),5),'net_mean_r':round(sum(net)/len(net),5) if net else None,'win_rate_net':sum(r>0 for r in net)/len(net) if net else None,'max_drawdown_r':round(max_dd,5)}
    return {'symbol_strategy':'20-bar breakout, next-open fill, ATR stop','side':side,'base':stats(enriched),'indicator_filtered':stats([t for t in enriched if t['alignment']>=2]),'fee_bps_per_side':fee_bps,'slippage_bps_per_side':slippage_bps,'sample_limit':50,'evaluated_trades':enriched[-25:],'limitations':'Only last 50 base trades retained by historical_breakouts; no orderflow replay, funding, gap execution model, or out-of-sample validation. Results are not predictive.'}
