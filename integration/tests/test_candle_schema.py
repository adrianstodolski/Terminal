import json,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import api

class FakeResponse:
    def __init__(self,payload):self.payload=payload
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,*args):return json.dumps(self.payload).encode()

class ApiSchemaRegression(unittest.TestCase):
    def test_hyperliquid_candles_normalize_to_internal_format(self):
        step=300000;now=600*step
        payload=[{'t':i*step,'T':(i+1)*step-1,'o':'100','h':'101','l':'99','c':'100.5'} for i in range(500,601)]
        with patch.object(api.time,'time',return_value=now/1000),patch.object(api,'urlopen',return_value=FakeResponse(payload)):
            result=api.fetch_candles('BTC','5m')
        self.assertEqual(len(result),100)
        self.assertEqual(set(result[0]),{'t','o','h','l','c'})
        self.assertEqual(result[-1]['t'],(now//step-1)*step)
    def test_incomplete_candles_excluded(self):
        step=300000;now=600*step+10
        payload=[{'t':i*step,'T':(i+1)*step-1,'o':'100','h':'101','l':'99','c':'100.5'} for i in range(500,601)]
        with patch.object(api.time,'time',return_value=now/1000),patch.object(api,'urlopen',return_value=FakeResponse(payload)):
            result=api.fetch_candles('BTC','5m')
        self.assertEqual(result[-1]['t'],599*step)

if __name__=='__main__': unittest.main()
