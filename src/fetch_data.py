"""
Thu thập dữ liệu tài chính từ yfinance.
Dữ liệu được trả về dạng list[dict] với cấu trúc:
  {
    "ticker": "AAPL",
    "source": "financials" | "news" | "info",
    "content": "...",
    "date": "2024-01-15"
  }
"""
import json
from pathlib import Path
import yfinance as yf
from loguru import logger

DEFAULT_TICKERS = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]

def fetch_from_yfinance(tickers: list[str] = None) -> list[dict]:
    """Fetch thông tin tài chính + tin tức từ yfinance."""
    tickers = tickers or DEFAULT_TICKERS
    documents = []

    for ticker_symbol in tickers:
        logger.info(f"Fetching data for {ticker_symbol}")
        ticker = yf.Ticker(ticker_symbol)

        # 1. Thông tin công ty
        try:
            info = ticker.info
            if info.get("longBusinessSummary"):
                documents.append({
                    "ticker": ticker_symbol,
                    "source": "company_info",
                    "content": f"Company: {info.get('longName', ticker_symbol)}. "
                               f"Sector: {info.get('sector', 'N/A')}. "
                               f"Industry: {info.get('industry', 'N/A')}. "
                               f"Summary: {info['longBusinessSummary']}",
                    "date": None,
                })
        except Exception as e:
            logger.warning(f"Failed to fetch info for {ticker_symbol}: {e}")

        # 2. Tin tức gần đây
        try:
            news = ticker.news
            for article in news[:5]:  # Lấy 5 tin mới nhất
                title = article.get("title", "")
                link = article.get("link", "")
                publisher = article.get("publisher", "")
                if title:
                    documents.append({
                        "ticker": ticker_symbol,
                        "source": "news",
                        "content": f"[{publisher}] {title}. Link: {link}",
                        "date": None,
                    })
        except Exception as e:
            logger.warning(f"Failed to fetch news for {ticker_symbol}: {e}")

    logger.info(f"Total documents fetched: {len(documents)}")
    return documents

def fetch_from_json(file_path: str) -> list[dict]:
    """Load dữ liệu từ file JSON local."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    logger.info(f"Loaded {len(data)} documents from {file_path}")
    return data

def validate_documents(documents: list[dict]) -> list[dict]:
    """Validate và lọc bỏ documents không hợp lệ."""
    valid = []
    for doc in documents:
        if not doc.get("content") or not doc["content"].strip():
            logger.warning(f"Skipping empty document: {doc.get('ticker', 'unknown')}")
            continue
        if not doc.get("ticker"):
            logger.warning("Skipping document without ticker")
            continue
        valid.append(doc)

    logger.info(f"Validated: {len(valid)}/{len(documents)} documents passed")
    return valid