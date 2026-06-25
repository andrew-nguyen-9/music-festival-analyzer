"""
names.py
--------
One canonical way to derive an artist's display name and URL slug, shared by
every pipeline writer.

Before v2.3 each script slugified differently: the schedule seeder stripped
accents straight to hyphens ("Röz" -> "r-z") while the scrapers used
python-slugify ("Röz" -> "roz"). The same act could therefore land as two
`artists` rows with two slugs and a split Spotify-cache join. Route all writers
through here so a name maps to exactly one slug everywhere.

The Spotify cache keys on `artists.id` (a UUID FK), not the slug — so
normalizing the *display name* is safe. The *slug* is identity for /artist/[slug]
URLs and for artist-row dedup, so `canonical_slug` is the value that must never
drift between scripts.
"""

from slugify import slugify

# Known display-name aliases: map a raw scraped/seeded variant (lowercased,
# whitespace-normalized) to the one canonical display name. Keep this small and
# obvious — it is a tuning knob, not a place for guesses. Add an entry only when
# the audit confirms two strings are the same act.
NAME_ALIASES: dict[str, str] = {
    # "raw variant": "Canonical Name",
}


def canonical_name(raw: str) -> str:
    """Trim, collapse internal whitespace, and apply the known-alias map."""
    name = " ".join((raw or "").split())
    return NAME_ALIASES.get(name.lower(), name)


def canonical_slug(raw: str) -> str:
    """ASCII URL slug for an artist. Transliterates accents (python-slugify) so
    the slug is identical across every writer, and is derived from the canonical
    name so aliases collapse to a single slug."""
    return slugify(canonical_name(raw))


def _demo() -> None:
    # Accents transliterate, they do not hyphenate (the v2.3.1 slug-drift bug).
    assert canonical_slug("Röz") == "roz", canonical_slug("Röz")
    assert canonical_slug("Adéla") == "adela", canonical_slug("Adéla")
    # Whitespace + case collapse to one slug / one name.
    assert canonical_slug("  Wet   Leg ") == "wet-leg"
    assert canonical_name("  Wet   Leg ") == "Wet Leg"
    # Symbols are handled deterministically and case-insensitively.
    assert canonical_slug("BBNO$") == canonical_slug("bbno$")
    print("names: all checks passed")


if __name__ == "__main__":
    _demo()
