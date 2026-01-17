import unittest
from stock_live_comparison import StockLiveComparison

class TestStockLiveComparison(unittest.TestCase):
    def test_get_default_tickers_valid(self):
        """Test that get_default_tickers returns a valid list of strings."""
        tickers = StockLiveComparison.get_default_tickers()
        
        # Check type
        self.assertIsInstance(tickers, list)
        
        # Check content types
        for t in tickers:
            self.assertIsInstance(t, str)
            self.assertTrue(len(t) > 0)
            
        # Check it is sorted
        self.assertEqual(tickers, sorted(tickers))
        
        # Check specific known tickers exist
        expected_subset = ["AAPL", "GOOG", "MSFT", "^SPX"]
        for expected in expected_subset:
            self.assertIn(expected, tickers)
            
        # Verify length is reasonable (at least 10)
        self.assertGreater(len(tickers), 10)

if __name__ == '__main__':
    unittest.main()
