from app.models import TradeRecord
from app.services.trade_analysis import calculate_pnl

t1 = TradeRecord(trade_id="1", symbol="AAPL", quantity=10, trade_price=100.0)
t2 = TradeRecord(trade_id="2", symbol="AAPL", quantity=-10, trade_price=110.0)

print("Running calculate_pnl...")
res = calculate_pnl([t1, t2])
print("Done!")
print(res)
