from app.services import groq_summarizer


def test_generate_comment_summary_returns_none_when_disabled(monkeypatch):
    monkeypatch.setattr(groq_summarizer, "ENABLE_GROQ_COMMENT_SUMMARY", False)
    monkeypatch.setattr(groq_summarizer, "GROQ_API_KEY", "test-key")

    result = groq_summarizer.generate_comment_summary({"comments_analyzed": 10})

    assert result is None


def test_generate_comment_summary_uses_groq_response(monkeypatch):
    monkeypatch.setattr(groq_summarizer, "ENABLE_GROQ_COMMENT_SUMMARY", True)
    monkeypatch.setattr(groq_summarizer, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(groq_summarizer, "GROQ_MODEL", "test-model")
    monkeypatch.setattr(groq_summarizer, "GROQ_TIMEOUT_SECONDS", 1.0)

    captured = {}

    class _Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {"message": {"content": "Several review patterns were noted. Read the reviews carefully."}}
                ]
            }

    def _fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return _Response()

    monkeypatch.setattr(groq_summarizer.httpx, "post", _fake_post)

    result = groq_summarizer.generate_comment_summary({"comments_analyzed": 12, "summary": "local"})

    assert result == "Several review patterns were noted. Read the reviews carefully."
    assert captured["url"].startswith("https://api.groq.com/openai/v1/chat/completions")
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["model"] == "test-model"


def test_generate_comment_summary_sanitizes_output(monkeypatch):
    monkeypatch.setattr(groq_summarizer, "ENABLE_GROQ_COMMENT_SUMMARY", True)
    monkeypatch.setattr(groq_summarizer, "GROQ_API_KEY", "test-key")

    class _Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {"message": {"content": '"One sentence only. Another sentence. Extra words. Extra words. Extra words."'}}
                ]
            }

    monkeypatch.setattr(groq_summarizer.httpx, "post", lambda *args, **kwargs: _Response())

    result = groq_summarizer.generate_comment_summary({"comments_analyzed": 5})

    assert result == "One sentence only. Another sentence."