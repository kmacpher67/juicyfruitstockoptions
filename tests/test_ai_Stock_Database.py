def test_upsert_and_setup(tmp_path, monkeypatch):
    # Use a test database
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017/test_stocklive")
    db = AiStockDatabase(db_name="test_stocklive", collection_name="test_stock_data")
    db.collection.delete_many({})  # Clean up before test

    record = {"Ticker": "TEST", "price": 100}
    db.upsert_stock_record(record)
    found = db.collection.find_one({"Ticker": "TEST"})
    assert found["price"] == 100

    # Test upsert_many
    records = [{"Ticker": "TEST2", "price": 200}, {"Ticker": "TEST3", "price": 300}]
    db.upsert_many(records)
    assert db.collection.count_documents({"Ticker": {"$in": ["TEST2", "TEST3"]}}) == 2