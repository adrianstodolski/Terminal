"""Open, causal approximations for crypto research. No proprietary indicator equivalence."""
import math
from indicator_lab import _validate, ema, rsi

def rolling_mean(values, n):
    return [None if i+1<n else sum(values[i-n+1:i+1])/n for i in range(len(values))]

def rolling_std(values,n):
    out=[]
    for i in range(len(values)):
        if i+1<n:out.append(None);continue
        w=values[i-n+1:i+1];m=sum(w)/n
        out.append(math.sqrt(sum((x-m)**2 for x in w)/n))
    return out

def wilder_atr(high,low,close,n=14):
    tr=[high[0]-low[0]]+[max(high[i]-low[i],abs(high[i]-close[i-1]),abs(low[i]-close[i-1])) for i in range(1,len(close))]
    out=[None]*(n-1);a=sum(tr[:n])/n;out.append(a)
    for x in tr[n:]:a=(a*(n-1)+x)/n;out.append(a)
    return out

def advanced_snapshot(bars):
    rows=_validate(bars);c=[float(b['c']) for b in rows];h=[float(b['h']) for b in rows];l=[float(b['l']) for b in rows]
    atr=wilder_atr(h,l,c);atr_last=atr[-1]
    fast=ema(c,20);slow=ema(c,40);macd=[a-b for a,b in zip(fast,slow)]
    explosion=4*rolling_std(c,20)[-1];momentum=(macd[-1]-macd[-2])*150
    deadzone=atr_last*3.7
    active=abs(momentum)>deadzone and explosion>deadzone
    e13=ema(c,13);e21=ema(c,21)
    force=(e13[-1]-e13[-2]+e21[-1]-e21[-2])*.5*(e13[-1]-e21[-1])
    window=[]
    for i in range(22,len(c)):
        d=(e13[i]-e13[i-1]+e21[i]-e21[i-1])*.5*(e13[i]-e21[i])
        window.append(d)
    denom=max((abs(x) for x in window[-50:]),default=0)
    tdfi=force/denom if denom else 0
    trend_fast=ema(c,8)[-1];trend_mid=ema(c,21)[-1];trend_slow=ema(c,55)[-1]
    trend='UP' if trend_fast>trend_mid>trend_slow else 'DOWN' if trend_fast<trend_mid<trend_slow else 'MIXED'
    upper=max(h[-21:-1]);lower=min(l[-21:-1]);mid=(upper+lower)/2
    kama=c[9]
    for i in range(10,len(c)):
        direction=abs(c[i]-c[i-10]);noise=sum(abs(c[j]-c[j-1]) for j in range(i-9,i+1))
        er=direction/noise if noise else 0
        alpha=(er*(2/3-2/31)+2/31)**2
        kama+=alpha*(c[i]-kama)
    r=rsi(c,14);valid=[v for v in r if v is not None]
    baseline=rolling_mean(valid,20)[-1];sd=rolling_std(valid,20)[-1]
    composite=[('trend',1 if trend=='UP' else -1 if trend=='DOWN' else 0),('force',1 if tdfi>.25 else -1 if tdfi<-.25 else 0),('momentum',1 if active and momentum>0 else -1 if active and momentum<0 else 0)]
    score=sum(v for _,v in composite)
    return {'closed_at_ms':int(rows[-1]['t'])+int(rows[1]['t'])-int(rows[0]['t'])-1,'close':c[-1],
      'waddah_inspired':{'momentum':momentum,'explosion':explosion,'atr_deadzone':deadzone,'active':active},
      'tdfi_inspired':{'normalized_force':tdfi,'direction':'UP' if tdfi>.25 else 'DOWN' if tdfi<-.25 else 'NEUTRAL'},
      'itrend_inspired':{'ema8':trend_fast,'ema21':trend_mid,'ema55':trend_slow,'direction':trend},
      'hilo_channel':{'prior_20_high':upper,'prior_20_low':lower,'mid':mid,'breakout_up':c[-1]>upper,'breakout_down':c[-1]<lower},
      'supply_demand_proxy':{'supply':upper,'demand':lower,'method':'prior 20 completed candle extremes'},
      'rsi_bollinger':{'rsi14':r[-1],'mid':baseline,'upper':baseline+2*sd,'lower':baseline-2*sd},
      'composite_rsi_proxy':{'rsi14':r[-1],'adaptive_upper':baseline+sd,'adaptive_lower':baseline-sd},
      'adaptive_kama':{'value':kama,'price_above':c[-1]>kama},
      'consensus':{'score':score,'votes':dict(composite),'bias':'LONG' if score>=2 else 'SHORT' if score<=-2 else 'WAIT'},
      'atr14_wilder':atr_last,'warning':'Research-only, causal open implementations; NOT exact MT4, Jurik, Waddah Attar, TDFI or iTrend clones. No performance claim.'}
