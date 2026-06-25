"""
test_aggregator.py — offline self-test for v3.2 ingestion at scale.
No DB, no network, no API keys. Run: python test_aggregator.py
Covers: target CSV parse · TM/SeatGeek normalize · cross-source merge ·
coalesce-forward festival merge · staleness rotation · TM lineup normalize ·
an end-to-end run() with a fake store using the coalesce merge.
"""

import datetime as dt

import ingest
import aggregator as agg
import lineup_adapter as la


# ── Fixtures ───────────────────────────────────────────────────
_LOLLA = agg.Target(slug="lollapalooza", name="Lollapalooza", tm_keyword="Lollapalooza",
                    seatgeek_query="Lollapalooza")

_TM_JSON = {"_embedded": {"events": [
    {"name": "Lollapalooza 2026", "dates": {"start": {"localDate": "2026-07-30"}},
     "_embedded": {"venues": [{"name": "Grant Park", "city": {"name": "Chicago"},
        "state": {"stateCode": "IL"},
        "location": {"latitude": "41.8765", "longitude": "-87.6213"}}]}},
    {"name": "Lollapalooza 2026", "dates": {"start": {"localDate": "2026-08-02"}},
     "_embedded": {"venues": [{"name": "Grant Park", "city": {"name": "Chicago"},
        "state": {"stateCode": "IL"},
        "location": {"latitude": "41.8765", "longitude": "-87.6213"}}]}},
    # aftershow → filtered out by the 'official'/'aftershow' markers
    {"name": "Lollapalooza Official Aftershow: A Band",
     "dates": {"start": {"localDate": "2026-07-31"}}, "_embedded": {"venues": [{}]}},
]}}

_SG_JSON = {"events": [
    {"title": "Lollapalooza", "datetime_local": "2026-07-30T12:00:00",
     "venue": {"name": "Grant Park", "city": "Chicago", "state": "IL",
               "location": {"lat": 41.8765, "lon": -87.6213}}},
    {"title": "Lollapalooza", "datetime_local": "2026-08-02T12:00:00",
     "venue": {"name": "Grant Park", "city": "Chicago", "state": "IL",
               "location": {"lat": 41.8765, "lon": -87.6213}}},
]}


# ── Target list ────────────────────────────────────────────────
def test_load_targets():
    targets = agg.load_targets()
    assert len(targets) >= 20, len(targets)
    slugs = {t.slug for t in targets}
    assert "lollapalooza" in slugs and "coachella" in slugs
    lolla = next(t for t in targets if t.slug == "lollapalooza")
    assert lolla.tier == "flagship" and lolla.tm_keyword == "Lollapalooza"
    # blank provider-query column falls back to the display name
    t = agg.Target(slug="x", name="X Fest")
    assert t.tm_keyword == "X Fest" and t.seatgeek_query == "X Fest"


# ── Provider normalize ─────────────────────────────────────────
def test_normalize_tm():
    c = agg.normalize_tm(_TM_JSON, _LOLLA)
    assert c["provider"] == "ticketmaster"
    assert c["venue"] == "Grant Park" and c["city"] == "Chicago" and c["state"] == "IL"
    assert c["latitude"] == 41.8765 and c["longitude"] == -87.6213
    # aftershow excluded → edition range is the two main days
    assert c["start_date"] == "2026-07-30" and c["end_date"] == "2026-08-02"
    assert agg.normalize_tm({"_embedded": {"events": []}}, _LOLLA) is None


def test_normalize_seatgeek():
    c = agg.normalize_seatgeek(_SG_JSON, _LOLLA)
    assert c["provider"] == "seatgeek"
    assert c["latitude"] == 41.8765 and c["venue"] == "Grant Park"
    assert c["start_date"] == "2026-07-30" and c["end_date"] == "2026-08-02"
    assert agg.normalize_seatgeek({"events": []}, _LOLLA) is None


def test_edition_range_picks_soonest_year():
    # Two editions present → take the soonest year's min/max only.
    assert agg._edition_range(["2027-04-10", "2026-07-30", "2026-08-02", "2027-04-12"]) \
        == ("2026-07-30", "2026-08-02")


