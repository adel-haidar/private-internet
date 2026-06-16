"""Emergent topic discovery from a user's memory embeddings — privacy-first.

The old approach took the 20 most-recent memories and sent their full text to an
LLM, which (a) biased toward whatever was uploaded most and (b) shipped raw
private content to the cloud.

This module instead works on the **Titan embeddings already stored in pgvector**:

1. Cluster all of a user's memory vectors (spherical k-means, pure Python — no
   numpy/sklearn dependency, so it also runs on cheap self-host hardware).
2. Extract **distinctive keywords** for each cluster locally (TF over the cluster
   vs. the rest), so 30 medical documents collapse into ONE theme instead of 30.
3. Detect **emergent intersections** — pairs of clusters bridged by memories that
   sit between both (e.g. a "cars" cluster and a "Japan" cluster bridged into
   "Japanese cars").

The output is a list of **keyword sets** — never raw memory text. The labeling
step (topic_intelligence) sends only these keywords to Bedrock, so memories
never leave the box.  # MUST SCOPE BY USER
"""

import logging
import math
import random
import re
from collections import Counter, defaultdict
from operator import mul

from psycopg2.extras import RealDictCursor

from private_internet.database import _connect

logger = logging.getLogger(__name__)

# ── Tunables (thresholds are heuristic; safe to tune against real data) ───────
MAX_MEMORIES = 400          # cap vectors per run (cost control for pure-Python k-means)
KMEANS_ITERS = 12
MIN_CLUSTER_SIZE = 2        # ignore singleton clusters as standalone topics
MIN_FOR_INTERSECTIONS = 8   # need enough data before intersections are meaningful
BRIDGE_TAU = 0.45           # min similarity to the 2nd-nearest centroid to "bridge"
BRIDGE_GAP = 0.20           # 1st vs 2nd centroid similarity must be close
MIN_BRIDGES = 2             # how many bridging memories make an intersection real
SAME_TOPIC_MAX = 0.85       # centroids more similar than this are the same topic
MAX_CANDIDATES = 6          # cap LLM labeling calls per run
KEYWORDS_PER_CLUSTER = 8

# Unicode-aware word token: matches word characters across all scripts (Latin,
# Cyrillic, Arabic, Kana, Hangul, …) plus embedded apostrophes/hyphens.
# Minimum length 3 characters is enforced in _tokenize(), not the regex itself,
# because CJK characters carry meaning even at length 1.
_TOKEN_RE = re.compile(r"\w[\w'\-]*", re.UNICODE)

# Regex that matches a single CJK ideograph or kana character. We emit each
# character as an individual token so clustering has signal even when the text
# has no spaces (Japanese, Chinese, Korean run words together).
_CJK_RE = re.compile(
    r"[぀-ゟ"   # hiragana
    r"゠-ヿ"   # katakana
    r"一-鿿"   # CJK unified ideographs (common)
    r"㐀-䶿"   # CJK extension A
    r"가-힯"   # Hangul syllables
    r"]",
    re.UNICODE,
)

_STOPWORDS = {
    "the", "and", "for", "are", "but", "not", "you", "your", "with", "this", "that",
    "have", "has", "had", "was", "were", "will", "would", "could", "should", "from",
    "they", "their", "them", "what", "when", "where", "which", "while", "about",
    "into", "than", "then", "there", "here", "been", "being", "also", "more", "most",
    "some", "such", "very", "just", "like", "over", "after", "before", "because",
    "memory", "memories", "note", "notes", "today", "http", "https", "www", "com",
    "really", "thing", "things", "much", "many", "make", "made", "want", "need",
    "get", "got", "one", "two", "use", "used", "via", "per", "etc",
}


# ── Vector helpers (pure Python) ─────────────────────────────────────────────
def _parse_vec(raw) -> list[float] | None:
    if raw is None:
        return None
    if isinstance(raw, (list, tuple)):
        return [float(x) for x in raw]
    s = str(raw).strip()
    if s.startswith("["):
        s = s[1:]
    if s.endswith("]"):
        s = s[:-1]
    if not s:
        return None
    try:
        return [float(x) for x in s.split(",")]
    except ValueError:
        return None


