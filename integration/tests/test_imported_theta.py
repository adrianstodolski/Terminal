import sys
import math
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analytics import position_plan, historical_breakouts
from indicator_lab import indicator_snapshot, rsi
from advanced_indicators import advanced_snapshot
from strategy_lab import compare_strategies

def candles(n=400):
    out = []
    for i in range(n):
        c = 100 + i * .03 + math.sin(i * .4) * 1.5
        if i % 75 in (50, 51, 52):
            c += 3
        out.append({'t':i*300000,'o':c-.1,'h':c+.7,'l':c-.7,'c':c})
    return out

class ImportedThetaSmokeTests(unittest.TestCase):
    def test_position_sizing(self):
        result = position_plan(100, 99, 1000, .01, 2)
        self.assertAlmostEqual(result['quantity'], 10)
        self.assertAlmostEqual(result['stop_loss_usd'], 10)

    def test_bad_risk_rejected(self):
        with self.assertRaises(ValueError):
            position_plan(100, 100, 1000)

    def test_indicators(self):
        rows = candles()
        basic = indicator_snapshot(rows)
        advanced = advanced_snapshot(rows)
        self.assertTrue(math.isfinite(basic['atr14']))
        self.assertIn(advanced['consensus']['bias'], ('LONG','SHORT','WAIT'))

    def test_rsi_flat(self):
        self.assertEqual(rsi([100.0] * 40)[-1], 50.0)

    def test_gaps_rejected(self):
        rows = candles()
        rows.pop(12)
        with self.assertRaises(ValueError):
            indicator_snapshot(rows)

    def test_breakout_analysis(self):
        result = historical_breakouts(candles(), 'LONG')
        self.assertIn('trades', result)

    def test_strategy_comparison(self):
        result = compare_strategies(candles())
        self.assertLessEqual(result['indicator_filtered']['trades'], result['base']['trades'])

if __name__ == '__main__':
    unittest.main()
