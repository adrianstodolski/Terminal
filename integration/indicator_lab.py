"""Transparent, causal indicator research; not proprietary MT4/Jurik clones."""
import math

def _validate(bars):
    if len(bars)<60: raise ValueError('need at least 60 completed candles')
    rows=sorted(bars,key=lambda b:int(b['t']))
    step=int(rows[1]['t'])-int(rows[0]['t'])
    if step<=0 or any(int(b['t'])-int(a['t'])!=step for a,b in zip(rows,rows[1:])):
        raise ValueError('missing, duplicated or irregular candles')
    for b in rows:
        o,h,l,c=(float(b[k]) for k in ('o','h','l','c'))
        if not all(map(math.isfinite,(o,h,l,c))) or min(o,c)<l or max(o,c)>h or l<=0:
            raise ValueError('invalid OHLC')
    return rows

def ema(values,period):
    if period<1:raise ValueError('invalid period')
    out=[];last=None;k=2/(period+1)
    for x in values:
        last=x if last is None else last+k*(x-last)
        out.append(last)
    return out

def rsi(values,period=14):
    if len(values)<=period:raise ValueError('insufficient data')
    gains=[max(values[i]-values[i-1],0) for i in range(1,len(values))]
    losses=[max(values[i-1]-values[i],0) for i in range(1,len(values))]
    ag=sum(gains[:period])/period;al=sum(losses[:period])/period
    out=[None]*period
    def calc(g,l):return 50.0 if g==0 and l==0 else (100.0 if l==0 else 100-100/(1+g/l))
    out.append(calc(ag,al))
    for g,l in zip(gains[period:],losses[period:]):
        ag=(ag*(period-1)+g)/period;al=(al*(period-1)+l)/period
        out.append(calc(ag,al))
    return out

def indicator_snapshot(bars):
    rows=_validate(bars)
    close=[float(x['c']) for x in rows]
    high=[float(x['h']) for x in rows];low=[float(x['l']) for x in rows]
    typical=[(h+l+c)/3 for h,l,c in zip(high,low,close)]
    cci=[]
    for i in range(len(rows)):
        if i<19:cci.append(None);continue
        window=typical[i-19:i+1];mean=sum(window)/20
        dev=sum(abs(v-mean) for v in window)/20
        cci.append((typical[i]-mean)/(.015*dev) if dev else 0.0)
    r=rsi(close)
    r_window=[v for v in r[-20:] if v is not None]
    r_mean=sum(r_window)/len(r_window)
    r_sd=math.sqrt(sum((v-r_mean)**2 for v in r_window)/len(r_window))
    fast=ema(close,12);slow=ema(close,26)
    macd=[a-b for a,b in zip(fast,slow)]
    signal=ema(macd,9)
    trs=[high[i]-low[i] if i==0 else max(high[i]-low[i],abs(high[i]-close[i-1]),abs(low[i]-close[i-1])) for i in range(len(rows))]
    atr=sum(trs[-14:])/14
    cci_long=cci[-2] is not None and cci[-2]<=100<cci[-1]
    cci_short=cci[-2] is not None and cci[-2]>=-100>cci[-1]
    return {
        'closed_at_ms':int(rows[-1]['t'])+int(rows[1]['t'])-int(rows[0]['t'])-1,
        'close':close[-1],
        'cci20':{'value':cci[-1],'previous':cci[-2],'long_cross':cci_long,'short_cross':cci_short},
        'rsi14':{'value':r[-1],'bollinger_mid20':r_mean,'bollinger_upper20_2sd':r_mean+2*r_sd,'bollinger_lower20_2sd':r_mean-2*r_sd},
        'ema_trend':{'ema12':fast[-1],'ema26':slow[-1],'direction':'UP' if fast[-1]>slow[-1] else 'DOWN' if fast[-1]<slow[-1] else 'FLAT'},
        'macd':{'value':macd[-1],'signal':signal[-1],'histogram':macd[-1]-signal[-1]},
        'atr14':atr,
        'research_bias':'LONG' if cci_long and fast[-1]>slow[-1] else 'SHORT' if cci_short and fast[-1]<slow[-1] else 'WAIT',
        'methodology':'Causal CCI(20), Wilder RSI(14) with rolling RSI Bollinger(20,2), EMA(12/26), MACD(12/26/9), ATR(14 simple TR). Completed candles only. No Jurik/MT4 proprietary equivalence claimed.',
        'warning':'Experimental indicators; no profitability claim, no execution signal.'
    }