# ── Cross-source merge ─────────────────────────────────────────
def test_merge_agreement():
    fest, stats = agg.merge_candidates(
        [agg.normalize_tm(_TM_JSON, _LOLLA), agg.normalize_seatgeek(_SG_JSON, _LOLLA)], _LOLLA)
    assert fest["start_date"] == "2026-07-30" and fest["latitude"] == 41.8765
    assert stats["agreement"] is True and stats["date_conflicts"] == 0


def test_merge_fills_gap():
    tm_no_coords = {**agg.normalize_tm(_TM_JSON, _LOLLA), "latitude": None, "longitude": None}
    sg = agg.normalize_seatgeek(_SG_JSON, _LOLLA)
    fest, _ = agg.merge_candidates([tm_no_coords, sg], _LOLLA)
    assert fest["latitude"] == 41.8765  # filled from SeatGeek


def test_merge_date_conflict_prefers_tm():
    sg = {**agg.normalize_seatgeek(_SG_JSON, _LOLLA), "start_date": "2026-07-31"}
    fest, stats = agg.merge_candidates([agg.normalize_tm(_TM_JSON, _LOLLA), sg], _LOLLA)
    assert fest["start_date"] == "2026-07-30"  # TM (primary) kept
    assert stats["date_conflicts"] == 1 and stats["agreement"] is False


def test_merge_empty_is_none():
    fest, stats = agg.merge_candidates([], _LOLLA)
    assert fest is None and stats["providers"] == []


# ── Coalesce-forward festival merge (the trust-ordered core) ────
def test_merge_fields_insert():
    op, payload = ingest.merge_festival_fields(
        None, {"slug": "x", "name": "X", "start_date": "2026-07-30", "end_date": "2026-08-02",
               "latitude": 1.0, "longitude": 2.0})
    assert op == "insert" and payload["dates_estimated"] is False and payload["latitude"] == 1.0


def test_merge_fields_replaces_estimated_dates():
    existing = {"start_date": "2026-01-01", "end_date": "2026-01-02", "dates_estimated": True,
                "latitude": 1.0, "longitude": 2.0, "venue": "V", "city": "C"}
    op, payload = ingest.merge_festival_fields(
        existing, {"start_date": "2026-07-30", "end_date": "2026-08-02"})
    assert op == "update"
    assert payload["start_date"] == "2026-07-30" and payload["dates_estimated"] is False


def test_merge_fields_preserves_curated_dates():
    existing = {"start_date": "2026-07-30", "end_date": "2026-08-02", "dates_estimated": False,
                "latitude": 1.0, "longitude": 2.0, "venue": "V", "city": "C"}
    op, payload = ingest.merge_festival_fields(
        existing, {"start_date": "2099-01-01", "end_date": "2099-01-02"})
    assert op == "noop", payload  # curated dates untouched, nothing else to fill


def test_merge_fields_fills_null_only():
    existing = {"start_date": "2026-07-30", "end_date": "2026-08-02", "dates_estimated": False,
                "latitude": None, "longitude": None, "venue": "Real Venue", "city": None}
    op, payload = ingest.merge_festival_fields(
        existing, {"latitude": 5.0, "longitude": 6.0, "venue": "TM Venue", "city": "Chicago"})
    assert op == "update"
    assert payload["latitude"] == 5.0 and payload["city"] == "Chicago"
    assert "venue" not in payload  # existing non-null venue preserved


# ── Staleness rotation ─────────────────────────────────────────
def test_select_stale_targets():
    now = dt.datetime(2026, 6, 25, tzinfo=dt.timezone.utc)
    latest = {"b": "2026-05-01T00:00:00+00:00", "c": "2026-06-20T00:00:00Z"}
    # a, d never ingested → first (CSV order); then oldest-success first (b before c)
    assert agg.select_stale_targets(["a", "b", "c", "d"], latest, now, 3) == ["a", "d", "b"]
    assert agg.select_stale_targets(["a", "b", "c", "d"], latest, now, 99) == ["a", "d", "b", "c"]


def test_shard_targets_partitions_completely():
    slugs = [t.slug for t in agg.load_targets()]
    shards = 4
    parts = [agg.shard_targets(slugs, i, shards) for i in range(shards)]
    flat = [s for p in parts for s in p]
    assert sorted(flat) == sorted(slugs)             # complete
    assert len(flat) == len(set(flat)) == len(slugs)  # disjoint, no dupes
    assert agg.shard_targets(slugs, 0, 1) == slugs    # shards=1 → everything