def _normalize(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def _dot(a: list[float], b: list[float]) -> float:
    return sum(map(mul, a, b))


def _mean(vectors: list[list[float]]) -> list[float]:
    d = len(vectors[0])
    s = [0.0] * d
    for v in vectors:
        for i in range(d):
            s[i] += v[i]
    n = len(vectors)
    return [x / n for x in s]


# ── Data access ──────────────────────────────────────────────────────────────
def fetch_memory_vectors(user_id: str, limit: int = MAX_MEMORIES) -> list[dict]:
    """Most-recent `limit` memories that have an embedding.  # MUST SCOPE BY USER"""
    assert user_id is not None, "user_id must be set before any content operation"
    conn = _connect()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            """SELECT memory_id, title, content, tags, created_at, embedding
               FROM memories
               WHERE user_id = %s AND embedding IS NOT NULL AND merged_into IS NULL
               ORDER BY created_at DESC
               LIMIT %s""",
            (user_id, limit),
        )
        rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    out: list[dict] = []
    for r in rows:
        vec = _parse_vec(r["embedding"])
        if not vec:
            continue
        out.append({
            "id": r["memory_id"],
            "title": r["title"] or "",
            "content": r["content"] or "",
            "tags": [t.strip() for t in (r["tags"] or "").split(",") if t.strip()],
            "vec": vec,
        })
    return out


# ── k-means (spherical: vectors are L2-normalized, similarity = dot) ──────────
def _kmeans(vectors: list[list[float]], k: int, iters: int = KMEANS_ITERS, seed: int = 42):
    rnd = random.Random(seed)
    n = len(vectors)
    if k <= 1 or n <= k:
        return [0] * n if k <= 1 else list(range(n)), [vectors[0] if k <= 1 else v for v in (vectors[:k] or [vectors[0]])]

    # k-means++ seeding using cosine distance (1 - similarity).
    centers = [vectors[rnd.randrange(n)]]
    while len(centers) < k:
        weights = []
        for v in vectors:
            nearest = max(_dot(v, c) for c in centers)
            d = max(0.0, 1.0 - nearest)
            weights.append(d * d)
        total = sum(weights) or 1.0
        target = rnd.random() * total
        acc = 0.0
        pick = 0
        for i, w in enumerate(weights):
            acc += w
            if acc >= target:
                pick = i
                break
        centers.append(vectors[pick])

    labels = [0] * n
    for _ in range(iters):
        changed = False
        for i, v in enumerate(vectors):
            best, bi = -2.0, 0
            for ci, c in enumerate(centers):
                s = _dot(v, c)
                if s > best:
                    best, bi = s, ci
            if labels[i] != bi:
                labels[i] = bi
                changed = True
        groups: dict[int, list[list[float]]] = defaultdict(list)
        for i, lab in enumerate(labels):
            groups[lab].append(vectors[i])
        centers = [
            _normalize(_mean(groups[ci])) if groups[ci] else vectors[rnd.randrange(n)]
            for ci in range(k)
        ]
        if not changed:
            break
    return labels, centers


def _choose_k(n: int) -> int:
    return max(1, min(8, round(math.sqrt(n / 2)) or 1))


# ── Keyword extraction (local, distinctive terms) ────────────────────────────
def _tokenize(text: str) -> list[str]:
    """Return a list of meaningful tokens from `text`, Unicode-aware.

    For Latin/Cyrillic/Arabic scripts: split on word boundaries and keep tokens
    >= 3 characters that are not in the English stopword list.

    For CJK scripts (Japanese, Chinese, Korean): also emit individual characters
    as tokens, since there are no spaces between words — even single ideographs
    carry meaning and give the k-means clustering useful signal.
    """
    tokens: list[str] = []
    # 1. General multi-character tokens (applies to all scripts).
    for t in _TOKEN_RE.findall(text):
        tl = t.lower()
        # Apply English stopwords only to ASCII tokens (Latin script).
        if tl.isascii():
            if len(tl) < 3 or tl in _STOPWORDS:
                continue
        else:
            if len(tl) < 2:
                continue
        tokens.append(tl)
    # 2. Individual CJK characters as supplementary tokens so zero-space scripts
    #    are not silent when _TOKEN_RE produces only long multi-char runs.
    for ch in _CJK_RE.findall(text):
        tokens.append(ch)
    return tokens


