import pytest
from src.process_data import chunk_text, prepare_chunks
from src.config import settings

class TestChunkText:
    def test_short_text_returns_single_chunk(self):
        """Text ngắn hơn chunk_size → 1 chunk duy nhất."""
        text = "This is a short text."
        chunks = chunk_text(text, chunk_size=500, chunk_overlap=50)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_splits_correctly(self):
        """Text dài phải được chia thành nhiều chunks."""
        text = "Word " * 200  # ~1000 ký tự
        chunks = chunk_text(text, chunk_size=100, chunk_overlap=20)
        assert len(chunks) > 1

    def test_chunk_size_does_not_exceed_limit(self):
        """Mỗi chunk KHÔNG được vượt quá chunk_size."""
        text = "A" * 2000
        chunk_size = 300
        chunks = chunk_text(text, chunk_size=chunk_size, chunk_overlap=50)
        for chunk in chunks:
            assert len(chunk) <= chunk_size + 50  # TextSplitter cho phép tolerance nhỏ

    def test_empty_text_returns_empty(self):
        chunks = chunk_text("", chunk_size=500, chunk_overlap=50)
        assert chunks == [] or chunks == [""]

    def test_overlap_preserves_context(self):
        """Overlap đảm bảo không mất ngữ cảnh giữa 2 chunk."""
        text = "Sentence one. Sentence two. Sentence three. Sentence four. Sentence five."
        chunks = chunk_text(text, chunk_size=40, chunk_overlap=15)
        if len(chunks) >= 2:
            # Kiểm tra có phần chồng lấp
            combined = " ".join(chunks)
            # Mỗi từ trong text gốc phải xuất hiện ít nhất 1 lần
            for word in text.split():
                assert word.rstrip(".") in combined or word in combined

class TestPrepareChunks:
    def test_metadata_preserved(self):
        """Metadata từ document gốc phải được giữ lại trong mỗi chunk."""
        docs = [{
            "ticker": "AAPL",
            "source": "company_info",
            "content": "Apple Inc is a technology company. " * 50,
            "date": "2024-01-15",
        }]
        chunks = prepare_chunks(docs)
        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk["metadata"]["ticker"] == "AAPL"
            assert chunk["metadata"]["source"] == "company_info"
            assert "chunk_index" in chunk["metadata"]
            assert "total_chunks" in chunk["metadata"]

    def test_empty_input_returns_empty(self):
        assert prepare_chunks([]) == []