"""Unit tests for the pure-Python topic clustering / intersection logic.

Uses small synthetic vectors so the maths is deterministic and DB/Bedrock-free.
"""

import math

from private_internet.content import topic_clustering as tc


def _unit(v):
    return tc._normalize(v)


def test_parse_vec_handles_pgvector_string():
    assert tc._parse_vec("[1,2,3]") == [1.0, 2.0, 3.0]
    assert tc._parse_vec("[]") is None
    assert tc._parse_vec(None) is None
    assert tc._parse_vec([0.5, 0.25]) == [0.5, 0.25]


def test_normalize_and_dot():
    v = _unit([3.0, 4.0])
    assert math.isclose(math.sqrt(v[0] ** 2 + v[1] ** 2), 1.0, rel_tol=1e-9)
    # orthogonal unit vectors -> dot 0; identical -> dot 1
    assert math.isclose(tc._dot(_unit([1, 0]), _unit([0, 1])), 0.0, abs_tol=1e-9)
    assert math.isclose(tc._dot(_unit([1, 1]), _unit([1, 1])), 1.0, rel_tol=1e-9)


def test_kmeans_separates_two_blobs():
    # Two tight blobs around orthogonal axes.
    blob_a = [_unit([1.0, 0.02 * i]) for i in range(6)]
    blob_b = [_unit([0.02 * i, 1.0]) for i in range(6)]
    vectors = blob_a + blob_b
    labels, centers = tc._kmeans(vectors, k=2, seed=1)
    # All of blob_a share one label, all of blob_b share the other.
    assert len(set(labels[:6])) == 1
    assert len(set(labels[6:])) == 1
    assert labels[0] != labels[6]


def test_choose_k_scales_with_n():
    assert tc._choose_k(1) == 1
    assert tc._choose_k(2) >= 1
    assert tc._choose_k(200) <= 8  # capped


def test_distinctive_prefers_cluster_specific_terms():
    from collections import Counter

    cluster = Counter({"toyota": 5, "japan": 4, "common": 3})
    other = Counter({"common": 30, "toyota": 0, "japan": 1})
    glob = cluster + other
    kws = tc._distinctive(cluster, glob, top=2)
    assert "toyota" in kws            # frequent here, absent elsewhere
    assert "common" not in kws        # frequent everywhere -> not distinctive


def test_build_keyword_candidates_clusters_and_intersects(monkeypatch):
    """End-to-end (sans DB): two themes + a bridge should yield cluster topics
    and an emergent intersection topic."""
    # Theme A ("cars"), Theme B ("japan"), and bridge memories near both axes.
    def mk(vec, title, tags):
        return {"id": f"m{title}", "title": title, "content": title, "tags": tags, "vec": vec}

    mems = []
    for i in range(10):
        mems.append(mk([1.0, 0.0, 0.03 * i], f"car{i}", ["cars", "engine"]))
    for i in range(10):
        mems.append(mk([0.0, 1.0, 0.03 * i], f"jp{i}", ["japan", "tokyo"]))
    # bridge: equally close to both car-axis and japan-axis
    for i in range(3):
        mems.append(mk([0.7, 0.7, 0.0], f"jdm{i}", ["cars", "japan", "import"]))

    monkeypatch.setattr(tc, "fetch_memory_vectors", lambda user_id, limit=tc.MAX_MEMORIES: mems)
    # Force k=2 so the two main axes are the clusters and bridges sit between them.
    monkeypatch.setattr(tc, "_choose_k", lambda n: 2)

    candidates = tc.build_keyword_candidates("user-1")
    assert candidates, "expected at least one candidate"
    kinds = {c["kind"] for c in candidates}
    assert "cluster" in kinds
    assert "intersection" in kinds, "bridge memories should produce an intersection"

    inter = next(c for c in candidates if c["kind"] == "intersection")
    # The intersection keyword set should draw from both themes.
    assert any(k in inter["keywords"] for k in ("cars", "engine"))
    assert any(k in inter["keywords"] for k in ("japan", "tokyo"))
