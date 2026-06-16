"""Unit tests for the Unicode-aware topic clustering (Bug A).

Verifies that:
- Japanese / CJK text produces non-empty tokens
- build_keyword_candidates returns candidates for a Japanese-memory set
- English behaviour is unchanged
"""

from collections import Counter
from unittest.mock import patch

from private_internet.content import topic_clustering as tc


# ── _tokenize: Unicode-aware token extraction ────────────────────────────────

class TestTokenizeUnicode:
    def test_japanese_text_produces_tokens(self):
        text = "東京で中学校の教師をしています"
        tokens = tc._tokenize(text)
        assert tokens, "Japanese text must produce at least one token"

    def test_japanese_contains_cjk_chars(self):
        text = "東京で中学校の教師をしています"
        tokens = tc._tokenize(text)
        # Every individual CJK character should appear as a token
        cjk_tokens = [t for t in tokens if len(t) == 1 and "一" <= t <= "鿿"]
        assert cjk_tokens, "CJK ideographs should be emitted as individual tokens"

    def test_japanese_sentence_multiple_tokens(self):
        # A rich sentence should yield multiple distinct tokens
        text = "東京で中学校の教師をしています"
        tokens = tc._tokenize(text)
        assert len(set(tokens)) >= 3, "expected at least 3 distinct tokens from a Japanese sentence"

    def test_mixed_japanese_english(self):
        text = "東京 is my home city"
        tokens = tc._tokenize(text)
        # English words should still appear
        assert "home" in tokens or "city" in tokens
        # CJK chars should also appear
        cjk = [t for t in tokens if not t.isascii()]
        assert cjk, "CJK chars should be present alongside English tokens"

    def test_cyrillic_text_produces_tokens(self):
        text = "Москва — столица России"
        tokens = tc._tokenize(text)
        assert tokens, "Cyrillic text must produce at least one token"
        cyr = [t for t in tokens if not t.isascii()]
        assert cyr, "Cyrillic tokens should be present"

    def test_english_stopwords_filtered(self):
        tokens = tc._tokenize("the cat sat on the mat and")
        # 'the', 'and' are stopwords and must be excluded
        assert "the" not in tokens
        assert "and" not in tokens
        # 'cat', 'sat', 'mat' should be kept
        assert "cat" in tokens
        assert "sat" in tokens

    def test_short_latin_tokens_filtered(self):
        # Latin tokens shorter than 3 chars should be excluded
        tokens = tc._tokenize("I go to the gym every day")
        assert "go" not in tokens   # 2 chars → excluded
        assert "to" not in tokens   # 2 chars → excluded
        assert "gym" in tokens      # 3 chars → kept

    def test_empty_text_returns_empty(self):
        assert tc._tokenize("") == []

    def test_ascii_digits_only_not_token(self):
        # Purely numeric tokens from ASCII should not appear (len < 3 for 1-2 digits,
        # and \w matches digits too — but they shouldn't survive stopword/length filter
        # for 1-2 digit runs)
        tokens = tc._tokenize("1 12 word")
        assert "1" not in tokens
        assert "12" not in tokens


# ── build_keyword_candidates: Japanese memory set ────────────────────────────

class TestBuildKeywordCandidatesJapanese:
    def test_japanese_memory_set_produces_candidates(self, monkeypatch):
        """Non-Latin memories must produce non-empty topic candidates."""
        import math

        def _unit(v):
            return tc._normalize(v)

        # Three distinct clusters in embedding space with Japanese text.
        mems = []
        # Cluster A: education / school theme (axis 1)
        for i in range(8):
            mems.append({
                "id": f"edu{i}",
                "title": "中学校の授業",
                "content": "東京で中学校の教師をしています。生徒たちの成長を見守ることが喜びです。",
                "tags": ["教育", "学校"],
                "vec": _unit([1.0, 0.02 * i, 0.0]),
            })
        # Cluster B: technology theme (axis 2)
        for i in range(8):
            mems.append({
                "id": f"tech{i}",
                "title": "プログラミング学習",
                "content": "Pythonを使ってウェブ開発を学んでいます。GitHubでプロジェクトを公開しました。",
                "tags": ["プログラミング", "技術"],
                "vec": _unit([0.02 * i, 1.0, 0.0]),
            })

        monkeypatch.setattr(
            tc, "fetch_memory_vectors", lambda user_id, limit=tc.MAX_MEMORIES: mems
        )
        monkeypatch.setattr(tc, "_choose_k", lambda n: 2)

        candidates = tc.build_keyword_candidates("user-jp-1")
        assert candidates, "expected at least one candidate from Japanese memories"
        # Every candidate must have at least one non-empty keyword
        for c in candidates:
            assert c["keywords"], f"candidate has empty keywords: {c}"

    def test_japanese_tokens_in_keywords(self, monkeypatch):
        """Keywords extracted from Japanese text should include CJK characters."""
        import math

        def _unit(v):
            return tc._normalize(v)

        mems = []
        for i in range(6):
            mems.append({
                "id": f"m{i}",
                "title": "東京の交通",
                "content": "電車とバスで通勤しています。東京の電車は時間通りです。",
                "tags": ["東京", "交通"],
                "vec": _unit([1.0, 0.01 * i]),
            })

        monkeypatch.setattr(
            tc, "fetch_memory_vectors", lambda user_id, limit=tc.MAX_MEMORIES: mems
        )
        monkeypatch.setattr(tc, "_choose_k", lambda n: 1)

        candidates = tc.build_keyword_candidates("user-jp-2")
        assert candidates
        all_kws = [kw for c in candidates for kw in c["keywords"]]
        # At least some keywords should be CJK characters or multi-char CJK tokens
        non_ascii_kws = [k for k in all_kws if not k.isascii()]
        assert non_ascii_kws, (
            f"expected CJK keywords from Japanese text, got: {all_kws}"
        )


# ── Regression: English behaviour unchanged ──────────────────────────────────

class TestEnglishBehaviourUnchanged:
    def test_english_tokenize_unchanged(self):
        text = "machine learning model training neural network"
        tokens = tc._tokenize(text)
        assert "machine" in tokens
        assert "learning" in tokens
        assert "model" in tokens
        assert "training" in tokens
        assert "neural" in tokens
        assert "network" in tokens

    def test_distinctive_still_works_with_ascii(self):
        cluster = Counter({"python": 5, "machine": 4, "common": 3})
        other = Counter({"common": 30, "python": 0, "machine": 1})
        glob = cluster + other
        kws = tc._distinctive(cluster, glob, top=2)
        assert "python" in kws
        assert "common" not in kws
