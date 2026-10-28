"""Read-only EdgeDepth Gateway book monitor; subset protobuf decoder."""
import json, math, threading, time

def varint(buf,pos):
    v=0
    for i in range(10):
        if pos>=len(buf): raise ValueError('truncated varint')
        b=buf[pos];pos+=1;v|=(b&127)<<(7*i)
        if not b&128:return v,pos
    raise ValueError('varint too long')

def fields(buf, include_wire=False):
    import struct
    pos=0
    while pos<len(buf):
        tag,pos=varint(buf,pos);num,wire=tag>>3,tag&7
        if not num:raise ValueError('invalid protobuf field')
        if wire==0:val,pos=varint(buf,pos)
        elif wire==1:
            if pos+8>len(buf):raise ValueError('truncated fixed64')
            val=struct.unpack_from('<d',buf,pos)[0];pos+=8
        elif wire==2:
            length,pos=varint(buf,pos)
            if length>len(buf)-pos:raise ValueError('truncated length')
            val=buf[pos:pos+length];pos+=length
        elif wire==5:
            if pos+4>len(buf):raise ValueError('truncated fixed32')
            val=buf[pos:pos+4];pos+=4
        else:raise ValueError('unsupported protobuf wire')
        yield (num,wire,val) if include_wire else (num,val)

def decode_payload(data):
    f=list(fields(data)); pair=next((v for k,v in f if k==1),b'')
    p=dict(fields(pair))
    return {'exchange':p.get(1,b'').decode(),'symbol':p.get(2,b'').decode(),
            'stream':next((v for k,v in f if k==2),0),'data':next((v for k,v in f if k==4),b'')}

def decode_book(data):
    d={'asks':[],'bids':[],'snapshot':False,'first':0,'last':0,'previous':0,'timestamp_ms':0}
    for k,v in fields(data):
        if k in (2,3):
            # BookLevel.price and BookLevel.size are both protobuf double (wire 1).
            # A present field of any other wire type is malformed, even if its
            # decoded numeric value happens to look plausible.
            l={}
            for number,wire,value in fields(v,include_wire=True):
                if number in (1,2):
                    if wire!=1:raise ValueError('invalid book level wire type')
                    l[number]=value
            price=l.get(1,0.0);qty=l.get(2,0.0)
            # proto3 omits zero-valued scalars; size=0 is a valid book-level deletion.
            if price is None or qty is None or not math.isfinite(price) or not math.isfinite(qty) or price<=0 or qty<0:
                raise ValueError('invalid book level')
            d['asks' if k==2 else 'bids'].append((price,qty))
        elif k==1:d['timestamp_ms']=v
        elif k==4:d['snapshot']=bool(v)
        elif k==6:d['first']=v
        elif k==7:d['last']=v
        elif k==8:d['previous']=v
    return d

class BookState:
    def __init__(self):
        self.bids={};self.asks={};self.last_id=0;self.ready=False
        self.updated_ms=0;self.errors=0;self.gaps=0;self.await_first=False;self.resync_requested=False
    def apply(self,update):
        if update['snapshot']:
            # A fresh gateway snapshot is the only valid base after a gap.
            self.bids.clear();self.asks.clear();self.last_id=0
            self.ready=True;self.await_first=True;self.resync_requested=False
        elif not self.ready:
            return False
        else:
            last=update['last'];first=update['first'];previous=update['previous']
            if last and self.last_id and last<=self.last_id:
                return False  # delayed duplicate; do not roll back
            if self.await_first:
                # The first diff after a REST-backed snapshot may straddle its ID.
                contiguous=(not self.last_id or not last or (
                    (first and first<=self.last_id+1<=last) or previous==self.last_id))
            else:
                contiguous=(not self.last_id or not last or (
                    (previous and previous==self.last_id) or (
                        not previous and first and first<=self.last_id+1<=last)))
            if not contiguous:
                self.ready=False;self.await_first=False;self.resync_requested=True
                self.gaps+=1;self.bids.clear();self.asks.clear()
                return False
        for name,book in (('bids',self.bids),('asks',self.asks)):
            for price,qty in update[name]:
                if qty==0:book.pop(price,None)
                else:book[price]=qty
        self.last_id=update['last'] or self.last_id
        self.await_first=False if not update['snapshot'] else self.await_first
        self.updated_ms=int(time.time()*1000)
        return True
    def report(self):
        age=int(time.time()*1000)-self.updated_ms if self.updated_ms else None
        if not self.ready or not self.bids or not self.asks:return {'status':'waiting_snapshot','age_ms':age,'gaps':self.gaps,'resync_requested':self.resync_requested}
        bid=max(self.bids);ask=min(self.asks)
        if bid>=ask:return {'status':'crossed_book','age_ms':age,'gaps':self.gaps}
        bq=sum(q for p,q in self.bids.items() if p>=bid*.999)
        aq=sum(q for p,q in self.asks.items() if p<=ask*1.001)
        return {'status':'live' if age is not None and age<10000 else 'stale',
                'age_ms':age,'best_bid':bid,'best_ask':ask,
                'spread_bps':(ask-bid)/((ask+bid)/2)*10000,
                'near_bid_qty':bq,'near_ask_qty':aq,
                'near_imbalance':(bq-aq)/(bq+aq) if bq+aq else None,
                'gaps':self.gaps,'venue':'Binance USD-M',
                'note':'Binance book context only; NOT Hyperliquid executable depth'}

class GatewayMonitor:
    def __init__(self,url='ws://127.0.0.1:9001/ws',symbols=('btcusdt',)):
        self.url=url;self.symbols=tuple(symbols);self.books={s.upper():BookState() for s in symbols}
        self.lock=threading.Lock();self.error=None;self.connected=False;self.decode_errors=0;self.reconnects=0
    def start(self):
        threading.Thread(target=self.run,daemon=True,name='edgedepth-book-monitor').start()
    def run(self):
        try:
            from websockets.sync.client import connect
        except ImportError:
            self.error='Install websockets: python3 -m pip install websockets';return
        while True:
            try:
                with connect(self.url,open_timeout=5,max_size=8*1024*1024) as ws:
                    self.connected=True;self.error=None
                    for s in self.symbols:
                        ws.send(json.dumps({'method':'subscribe','data':{'pair':{'exchange':'binancef','symbol':s},'stream':3,'timeframe':0}}))
                    for frame in ws:
                        if not isinstance(frame,bytes):continue
                        try:
                            p=decode_payload(frame)
                            if p['stream']!=3 or p['symbol'].upper() not in self.books:continue
                            u=decode_book(p['data'])
                        except (ValueError,KeyError,TypeError,UnicodeDecodeError) as exc:
                            # A malformed frame must not drop a healthy WebSocket connection.
                            self.decode_errors+=1
                            self.error='bad frame: '+str(exc)[:120]
                            continue
                        with self.lock:
                            book=self.books[p['symbol'].upper()]
                            applied=book.apply(u)
                            need_resync=book.resync_requested
                        if need_resync:
                            # No snapshot arrives on an ongoing subscription.
                            # Reconnect/re-subscribe to obtain an authoritative base.
                            raise ConnectionError('depth sequence gap: resubscribe for snapshot')
                        if applied:self.error=None
            except Exception as e:self.error=str(e)[:160]
            self.connected=False;self.reconnects+=1;time.sleep(3)
    def report(self):
        with self.lock: books={k:v.report() for k,v in self.books.items()}
        return {'connected':self.connected,'error':self.error,'decode_errors':self.decode_errors,'reconnects':self.reconnects,'books':books}
