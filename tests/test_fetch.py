import pytest
from src.fetch_data import fetch_from_yfinance, fetch_from_json, validate_documents

class TestFetchFromYfinance:
    def test_returns_non_empty_list(self):
        """Kiểm tra fetch ít nhất trả về 1 document."""
        docs = fetch_from_yfinance(["AAPL"])
        assert isinstance(docs, list)
        assert len(docs) > 0

    def test_document_schema(self):
        """Kiểm tra mỗi document có đủ các trường bắt buộc."""
        docs = fetch_from_yfinance(["MSFT"])
        for doc in docs:
            assert "ticker" in doc
            assert "source" in doc
            assert "content" in doc
            assert isinstance(doc["content"], str)
            assert len(doc["content"]) > 0

    def test_invalid_ticker_does_not_crash(self):
        """Ticker không hợp lệ không được làm crash toàn bộ pipeline."""
        docs = fetch_from_yfinance(["INVALID_TICKER_XYZ"])
        assert isinstance(docs, list)  # Có thể rỗng nhưng không crash

class TestValidateDocuments:
    def test_filters_empty_content(self):
        docs = [
            {"ticker": "AAPL", "source": "info", "content": "Valid content"},
            {"ticker": "MSFT", "source": "info", "content": ""},
            {"ticker": "GOOGL", "source": "info", "content": "   "},
        ]
        valid = validate_documents(docs)
        assert len(valid) == 1

    def test_filters_missing_ticker(self):
        docs = [
            {"source": "info", "content": "No ticker here"},
            {"ticker": "AAPL", "source": "info", "content": "Has ticker"},
        ]
        valid = validate_documents(docs)
        assert len(valid) == 1

class TestFetchFromJson:
    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            fetch_from_json("nonexistent.json")