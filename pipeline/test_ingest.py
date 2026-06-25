"""
test_ingest.py — offline self-test for the v3.0 ingestion framework.
No DB, no network. Run: python test_ingest.py   (or: python ingest.py --self-test)
"""

import ingest


class _FakeStore:
    """In-memory stand-in for SupabaseStore (the run() seam)."""

    def __init__(self):
        self.runs: dict[str, dict] = {}
        self.tables: dict[str, list[dict]] = {"festivals": [], "artists": [], "lineups": []}
        self._n = 0

    def open_run(self, source_id, festival_slug):
        rid = f"run-{len(self.runs) + 1}"
        self.runs[rid] = {"status": "running", "source_id": source_id, "festival_slug": festival_slug}
        return rid

    def close_run(self, run_id, status, rows_upserted, rows_skipped, errors, stats):
        self.runs[run_id].update(status=status, rows_upserted=rows_upserted,
                                 rows_skipped=rows_skipped, errors=errors, stats=stats)

    def upsert(self, table, rows, on_conflict):
        # Echo rows back with fake ids (mimics PostgREST return=representation).
        out = []
        for r in rows:
            self._n += 1
            rr = {**r, "id": f"{table}-{self._n}"}
            self.tables[table].append(rr)
            out.append(rr)
        return out

    def resolve_ids(self, table, slugs):
        return {r["slug"]: r["id"] for r in self.tables[table] if r.get("slug") in slugs}


def test_happy_path_and_accounting():
    """One festival, one valid artist, one resolvable lineup → all upserted."""
    config = {
        "festival": {"slug": "pilotfest", "name": "Pilot Fest"},
        "lineups": [
            {"festival_slug": "pilotfest", "artist_slug": "real-band",
             "artist_name": "Real Band", "year": 2026, "is_headliner": True},
        ],
    }
    store = _FakeStore()
    adapter = ingest.ConfigManualAdapter(config)
    res = ingest.run(adapter, store, source_id="src-1", festival_slug="pilotfest", trust="official")

    assert res["status"] == "success", res
    assert res["rows_skipped"] == 0, res
    # 1 festival + 1 derived artist + 1 lineup
    assert res["rows_upserted"] == 3, res
    assert store.runs["run-1"]["status"] == "success"
    assert store.runs["run-1"]["festival_slug"] == "pilotfest"
    # lineup got FK ids + provenance from the source
    lineup = store.tables["lineups"][0]
    assert lineup["source"] == "official" and lineup["source_id"] == "src-1"
    assert lineup["festival_id"] and lineup["artist_id"]


def test_validation_and_unresolved_are_skipped():
    """Invalid artist dropped pre-upsert; its lineup then can't resolve → both skipped."""
    config = {
        "festival": {"slug": "pilotfest", "name": "Pilot Fest"},
        "artists": [{"slug": "no-name"}],  # missing name → invalid
        "lineups": [
            {"festival_slug": "pilotfest", "artist_slug": "good", "artist_name": "Good", "year": 2026},
            {"festival_slug": "pilotfest", "artist_slug": "no-name", "year": 2026},  # unresolved
            {"festival_slug": "pilotfest", "artist_slug": "x"},                       # missing year → invalid
        ],
    }
    store = _FakeStore()
    res = ingest.run(ingest.ConfigManualAdapter(config), store, source_id="s", trust="official")

    assert res["status"] == "partial", res
    # skipped: 1 invalid artist + 1 invalid lineup (no year) + 1 unresolved lineup
    assert res["rows_skipped"] == 3, res
    # upserted: 1 festival + 1 valid derived artist ("good") + 1 resolvable lineup
    assert res["rows_upserted"] == 3, res
    assert len(store.tables["lineups"]) == 1


def test_adapter_error_records_error_run():
    class _Boom(ingest.SourceAdapter):
        key = "_boom"
        trust = "official"

        def fetch(self):
            raise RuntimeError("source down")

        def normalize(self, raw):
            return ingest.Normalized()

    store = _FakeStore()
    res = ingest.run(_Boom(), store, source_id="s")
    assert res["status"] == "error", res
    assert res["errors"] and res["errors"][0]["stage"] == "run"
    assert store.runs["run-1"]["status"] == "error"


def test_registry():
    assert ingest.get_adapter("manual_config").key == "manual_config"
    try:
        ingest.get_adapter("nope")
    except KeyError:
        pass
    else:
        raise AssertionError("expected KeyError for unknown adapter key")


def run_all():
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("All ingest self-tests passed.")


if __name__ == "__main__":
    run_all()
