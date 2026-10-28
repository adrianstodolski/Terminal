import sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import api
from market_fusion import summarize_l2
from gateway_depth import decode_payload, decode_book, BookState

def vi(value):
    out=bytearray()
    while value>127:
        out.append((value&127)|128);value>>=7
    out.append(value)
    return bytes(out)
def fv(tag,v):return vi(tag<<3|0)+vi(v)
def fb(tag,b):return vi(tag<<3|2)+vi(len(b))+b

class ApiSafetyTests(unittest.TestCase):
    def test_depth_does_not_fetch_unrelated_venues(self):
        with patch.object(api,'source_json',return_value={'time':1000,'levels':[[{'px':'99','sz':'2'}],[{'px':'101','sz':'1'}]]}) as fetch:
            with patch('market_fusion.time.time',return_value=1.2):
                d=api.hyperliquid_depth('BTC')
            self.assertEqual(fetch.call_count,1)
            self.assertEqual(fetch.call_args.args[0],api.HL_INFO)
            self.assertEqual(d['status'],'live')
    def test_source_overview_does_not_dump_market_array(self):
        payload={'time':1000,'levels':[[{'px':'99','sz':'2'}],[{'px':'101','sz':'1'}]]}
        def fake(url,payload=None,timeout=5):
            if url==api.HL_INFO:return {'time':1000,'levels':[[{'px':'99','sz':'2'}],[{'px':'101','sz':'1'}]]}
            if url.endswith('/v1/market'):return [{'symbol':'BTC','price':10}]
            return {'status':'ok'}
        with patch.object(api,'source_json',side_effect=fake):
            x=api.source_status('BTC')
        self.assertEqual(x['hyperdata_market']['rows'],1)
        self.assertNotIn('data',x['hyperdata_market'])
    def test_protobuf_envelope_contract(self):
        import struct
        pair=fb(1,b'binancef')+fb(2,b'btcusdt')
        level=fv(1,1000) # This field is not a double: decoder must reject.
        frame=fb(1,pair)+fv(2,3)+fb(4,level)
        p=decode_payload(frame)
        self.assertEqual(p['exchange'],'binancef')
        self.assertEqual(p['stream'],3)
        with self.assertRaises(ValueError):decode_book(fb(2,level))
    def test_proto3_omitted_zero_size_is_book_deletion(self):
        import struct
        # A proto3 BookLevel with size=0 serializes only its nonzero price.
        level=vi(1<<3|1)+struct.pack('<d',80744.8)
        frame=fb(2,level)
        decoded=decode_book(frame)
        self.assertEqual(decoded['asks'],[(80744.8,0.0)])
        book=BookState()
        book.apply({'snapshot':True,'bids':[(80744.8,2.0)],'asks':[(80744.9,2.0)],'last':1,'first':1,'previous':0})
        book.apply({'snapshot':False,'bids':[(80744.8,0.0)],'asks':[],'last':2,'first':2,'previous':1})
        self.assertNotIn(80744.8,book.bids)

    def test_future_timestamp_rejected(self):
        obj={'time':30000,'levels':[[{'px':'99','sz':'2'}],[{'px':'101','sz':'1'}]]}
        self.assertEqual(summarize_l2(obj,now_ms=20000)['status'],'invalid')
    def test_missing_hyperliquid_depth_explicit(self):
        with patch.object(api,'source_json',side_effect=TimeoutError):
            self.assertEqual(api.hyperliquid_depth('BTC')['status'],'unavailable')

if __name__=='__main__':unittest.main()
