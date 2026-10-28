"""Deterministic research analytics. No trading or claimed predictive probabilities."""
import math

def position_plan(entry, stop, equity, risk_fraction=.005, leverage_cap=3):
    vals=(entry,stop,equity,risk_fraction,leverage_cap)
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in vals):
        raise ValueError('all inputs must be finite numbers')
    if entry<=0 or stop<=0 or equity<=0 or not 0<risk_fraction<=.05 or not 0<leverage_cap<=20 or entry==stop:
        raise ValueError('invalid risk inputs')
    risk_budget=equity*risk_fraction
    unit_risk=abs(entry-stop)
    quantity=min(risk_budget/unit_risk,equity*leverage_cap/entry)
    return {'risk_budget_usd':round(risk_budget,2),'quantity':quantity,'notional_usd':quantity*entry,'stop_loss_usd':quantity*unit_risk,'max_leverage':leverage_cap,'assumptions':'Excludes fees, funding, slippage, liquidation and gap risk; informational only'}

def historical_breakouts(bars, side, atr_period=14, lookback=20, horizon=12):
    """Non-overlapping historical close-confirmed breakouts; entry next bar open,
    stop/target evaluated intrabar; if both touched stop wins. No future leakage.
    All candles MUST be completed, contiguous, and chronologically ordered.
    """
    if side not in ('LONG','SHORT'):raise ValueError('invalid side')
    if len(bars)<lookback+atr_period+horizon+2:raise ValueError('insufficient history')
    candles=sorted(bars,key=lambda x:int(x['t']))
    interval=int(candles[1]['t'])-int(candles[0]['t'])
    if interval<=0 or any(int(b['t'])-int(a['t'])!=interval for a,b in zip(candles,candles[1:])):
        raise ValueError('candle gaps or duplicates')
    for b in candles:
        if not all(math.isfinite(float(b[k])) for k in ('o','h','l','c')) or float(b['h'])<float(b['l']):raise ValueError('invalid OHLC')
    outcomes=[];i=max(lookback,atr_period+1)
    direction=1 if side=='LONG' else -1
    while i<len(candles)-1:
        previous=candles[i-lookback:i]
        threshold=max(float(x['h']) for x in previous) if direction==1 else min(float(x['l']) for x in previous)
        close=float(candles[i]['c'])
        if direction*(close-threshold)<=0:i+=1;continue
        trs=[]
        for j in range(i-atr_period+1,i+1):
            b=candles[j];prior=float(candles[j-1]['c']);high=float(b['h']);low=float(b['l'])
            trs.append(max(high-low,abs(high-prior),abs(low-prior)))
        atr=sum(trs)/len(trs)
        if atr<=0:i+=1;continue
        entry=float(candles[i+1]['o']);stop=entry-direction*1.5*atr;target=entry+direction*3*atr
        exit_price=float(candles[min(i+horizon,len(candles)-1)]['c']);reason='TIME';last=min(i+horizon,len(candles)-1)
        for j in range(i+1,last+1):
            b=candles[j];low=float(b['l']);high=float(b['h'])
            stop_hit=low<=stop if direction==1 else high>=stop
            target_hit=high>=target if direction==1 else low<=target
            if stop_hit or target_hit:
                exit_price=stop if stop_hit else target
                reason='STOP' if stop_hit else 'TARGET';last=j;break
        r=direction*(exit_price-entry)/(1.5*atr)
        outcomes.append({'entry_ms':int(candles[i+1]['t']),'exit_ms':int(candles[last]['t']),'entry':entry,'exit':exit_price,'r':r,'exit_reason':reason})
        i=last+1
    wins=sum(x['r']>0 for x in outcomes);total=sum(x['r'] for x in outcomes)
    return {'side':side,'trades':len(outcomes),'win_rate':wins/len(outcomes) if outcomes else None,'mean_r':total/len(outcomes) if outcomes else None,'total_r':total,'assumptions':'Historical close-confirmed breakouts; next-open fill; stop-first intrabar ambiguity; no fees/slippage/funding; not a forecast','sample':outcomes,'trade_detail_count':len(outcomes)}
