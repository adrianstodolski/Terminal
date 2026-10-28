"""Venue-aware market depth and conservative signal gating. Read-only."""
import math
import time

def summarize_l2(levels, now_ms=None, max_age_ms=10000):
    now_ms = int(time.time()*1000) if now_ms is None else now_ms
    try:
        ts=int(levels['time']); sides=levels['levels']
        bids=[(float(x['px']),float(x['sz'])) for x in sides[0]]
        asks=[(float(x['px']),float(x['sz'])) for x in sides[1]]
        if not bids or not asks or any(not math.isfinite(v) or v<=0 for pair in bids+asks for v in pair):
            raise ValueError('invalid depth levels')
        bid=max(p for p,_ in bids);ask=min(p for p,_ in asks)
        if bid>=ask:raise ValueError('crossed book')
        bq=sum(q for p,q in bids if p>=bid*.999)
        aq=sum(q for p,q in asks if p<=ask*1.001)
        age=max(0,now_ms-ts)
        return {'status':'live' if age<=max_age_ms else 'stale','venue':'Hyperliquid','timestamp_ms':ts,'age_ms':age,
                'best_bid':bid,'best_ask':ask,'mid':(bid+ask)/2,'spread_bps':(ask-bid)/((ask+bid)/2)*10000,
                'near_bid_qty':bq,'near_ask_qty':aq,'near_imbalance':(bq-aq)/(bq+aq) if bq+aq else None}
    except (KeyError,IndexError,TypeError,ValueError,OverflowError) as e:
        return {'status':'invalid','venue':'Hyperliquid','reason':str(e)[:100]}

def qualify_signal(signal, depth, max_spread_bps=20, min_imbalance=.08):
    """Gate confirmations on the execution venue, never Binance proxy depth."""
    out=dict(signal);out['execution_depth']=depth
    if out.get('status')!='CONFIRMED':return out
    if depth.get('venue')!='Hyperliquid' or depth.get('status')!='live':
        out['status']='DEPTH_UNAVAILABLE';return out
    if depth.get('spread_bps',float('inf'))>max_spread_bps:
        out['status']='WIDE_SPREAD';return out
    side=out.get('side');imb=depth.get('near_imbalance')
    if imb is None or (side=='LONG' and imb<min_imbalance) or (side=='SHORT' and imb>-min_imbalance):
        out['status']='DEPTH_NOT_ALIGNED';return out
    out['status']='VENUE_CONFIRMED';return out