def _cluster_token_counts(member_idxs: list[int], mems: list[dict]) -> Counter:
    c: Counter = Counter()
    for i in member_idxs:
        m = mems[i]
        for tag in m["tags"]:
            for tok in _tokenize(tag):
                c[tok] += 3          # tags are strong signal
        for tok in _tokenize(m["title"]):
            c[tok] += 2
        for tok in _tokenize(m["content"]):
            c[tok] += 1
    return c


def _distinctive(cluster_c: Counter, global_c: Counter, top: int) -> list[str]:
    scored: list[tuple[float, int, str]] = []
    for tok, f in cluster_c.items():
        other = global_c[tok] - f
        score = f / (1.0 + other)          # frequent here, rare elsewhere
        scored.append((score, f, tok))
    scored.sort(reverse=True)
    return [tok for _, _, tok in scored[:top]]


# ── Orchestration ────────────────────────────────────────────────────────────
def build_keyword_candidates(user_id: str) -> list[dict]:
    """Return candidate topic keyword-sets (no raw memory text).

    Each candidate: {keywords: list[str], source_ids: list[str], kind: 'cluster'|'intersection'}
    """
    mems = fetch_memory_vectors(user_id)
    if not mems:
        return []

    norm = [_normalize(m["vec"]) for m in mems]
    n = len(mems)
    k = _choose_k(n)
    labels, centers = _kmeans(norm, k)

    groups: dict[int, list[int]] = defaultdict(list)
    for i, lab in enumerate(labels):
        groups[lab].append(i)

    cluster_counts = {ci: _cluster_token_counts(idxs, mems) for ci, idxs in groups.items()}
    global_counts: Counter = Counter()
    for c in cluster_counts.values():
        global_counts.update(c)

    cluster_keywords = {
        ci: _distinctive(cluster_counts[ci], global_counts, KEYWORDS_PER_CLUSTER)
        for ci in groups
    }

    candidates: list[dict] = []

    # 1. Emergent intersections first (the genuinely novel topics).
    for (a, b), bridge_idxs in _detect_intersections(centers, norm, labels, groups):
        kw = _merge_keywords(cluster_keywords.get(a, []), cluster_keywords.get(b, []))
        if not kw:
            continue
        src = [mems[i]["id"] for i in bridge_idxs[:5]]
        candidates.append({"keywords": kw, "source_ids": src, "kind": "intersection"})

    # 2. Single-theme clusters, largest first.
    for ci in sorted(groups, key=lambda c: len(groups[c]), reverse=True):
        if len(groups[ci]) < MIN_CLUSTER_SIZE and n > MIN_CLUSTER_SIZE:
            continue
        kw = cluster_keywords.get(ci, [])
        if not kw:
            continue
        src = [mems[i]["id"] for i in groups[ci][:5]]
        candidates.append({"keywords": kw, "source_ids": src, "kind": "cluster"})

    return candidates[:MAX_CANDIDATES]


def _merge_keywords(a: list[str], b: list[str], per_side: int = 4) -> list[str]:
    out: list[str] = []
    for tok in a[:per_side] + b[:per_side]:
        if tok not in out:
            out.append(tok)
    return out


def _detect_intersections(centers, norm, labels, groups) -> list[tuple[tuple[int, int], list[int]]]:
    k = len(centers)
    n = len(norm)
    if n < MIN_FOR_INTERSECTIONS or k < 2:
        return []

    bridges: dict[tuple[int, int], list[int]] = defaultdict(list)
    for i, v in enumerate(norm):
        sims = sorted(((_dot(v, centers[ci]), ci) for ci in range(k)), reverse=True)
        (s1, c1), (s2, c2) = sims[0], sims[1]
        if s2 >= BRIDGE_TAU and (s1 - s2) <= BRIDGE_GAP:
            bridges[tuple(sorted((c1, c2)))].append(i)

    result: list[tuple[tuple[int, int], list[int]]] = []
    for pair, idxs in bridges.items():
        if len(idxs) < MIN_BRIDGES:
            continue
        if _dot(centers[pair[0]], centers[pair[1]]) > SAME_TOPIC_MAX:
            continue  # the two clusters are really the same theme
        result.append((pair, idxs))
    # most-bridged intersections first
    result.sort(key=lambda r: len(r[1]), reverse=True)
    return result
