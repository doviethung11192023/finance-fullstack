"""
Integration Tests cho FastAPI endpoints.
Sử dụng TestClient để giả lập HTTP requests.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

class TestHealthEndpoints:
    def test_liveness_returns_200(self):
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert "timestamp" in data

    @patch("src.health._check_database", return_value=True)
    @patch("src.health._check_gemini", return_value=True)
    def test_readiness_all_healthy(self, mock_gemini, mock_db):
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    @patch("src.health._check_database", return_value="Connection refused")
    @patch("src.health._check_gemini", return_value=True)
    def test_readiness_db_down_returns_503(self, mock_gemini, mock_db):
        response = client.get("/health/ready")
        assert response.status_code == 503

class TestQueryEndpoint:
    @patch("src.main.query_rag")
    def test_query_success(self, mock_rag):
        mock_rag.return_value = {
            "answer": "Apple là công ty công nghệ hàng đầu thế giới.",
            "sources": [
                {
                    "ticker": "AAPL",
                    "source": "company_info",
                    "similarity": 0.92,
                    "preview": "Apple Inc is a technology company...",
                }
            ],
            "query": "Apple là gì?",
        }

        response = client.post("/query", json={"question": "Apple là gì?"})
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert len(data["sources"]) > 0
        assert data["sources"][0]["ticker"] == "AAPL"

    def test_query_empty_question_returns_422(self):
        response = client.post("/query", json={"question": ""})
        assert response.status_code == 422

    def test_query_missing_body_returns_422(self):
        response = client.post("/query")
        assert response.status_code == 422

class TestMetricsEndpoint:
    def test_metrics_endpoint_exists(self):
        response = client.get("/metrics")
        assert response.status_code == 200
        # Prometheus metrics format
        assert "http_requests_total" in response.text or "HELP" in response.text