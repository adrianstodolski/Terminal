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

def fetch_candles(symbol,interval,bars=350):
    if not symbol.replace('-','').isalnum() or len(symbol)>24 or interval not in INTERVALS:
        raise ValueError('invalid symbol or interval')
    end=int(time.time()*1000);step=INTERVALS[interval]
    body=json.dumps({'type':'candleSnapshot','req':{'coin':symbol,'interval':interval,'startTime':end-(bars+1)*step,'endTime':end}}).encode()
    req=Request(HL_INFO,data=body,headers={'Content-Type':'application/json','User-Agent':'EdgeDepth-readonly/0.1'})
    with urlopen(req,timeout=12) as response: data=json.load(response)
    if not isinstance(data,list):raise ValueError('unexpected candle response')
    complete=[x for x in data if int(x['T'])<end]
    if len(complete)<60:raise ValueError('too few completed candles')
    return complete

class Handler(BaseHTTPRequestHandler):
    def reply(self,status,value):
        body=json.dumps(value,allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        self.send_header('Access-Control-Allow-Origin','http://127.0.0.1:8080')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers();self.wfile.write(body)
    def do_GET(self):
        path=urlsplit(self.path).path
        args=parse_qs(urlsplit(self.path).query)
        get=lambda name,default:args.get(name,[default])[0]
        if path=='/api/health':
            return self.reply(200,{'status':'ok','service':'EdgeDepth independent analytics API','read_only':True,'warning':'No live trading validation'})
        if path not in ('/api/risk','/api/indicators','/api/advanced-indicators','/api/backtest','/api/strategy-compare'):
            return self.reply(404,{'error':'unknown endpoint'})
        try:
            if path=='/api/risk':
                return self.reply(200,position_plan(float(get('entry','0')),float(get('stop','0')),float(get('equity','0')),float(get('risk_fraction','0.005')),float(get('leverage_cap','3'))))
            symbol=get('symbol','BTC').upper();interval=get('interval','5m')
            if path in ('/api/backtest','/api/strategy-compare') and interval!='5m':
                raise ValueError('backtesting supports only 5m')
            side=get('side','LONG').upper()
            if side not in ('LONG','SHORT'):raise ValueError('invalid side')
            bars=fetch_candles(symbol,interval)
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
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8765);args=p.parse_args()
    print(f'EdgeDepth read-only analytics: http://127.0.0.1:{args.port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
if __name__=='__main__':main()
