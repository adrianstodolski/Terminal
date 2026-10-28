import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from gateway_depth import BookState

def packet(snapshot,last,first=0,previous=0,bids=None,asks=None):
    return dict(snapshot=snapshot,last=last,first=first,previous=previous,
                bids=[] if bids is None else bids,asks=[] if asks is None else asks)

class BookResyncTests(unittest.TestCase):
    def test_first_diff_overlaps_snapshot(self):
        book=BookState()
        self.assertTrue(book.apply(packet(True,100,bids=[(100.0,2)],asks=[(101.0,3)])))
        self.assertTrue(book.apply(packet(False,105,first=99,previous=97,bids=[(100.0,4)])))
        self.assertEqual(book.gaps,0)
        self.assertTrue(book.ready)
    def test_gap_is_unusable_until_fresh_snapshot(self):
        book=BookState()
        book.apply(packet(True,100,bids=[(100.0,2)],asks=[(101.0,3)]))
        book.apply(packet(False,101,first=101,previous=100))
        self.assertFalse(book.apply(packet(False,105,first=105,previous=102)))
        self.assertTrue(book.resync_requested)
        self.assertEqual(book.report()['status'],'waiting_snapshot')
        self.assertTrue(book.apply(packet(True,108,bids=[(100.0,2)],asks=[(101.0,3)])))
        self.assertFalse(book.resync_requested)
    def test_duplicate_is_not_gap(self):
        book=BookState()
        book.apply(packet(True,100,bids=[(100.0,2)],asks=[(101.0,3)]))
        self.assertFalse(book.apply(packet(False,99,first=99,previous=98)))
        self.assertEqual(book.gaps,0)

if __name__=='__main__': unittest.main()
