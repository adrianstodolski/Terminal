import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from market_fusion import summarize_l2,qualify_signal
from gateway_depth import BookState, decode_book, varint

class IntegrationSourceTests(unittest.TestCase):
 def test_hyperliquid_valid_l2(self):
  d=summarize_l2({'time':1000,'levels':[[{'px':'99','sz':'2'}],[{'px':'101','sz':'1'}]]},now_ms=2000)
  self.assertEqual(d['status'],'live')
  self.assertEqual(d['venue'],'Hyperliquid')
  self.assertGreater(d['near_imbalance'],0)
 def test_stale_book_is_not_confirmed(self):
  d=summarize_l2({'time':1000,'levels':[[{'px':'99','sz':'2'}],[{'px':'101','sz':'1'}]]},now_ms=20000)
  self.assertEqual(qualify_signal({'side':'LONG','status':'CONFIRMED'},d)['status'],'DEPTH_UNAVAILABLE')
 def test_binance_depth_cannot_confirm_hyperliquid(self):
  out=qualify_signal({'side':'LONG','status':'CONFIRMED'},{'venue':'Binance USD-M','status':'live','near_imbalance':1,'spread_bps':0})
  self.assertEqual(out['status'],'DEPTH_UNAVAILABLE')
 def test_crossed_book_invalid(self):
  d=summarize_l2({'time':1000,'levels':[[{'px':'101','sz':'1'}],[{'px':'100','sz':'2'}]]},now_ms=1000)
  self.assertEqual(d['status'],'invalid')
 def test_gateway_gap_needs_snapshot(self):
  b=BookState()
  self.assertTrue(b.apply({'snapshot':True,'bids':[(100.,1.)],'asks':[(101.,2.)],'last':10,'first':10,'previous':0}))
  self.assertFalse(b.apply({'snapshot':False,'bids':[(100.,3.)],'asks':[],'last':13,'first':13,'previous':9}))
  self.assertEqual(b.report()['status'],'waiting_snapshot')
  self.assertEqual(b.gaps,1)
 def test_varint_bounds(self):
  with self.assertRaises(ValueError):varint(b'\x80',0)

if __name__=='__main__':unittest.main()
