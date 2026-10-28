"""Read-only local JSON API; research only. Run: python3 integration/api.py"""
import argparse, json, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs
from urllib.request import Request, urlopen
from analytics import position_plan, historical_breakouts
from indicator_lab import indicator_snapshot
from advanced_indicators import advanced_snapshot
from strategy_lab import compare_strategies

HL_INFO='https://api.hyperliquid.xyz/info'
INTERVALS={'1m':60000,'5m':300000,'15m':900000,'1h':3600000,'4h':14400000}

# Imported read-only source diagnostics. Never submits exchange orders.
from market_fusion import summarize_l2
from gateway_depth import GatewayMonitor
from urllib.parse import urlencode
from urllib.error import URLError

_GATEWAY = None

def source_json(url, payload=None, timeout=5):
    body=None if payload is None else json.dumps(payload).encode()
    headers={'Content-Type':'application/json','User-Agent':'EdgeDepth-integration/0.2'}
    with urlopen(Request(url,data=body,headers=headers),timeout=timeout) as response:
        return json.load(response)

def hyperliquid_depth(symbol):
    try:
        return summarize_l2(source_json(HL_INFO, {'type':'l2Book','coin':symbol}, timeout=5))
    except Exception as exc:
        return {'status':'unavailable','venue':'Hyperliquid','reason':type(exc).__name__}

def gateway_status():
    return _GATEWAY.report() if _GATEWAY is not None else {
        'status':'disabled','reason':'Use --gateway to subscribe to local Gateway'}

def source_status(symbol='BTC'):
    """Diagnostics are independent; one offline venue cannot mask another."""
    sources={'hyperliquid_depth':hyperliquid_depth(symbol),'gateway':gateway_status()}
    for key,url in (
        ('hyperdata_health','http://127.0.0.1:8420/v1/health'),
        ('hyperdata_market','http://127.0.0.1:8420/v1/market')):
        try:
            data=source_json(url,timeout=2)
            if key=='hyperdata_market':
                # Keep overview bounded; market data may include many symbols.
                rows=data if isinstance(data,list) else None
                if isinstance(data,dict):
                    for name in ('markets','assets','data','results','items'):
                        if isinstance(data.get(name),list):rows=data[name];break
                    if rows is None and data and all(isinstance(v,dict) for v in data.values()):rows=list(data.values())
                sources[key]={'status':'available','rows':len(rows) if rows is not None else None,
                              'data_shape':type(data).__name__,
                              'keys':list(data)[:12] if isinstance(data,dict) else None,
                              'note':'rows=null means unrecognized response schema, not an empty market'}
            else:
                sources[key]={'status':'available','data':data}
        except Exception as exc:
            sources[key]={'status':'unavailable','reason':type(exc).__name__}
    try:
        import ccxt
        exchange=ccxt.binanceusdm({'enableRateLimit':True,'timeout':4000})
        ticker=exchange.fetch_ticker(f'{symbol}/USDT:USDT')
        sources['ccxt']={'status':'available','venue':'Binance USD-M',
                         'last':ticker.get('last'),'timestamp_ms':ticker.get('timestamp')}
    except Exception as exc:
        sources['ccxt']={'status':'unavailable','reason':type(exc).__name__}
    return sources


def fetch_candles(symbol,interval,bars=350):
    if not symbol.replace('-','').isalnum() or len(symbol)>24 or interval not in INTERVALS:
        raise ValueError('invalid symbol or interval')
    end=int(time.time()*1000);step=INTERVALS[interval]
    body=json.dumps({'type':'candleSnapshot','req':{'coin':symbol,'interval':interval,'startTime':end-(bars+1)*step,'endTime':end}}).encode()
    req=Request(HL_INFO,data=body,headers={'Content-Type':'application/json','User-Agent':'EdgeDepth-readonly/0.1'})
    with urlopen(req,timeout=12) as response: data=json.load(response)
    if not isinstance(data,list):raise ValueError('unexpected candle response')
    complete=[]
    for x in data:
        if not isinstance(x,dict):continue
        try:
            start=int(x['t']); finish=int(x.get('T',start+step-1))
            if finish>=end or start+step>end:continue
            row={'t':start,'o':float(x['o']),'h':float(x['h']),'l':float(x['l']),'c':float(x['c'])}
            if row['l']<=0 or row['h']<max(row['o'],row['c']) or row['l']>min(row['o'],row['c']):continue
            complete.append(row)
        except (KeyError,ValueError,TypeError):continue
    complete.sort(key=lambda x:x['t'])
    if len(complete)<60:raise ValueError('too few valid completed candles')
    return complete