# ── Flagship lineup normalize ──────────────────────────────────
def test_normalize_tm_lineup():
    attractions = [{"name": n} for n in
                   ["Headliner One", "Headliner Two", "Act 3", "Act 4", "Act 5", "Act 6"]]
    data = {"_embedded": {"events": [
        {"name": "Coachella 2026", "dates": {"start": {"localDate": "2026-04-10"}},
         "_embedded": {"attractions": attractions}},
        {"name": "Coachella Official Aftershow", "dates": {"start": {"localDate": "2026-04-11"}},
         "_embedded": {"attractions": attractions}},  # filtered
    ]}}
    rows = la.normalize_tm_lineup(data, "coachella", "Coachella", 2026, headliners_per_day=2)
    assert len(rows) == 6, rows  # only the main event's 6 acts
    assert rows[0]["is_headliner"] is True and rows[2]["is_headliner"] is False
    assert rows[0]["artist_slug"] == "headliner-one" and rows[0]["festival_slug"] == "coachella"


# ── End-to-end: run() + coalesce merge via a fake store ────────
class _FakeStore:
    def __init__(self, festivals=None):
        self.runs = {}
        self.tables = {"festivals": list(festivals or []), "artists": [], "lineups": []}
        self._n = 0

    def open_run(self, source_id, festival_slug):
        rid = f"run-{len(self.runs)+1}"
        self.runs[rid] = {"status": "running", "festival_slug": festival_slug}
        return rid

    def close_run(self, run_id, status, up, sk, errs, stats):
        self.runs[run_id].update(status=status, rows_upserted=up, stats=stats)

    def upsert(self, table, rows, on_conflict):
        out = []
        for r in rows:
            self._n += 1
            rr = {**r, "id": f"{table}-{self._n}"}
            self.tables[table].append(rr)
            out.append(rr)
        return out

    def resolve_ids(self, table, slugs):
        return {r["slug"]: r["id"] for r in self.tables[table] if r.get("slug") in slugs}

    def merge_festivals(self, rows, trust):
        affected = []
        for r in rows:
            existing = next((f for f in self.tables["festivals"] if f["slug"] == r["slug"]), None)
            op, payload = ingest.merge_festival_fields(existing, r)
            if op == "insert":
                self._n += 1
                row = {**payload, "id": f"festivals-{self._n}"}
                self.tables["festivals"].append(row)
                affected.append(row)
            elif op == "update":
                existing.update(payload)
                affected.append(existing)
        return affected


def test_run_aggregator_merges_not_clobbers():
    """A curated stub (estimated dates, no coords) gets real dates + coords from the
    aggregator, while its hand-tuned accent_color/name survive."""
    stub = {"slug": "lollapalooza", "name": "Lollapalooza", "accent_color": "#FF4500",
            "start_date": "2026-01-01", "end_date": "2026-01-02", "dates_estimated": True,
            "latitude": None, "longitude": None, "venue": None, "city": None, "state": None,
            "timezone": None}
    store = _FakeStore(festivals=[stub])

    class _StubAgg(agg.AggregatorAdapter):
        def fetch(self):
            return {"target": _LOLLA,
                    "candidates": [agg.normalize_tm(_TM_JSON, _LOLLA),
                                   agg.normalize_seatgeek(_SG_JSON, _LOLLA)]}

    res = ingest.run(_StubAgg({"target": _LOLLA}), store,
                     source_id="agg", festival_slug="lollapalooza", trust="aggregator")
    assert res["status"] == "success", res
    f = store.tables["festivals"][0]
    assert f["start_date"] == "2026-07-30" and f["dates_estimated"] is False  # real dates
    assert f["latitude"] == 41.8765 and f["venue"] == "Grant Park"           # gaps filled
    assert f["accent_color"] == "#FF4500" and f["name"] == "Lollapalooza"    # curated preserved
    assert store.runs["run-1"]["stats"]["agreement"] is True                 # stats logged


def run_all():
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("All aggregator self-tests passed.")


if __name__ == "__main__":
    run_all()
