"""
Runnable checks for spotify_sync — no network, no DB.

    python test_spotify_sync.py   # exits non-zero on failure

Covers the two pieces with real logic: rate-limit backoff (the "survives a
rate-limit storm" exit criterion) and fuzzy name matching.
"""

from spotipy.exceptions import SpotifyException

import spotify_sync as s


class FakeSpotify:
    """Raises 429 `fail_times` times, then returns `items` once."""

    def __init__(self, items, fail_times=0):
        self.items = items
        self.fail_times = fail_times
        self.calls = 0

    def search(self, q, type, limit, offset):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise SpotifyException(429, -1, "rate limited",
                                   headers={"Retry-After": "0"})
        # Only page 0 has results in these tests.
        items = self.items if offset == 0 else []
        return {"artists": {"items": items}}


def test_backoff_recovers_from_429():
    fake = FakeSpotify([{"name": "Hozier", "id": "x", "popularity": 80}], fail_times=3)
    items = s.search_page(fake, "Hozier", offset=0)
    assert items and items[0]["id"] == "x"
    assert fake.calls == 4, f"expected 3 retries + 1 success, got {fake.calls}"


def test_backoff_gives_up_after_max_attempts():
    fake = FakeSpotify([], fail_times=99)
    try:
        s.search_page(fake, "Whoever", offset=0)
    except SpotifyException:
        assert fake.calls == 6, f"expected 6 attempts, got {fake.calls}"
    else:
        raise AssertionError("expected SpotifyException after exhausting retries")


def test_match_score_exact_and_diacritics():
    assert s.match_score("Beyoncé", "Beyonce") == 1.0          # diacritics stripped
    assert s.match_score("The Strokes", "the strokes!") == 1.0  # case/punct ignored
    assert s.match_score("Hozier", "Drake") < 0.5


def test_best_match_breaks_ties_on_popularity():
    items = [
        {"name": "Twin", "id": "low", "popularity": 10},
        {"name": "Twin", "id": "high", "popularity": 90},
    ]
    best, score = s.best_match(items, "Twin")
    assert score == 1.0 and best["id"] == "high"


def test_best_match_handles_null_popularity_tie():
    # 2026: popularity comes back null — tie-break must not TypeError.
    items = [
        {"name": "Twin", "id": "a", "popularity": None},
        {"name": "Twin", "id": "b", "popularity": None},
    ]
    best, score = s.best_match(items, "Twin")
    assert score == 1.0 and best["id"] == "a"  # first wins when both null


def test_search_artist_picks_best_across_results():
    items = [
        {"name": "Hozer", "id": "a", "popularity": 50},
        {"name": "Hozier", "id": "b", "popularity": 70},
    ]
    fake = FakeSpotify(items)
    best, score = s.search_artist(fake, "Hozier")
    assert best["id"] == "b" and score == 1.0


def test_build_row_miss_has_no_spotify_fields():
    row = s.build_row("artist-123", None)
    assert row["artist_id"] == "artist-123"
    assert row["spotify_id"] is None and row["genres"] == []
    assert "fetched_at" in row and "expires_at" not in row  # trigger owns expires_at


def test_build_row_coalesce_keeps_known_value_over_fresh_null():
    # 2026 reality: a fresh search item with null stats must NOT wipe good data.
    prev = {"spotify_id": "sp1", "popularity": 70, "followers": 9000,
            "genres": ["indie"], "image_url": "http://old"}
    thin = {"id": "sp1", "name": "Act"}  # no popularity/followers/genres/images
    row = s.build_row("a1", thin, prev)
    assert row["popularity"] == 70 and row["followers"] == 9000
    assert row["genres"] == ["indie"] and row["image_url"] == "http://old"


def test_build_row_coalesce_prefers_fresh_value():
    prev = {"popularity": 70}
    fresh = {"id": "sp1", "popularity": 88, "followers": {"total": 1}}
    assert s.build_row("a1", fresh, prev)["popularity"] == 88


def test_build_row_miss_keeps_prev_match():
    # A flaky empty search shouldn't downgrade a previously matched artist.
    prev = {"spotify_id": "sp1", "popularity": 50}
    row = s.build_row("a1", None, prev)
    assert row["spotify_id"] == "sp1" and row["popularity"] == 50


def test_build_row_hit_maps_fields():
    item = {"id": "sp1", "popularity": 65, "genres": ["indie"],
            "followers": {"total": 1234}, "images": [{"url": "http://img"}]}
    row = s.build_row("artist-9", item)
    assert row["spotify_id"] == "sp1"
    assert row["followers"] == 1234 and row["popularity"] == 65
    assert row["genres"] == ["indie"] and row["image_url"] == "http://img"
    assert row["preview_url"] is None  # 2026: no top-tracks endpoint


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"\n{len(tests)} checks passed.")