class Handler(BaseHTTPRequestHandler):
    def reply(self,status,value):
        body=json.dumps(value,allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        origin=self.headers.get('Origin','')
        allowed={'http://127.0.0.1:8080','http://localhost:8080',
                 'http://127.0.0.1:8082','http://localhost:8082'}
        if origin in allowed:
            self.send_header('Access-Control-Allow-Origin',origin)
            self.send_header('Vary','Origin')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers();self.wfile.write(body)
    def do_GET(self):
        path=urlsplit(self.path).path
        args=parse_qs(urlsplit(self.path).query)
        get=lambda name,default:args.get(name,[default])[0]
        if path=='/api/health':
            return self.reply(200,{'status':'ok','service':'EdgeDepth independent analytics API','read_only':True,'warning':'No live trading validation'})
        if path not in ('/api/risk','/api/indicators','/api/advanced-indicators','/api/backtest','/api/strategy-compare','/api/candles','/api/overview','/api/depth','/api/fusion'):
            return self.reply(404,{'error':'unknown endpoint'})
        try:
            if path in ('/api/overview','/api/depth','/api/fusion'):
                symbol=get('symbol','BTC').upper()
                if not symbol.replace('-','').isalnum() or len(symbol)>24:raise ValueError('invalid symbol')
                if path in ('/api/depth','/api/fusion'):
                    depth=hyperliquid_depth(symbol)
                    gateway=gateway_status()
                    if path=='/api/depth':return self.reply(200,{'symbol':symbol,'hyperliquid':depth,'gateway':gateway})
                    return self.reply(200,{'symbol':symbol,'execution_venue':'Hyperliquid','execution_depth':depth,'context_venue':gateway,'note':'Binance depth is not execution venue confirmation'})
                return self.reply(200,{'symbol':symbol,'sources':source_status(symbol),'read_only':True})
            if path=='/api/risk':
                return self.reply(200,position_plan(float(get('entry','0')),float(get('stop','0')),float(get('equity','0')),float(get('risk_fraction','0.005')),float(get('leverage_cap','3'))))
            symbol=get('symbol','BTC').upper();interval=get('interval','5m')
            if path in ('/api/backtest','/api/strategy-compare') and interval!='5m':
                raise ValueError('backtesting supports only 5m')
            side=get('side','LONG').upper()
            if side not in ('LONG','SHORT'):raise ValueError('invalid side')
            bars=fetch_candles(symbol,interval)
            if path=='/api/candles':
                return self.reply(200,{'symbol':symbol,'interval':interval,'candles':bars[-180:],'source':'Hyperliquid completed candles','read_only':True})
            if path=='/api/indicators':result=indicator_snapshot(bars)
            elif path=='/api/advanced-indicators':result=advanced_snapshot(bars)
            elif path=='/api/backtest':result=historical_breakouts(bars,side)
            else:result=compare_strategies(bars,side,float(get('fee_bps','5')),float(get('slippage_bps','3')))
            result.update({'symbol':symbol,'interval':interval,'source':'Hyperliquid completed candles','read_only':True})
            return self.reply(200,result)
        except (ValueError,KeyError,TypeError) as exc:return self.reply(400,{'error':str(exc)[:200]})
        except Exception as exc:return self.reply(503,{'error':str(exc)[:200],'note':'upstream market-data dependency unavailable'})
    def log_message(self,*args):pass

def main():
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8765);p.add_argument('--gateway',action='store_true',help='monitor EdgeDepth Gateway WebSocket (requires websockets)');args=p.parse_args()
    global _GATEWAY
    if args.gateway:
        _GATEWAY=GatewayMonitor();_GATEWAY.start()
    print(f'EdgeDepth read-only analytics: http://127.0.0.1:{args.port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
if __name__=='__main__':main()
