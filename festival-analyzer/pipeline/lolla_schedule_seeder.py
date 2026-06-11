"""
lolla_schedule_seeder.py
------------------------
Seeds the complete Lollapalooza 2026 schedule into the Supabase `lineups` table.

For each artist, the script will:
  1. Look up or create the artist record (upsert on slug)
  2. Upsert the lineup entry (on_conflict: festival_id, artist_id, year)

Run:
    python lolla_schedule_seeder.py               # seed all entries
    python lolla_schedule_seeder.py --dry-run     # preview without writing
    python lolla_schedule_seeder.py --force       # re-seed even if entries exist

Schedule: one-off / manual; re-run is safe (idempotent)
"""

import os
import re
import argparse
import logging

from dotenv import load_dotenv
from supabase import create_client, Client
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich import print as rprint

load_dotenv()
console = Console()
log = logging.getLogger(__name__)

FESTIVAL_SLUG = "lollapalooza"
YEAR = 2026

# ---------------------------------------------------------------------------
# Schedule data
# ---------------------------------------------------------------------------

SCHEDULE = [
    # ── Thursday July 30, 2026 ──────────────────────────────────────────────
    # T-Mobile Stage
    {"name": "Asha Banks",            "stage": "T-Mobile Stage",      "day": "2026-07-30", "start": "12:45", "end": "13:30", "headliner": False},
    {"name": "Haute & Freddy",         "stage": "T-Mobile Stage",      "day": "2026-07-30", "start": "14:30", "end": "15:30", "headliner": False},
    {"name": "5 Seconds of Summer",    "stage": "T-Mobile Stage",      "day": "2026-07-30", "start": "16:30", "end": "17:30", "headliner": False},
    {"name": "Sombr",                  "stage": "T-Mobile Stage",      "day": "2026-07-30", "start": "18:30", "end": "19:30", "headliner": False},
    {"name": "Lorde",                  "stage": "T-Mobile Stage",      "day": "2026-07-30", "start": "20:30", "end": "23:00", "headliner": True},
    # Perry's Stage
    {"name": "Klo",                    "stage": "Perry's Stage",        "day": "2026-07-30", "start": "12:00", "end": "12:30", "headliner": False},
    {"name": "Know Good",              "stage": "Perry's Stage",        "day": "2026-07-30", "start": "12:45", "end": "13:30", "headliner": False},
    {"name": "Devault",                "stage": "Perry's Stage",        "day": "2026-07-30", "start": "13:45", "end": "14:45", "headliner": False},
    {"name": "MPH",                    "stage": "Perry's Stage",        "day": "2026-07-30", "start": "15:00", "end": "16:00", "headliner": False},
    {"name": "Boys Noize",             "stage": "Perry's Stage",        "day": "2026-07-30", "start": "16:15", "end": "17:15", "headliner": False},
    {"name": "Boris Brejcha",          "stage": "Perry's Stage",        "day": "2026-07-30", "start": "17:45", "end": "18:45", "headliner": False},
    {"name": "Kettama",                "stage": "Perry's Stage",        "day": "2026-07-30", "start": "19:00", "end": "20:00", "headliner": False},
    {"name": "Worship",                "stage": "Perry's Stage",        "day": "2026-07-30", "start": "20:30", "end": "21:45", "headliner": False},
    # Allianz Stage
    {"name": "Pearly Drops",           "stage": "Allianz Stage",        "day": "2026-07-30", "start": "12:00", "end": "12:45", "headliner": False},
    {"name": "Bad Nerves",             "stage": "Allianz Stage",        "day": "2026-07-30", "start": "13:30", "end": "14:30", "headliner": False},
    {"name": "SB19",                   "stage": "Allianz Stage",        "day": "2026-07-30", "start": "15:30", "end": "16:30", "headliner": False},
    {"name": "Audrey Hobert",          "stage": "Allianz Stage",        "day": "2026-07-30", "start": "17:30", "end": "18:30", "headliner": False},
    {"name": "Wet Leg",                "stage": "Allianz Stage",        "day": "2026-07-30", "start": "19:30", "end": "20:30", "headliner": False},
    # Kidzapalooza Stage
    {"name": "Mister G",               "stage": "Kidzapalooza Stage",   "day": "2026-07-30", "start": "12:00", "end": "12:30", "headliner": False},
    {"name": "School of Rock",         "stage": "Kidzapalooza Stage",   "day": "2026-07-30", "start": "13:30", "end": "14:00", "headliner": False},
    {"name": "Miss Tutti & The Fruity Band", "stage": "Kidzapalooza Stage", "day": "2026-07-30", "start": "15:00", "end": "15:30", "headliner": False},
    {"name": "Jazzy Ash",              "stage": "Kidzapalooza Stage",   "day": "2026-07-30", "start": "17:15", "end": "17:45", "headliner": False},
    # BMI Stage
    {"name": "The Braymores",          "stage": "BMI Stage",            "day": "2026-07-30", "start": "13:00", "end": "13:40", "headliner": False},
    {"name": "Simon Grossmann",        "stage": "BMI Stage",            "day": "2026-07-30", "start": "14:10", "end": "14:50", "headliner": False},
    {"name": "Elizabeth Nichols",      "stage": "BMI Stage",            "day": "2026-07-30", "start": "15:20", "end": "16:00", "headliner": False},
    {"name": "Bella Kay",              "stage": "BMI Stage",            "day": "2026-07-30", "start": "16:30", "end": "17:10", "headliner": False},
    {"name": "Chalk",                  "stage": "BMI Stage",            "day": "2026-07-30", "start": "17:40", "end": "18:20", "headliner": False},
    {"name": "Evening Elephants",      "stage": "BMI Stage",            "day": "2026-07-30", "start": "18:50", "end": "19:30", "headliner": False},
    # Airbnb Stage
    {"name": "Kim Theory",             "stage": "Airbnb Stage",         "day": "2026-07-30", "start": "12:00", "end": "12:30", "headliner": False},
    {"name": "Penelope Road",          "stage": "Airbnb Stage",         "day": "2026-07-30", "start": "12:50", "end": "13:30", "headliner": False},
    {"name": "Marlon Funaki",          "stage": "Airbnb Stage",         "day": "2026-07-30", "start": "13:50", "end": "14:30", "headliner": False},
    {"name": "Ecca Vandal",            "stage": "Airbnb Stage",         "day": "2026-07-30", "start": "14:50", "end": "15:30", "headliner": False},
    {"name": "Ninajirachi",            "stage": "Airbnb Stage",         "day": "2026-07-30", "start": "16:00", "end": "16:45", "headliner": False},
    {"name": "Amble",                  "stage": "Airbnb Stage",         "day": "2026-07-30", "start": "17:15", "end": "18:00", "headliner": False},
    {"name": "CMAT",                   "stage": "Airbnb Stage",         "day": "2026-07-30", "start": "18:30", "end": "19:15", "headliner": False},
    {"name": "Snow Strippers",         "stage": "Airbnb Stage",         "day": "2026-07-30", "start": "19:45", "end": "20:30", "headliner": False},
    {"name": "Viagra Boys",            "stage": "Airbnb Stage",         "day": "2026-07-30", "start": "21:00", "end": "22:00", "headliner": False},
    # Tito's Stage
    {"name": "Faouzia",                "stage": "Tito's Stage",         "day": "2026-07-30", "start": "12:15", "end": "13:00", "headliner": False},
    {"name": "Kingfishr",              "stage": "Tito's Stage",         "day": "2026-07-30", "start": "13:45", "end": "14:45", "headliner": False},
    {"name": "Paris Paloma",           "stage": "Tito's Stage",         "day": "2026-07-30", "start": "15:45", "end": "16:45", "headliner": False},
    {"name": "Little Simz",            "stage": "Tito's Stage",         "day": "2026-07-30", "start": "17:45", "end": "18:45", "headliner": False},
    {"name": "Devault",                "stage": "Tito's Stage",         "day": "2026-07-30", "start": "19:45", "end": "20:30", "headliner": False},
    # Bud Light Stage
    {"name": "Bixby",                  "stage": "Bud Light Stage",      "day": "2026-07-30", "start": "13:00", "end": "13:45", "headliner": False},
    {"name": "Between Friends",        "stage": "Bud Light Stage",      "day": "2026-07-30", "start": "14:45", "end": "15:45", "headliner": False},
    {"name": "Blood Orange",           "stage": "Bud Light Stage",      "day": "2026-07-30", "start": "16:45", "end": "17:45", "headliner": False},
    {"name": "Empire of the Sun",      "stage": "Bud Light Stage",      "day": "2026-07-30", "start": "18:45", "end": "19:45", "headliner": False},
    {"name": "John Summit",            "stage": "Bud Light Stage",      "day": "2026-07-30", "start": "20:30", "end": "22:00", "headliner": False},

    # ── Friday July 31, 2026 ────────────────────────────────────────────────
    # T-Mobile Stage
    {"name": "PartyOf2",               "stage": "T-Mobile Stage",      "day": "2026-07-31", "start": "12:55", "end": "13:40", "headliner": False},
    {"name": "I-DLE",                  "stage": "T-Mobile Stage",      "day": "2026-07-31", "start": "14:40", "end": "15:40", "headliner": False},
    {"name": "Zara Larsson",           "stage": "T-Mobile Stage",      "day": "2026-07-31", "start": "16:40", "end": "17:40", "headliner": False},
    {"name": "Lil Uzi Vert",           "stage": "T-Mobile Stage",      "day": "2026-07-31", "start": "18:40", "end": "19:40", "headliner": False},
    {"name": "Charli XCX",             "stage": "T-Mobile Stage",      "day": "2026-07-31", "start": "20:40", "end": "23:00", "headliner": True},
    # Perry's Stage
    {"name": "Bradeazy",               "stage": "Perry's Stage",        "day": "2026-07-31", "start": "12:00", "end": "12:30", "headliner": False},
    {"name": "Avello",                 "stage": "Perry's Stage",        "day": "2026-07-31", "start": "12:45", "end": "13:30", "headliner": False},
    {"name": "Lyny",                   "stage": "Perry's Stage",        "day": "2026-07-31", "start": "13:45", "end": "14:45", "headliner": False},
    {"name": "Röz",                    "stage": "Perry's Stage",        "day": "2026-07-31", "start": "15:00", "end": "16:00", "headliner": False},
    {"name": "Notion",                 "stage": "Perry's Stage",        "day": "2026-07-31", "start": "16:15", "end": "17:15", "headliner": False},
    {"name": "Sidepiece",              "stage": "Perry's Stage",        "day": "2026-07-31", "start": "17:45", "end": "18:45", "headliner": False},
    {"name": "Mustard",                "stage": "Perry's Stage",        "day": "2026-07-31", "start": "19:00", "end": "20:00", "headliner": False},
    {"name": "Major Lazer",            "stage": "Perry's Stage",        "day": "2026-07-31", "start": "20:30", "end": "21:45", "headliner": False},
    # Allianz Stage
    {"name": "The Army, The Navy",     "stage": "Allianz Stage",        "day": "2026-07-31", "start": "12:10", "end": "12:55", "headliner": False},
    {"name": "Claire Rosinkranz",      "stage": "Allianz Stage",        "day": "2026-07-31", "start": "13:40", "end": "14:40", "headliner": False},
    {"name": "Skye Newman",            "stage": "Allianz Stage",        "day": "2026-07-31", "start": "15:40", "end": "16:40", "headliner": False},
    {"name": "Suki Waterhouse",        "stage": "Allianz Stage",        "day": "2026-07-31", "start": "17:40", "end": "18:40", "headliner": False},
    {"name": "Not For Radio",          "stage": "Allianz Stage",        "day": "2026-07-31", "start": "19:40", "end": "20:40", "headliner": False},
    # Kidzapalooza Stage
    {"name": "Miss Tutti & The Fruity Band", "stage": "Kidzapalooza Stage", "day": "2026-07-31", "start": "12:00", "end": "12:30", "headliner": False},
    {"name": "Mister G",               "stage": "Kidzapalooza Stage",   "day": "2026-07-31", "start": "13:30", "end": "14:00", "headliner": False},
    {"name": "Jazzy Ash",              "stage": "Kidzapalooza Stage",   "day": "2026-07-31", "start": "15:00", "end": "15:30", "headliner": False},
    {"name": "School of Rock",         "stage": "Kidzapalooza Stage",   "day": "2026-07-31", "start": "17:15", "end": "17:45", "headliner": False},
    # BMI Stage
    {"name": "Whitney Whitney",        "stage": "BMI Stage",            "day": "2026-07-31", "start": "12:00", "end": "12:30", "headliner": False},
    {"name": "Valencia Grace",         "stage": "BMI Stage",            "day": "2026-07-31", "start": "13:00", "end": "13:40", "headliner": False},
    {"name": "Ella Boh",               "stage": "BMI Stage",            "day": "2026-07-31", "start": "14:10", "end": "14:50", "headliner": False},
    {"name": "Emi Grace",              "stage": "BMI Stage",            "day": "2026-07-31", "start": "15:20", "end": "16:00", "headliner": False},
    {"name": "IVRI",                   "stage": "BMI Stage",            "day": "2026-07-31", "start": "16:30", "end": "17:10", "headliner": False},
    {"name": "Ella Red",               "stage": "BMI Stage",            "day": "2026-07-31", "start": "17:40", "end": "18:20", "headliner": False},
    {"name": "Paloma Morphy",          "stage": "BMI Stage",            "day": "2026-07-31", "start": "18:50", "end": "19:30", "headliner": False},
    {"name": "Freddie Gibbs",          "stage": "BMI Stage",            "day": "2026-07-31", "start": "21:15", "end": "22:00", "headliner": False},
    # Airbnb Stage
    {"name": "Beno",                   "stage": "Airbnb Stage",         "day": "2026-07-31", "start": "12:00", "end": "12:30", "headliner": False},
    {"name": "Day We Ran",             "stage": "Airbnb Stage",         "day": "2026-07-31", "start": "12:50", "end": "13:30", "headliner": False},
    {"name": "Love Spells",            "stage": "Airbnb Stage",         "day": "2026-07-31", "start": "13:50", "end": "14:30", "headliner": False},
    {"name": "54 Ultra",               "stage": "Airbnb Stage",         "day": "2026-07-31", "start": "14:50", "end": "15:30", "headliner": False},
    {"name": "Finn Wolfhard",          "stage": "Airbnb Stage",         "day": "2026-07-31", "start": "16:00", "end": "16:45", "headliner": False},
    {"name": "Oklou",                  "stage": "Airbnb Stage",         "day": "2026-07-31", "start": "17:30", "end": "18:15", "headliner": False},
    {"name": "Slayyyter",              "stage": "Airbnb Stage",         "day": "2026-07-31", "start": "18:45", "end": "19:30", "headliner": False},
    {"name": "Horsegiirl",             "stage": "Airbnb Stage",         "day": "2026-07-31", "start": "20:00", "end": "20:45", "headliner": False},
    # Tito's Stage
    {"name": "Chicago Made",           "stage": "Tito's Stage",         "day": "2026-07-31", "start": "12:15", "end": "13:00", "headliner": False},
    {"name": "Julia Wolf",             "stage": "Tito's Stage",         "day": "2026-07-31", "start": "13:45", "end": "14:30", "headliner": False},
    {"name": "Mother Mother",          "stage": "Tito's Stage",         "day": "2026-07-31", "start": "15:30", "end": "16:30", "headliner": False},
    {"name": "Loathe",                 "stage": "Tito's Stage",         "day": "2026-07-31", "start": "17:30", "end": "18:30", "headliner": False},
    {"name": "Nettspend",              "stage": "Tito's Stage",         "day": "2026-07-31", "start": "19:30", "end": "20:30", "headliner": False},
    # Bud Light Stage
    {"name": "High Vis",               "stage": "Bud Light Stage",      "day": "2026-07-31", "start": "13:00", "end": "13:45", "headliner": False},
    {"name": "Balu Brigada",           "stage": "Bud Light Stage",      "day": "2026-07-31", "start": "14:30", "end": "15:30", "headliner": False},
    {"name": "The Story So Far",       "stage": "Bud Light Stage",      "day": "2026-07-31", "start": "16:30", "end": "17:30", "headliner": False},
    {"name": "Yungblud",               "stage": "Bud Light Stage",      "day": "2026-07-31", "start": "18:30", "end": "19:30", "headliner": False},
    {"name": "The Smashing Pumpkins",  "stage": "Bud Light Stage",      "day": "2026-07-31", "start": "20:30", "end": "22:00", "headliner": False},

    # ── Saturday August 1, 2026 ─────────────────────────────────────────────
    # T-Mobile Stage
    {"name": "Lucy Bedroque",          "stage": "T-Mobile Stage",      "day": "2026-08-01", "start": "13:10", "end": "13:55", "headliner": False},
    {"name": "Cortis",                 "stage": "T-Mobile Stage",      "day": "2026-08-01", "start": "14:55", "end": "15:45", "headliner": False},
    {"name": "Leon Thomas",            "stage": "T-Mobile Stage",      "day": "2026-08-01", "start": "16:30", "end": "17:30", "headliner": False},
    {"name": "The Neighbourhood",      "stage": "T-Mobile Stage",      "day": "2026-08-01", "start": "18:30", "end": "19:30", "headliner": False},
    {"name": "Olivia Dean",            "stage": "T-Mobile Stage",      "day": "2026-08-01", "start": "20:30", "end": "23:00", "headliner": True},
    # Perry's Stage
    {"name": "Peace Control",          "stage": "Perry's Stage",        "day": "2026-08-01", "start": "12:00", "end": "12:30", "headliner": False},
    {"name": "MC4D",                   "stage": "Perry's Stage",        "day": "2026-08-01", "start": "12:45", "end": "13:30", "headliner": False},
    {"name": "Omnom",                  "stage": "Perry's Stage",        "day": "2026-08-01", "start": "13:45", "end": "14:45", "headliner": False},
    {"name": "AYYBO",                  "stage": "Perry's Stage",        "day": "2026-08-01", "start": "15:00", "end": "16:00", "headliner": False},
    {"name": "Whethan",                "stage": "Perry's Stage",        "day": "2026-08-01", "start": "16:15", "end": "17:15", "headliner": False},
    {"name": "Max Styler",             "stage": "Perry's Stage",        "day": "2026-08-01", "start": "17:45", "end": "18:45", "headliner": False},
    {"name": "Alison Wonderland",      "stage": "Perry's Stage",        "day": "2026-08-01", "start": "19:00", "end": "20:00", "headliner": False},
    {"name": "Disco Lines",            "stage": "Perry's Stage",        "day": "2026-08-01", "start": "20:30", "end": "21:45", "headliner": False},
    # Allianz Stage
    {"name": "Sunday (1994)",          "stage": "Allianz Stage",        "day": "2026-08-01", "start": "12:25", "end": "13:10", "headliner": False},
    {"name": "Jim Legxacy",            "stage": "Allianz Stage",        "day": "2026-08-01", "start": "13:55", "end": "14:55", "headliner": False},
    {"name": "Khamari",                "stage": "Allianz Stage",        "day": "2026-08-01", "start": "15:45", "end": "16:30", "headliner": False},
    {"name": "Spacey Jane",            "stage": "Allianz Stage",        "day": "2026-08-01", "start": "17:30", "end": "18:30", "headliner": False},
    {"name": "Geese",                  "stage": "Allianz Stage",        "day": "2026-08-01", "start": "19:30", "end": "20:30", "headliner": False},
    # Kidzapalooza Stage
    {"name": "Flor Bromley",           "stage": "Kidzapalooza Stage",   "day": "2026-08-01", "start": "12:00", "end": "12:30", "headliner": False},
    {"name": "Mega Ran",               "stage": "Kidzapalooza Stage",   "day": "2026-08-01", "start": "13:30", "end": "14:00", "headliner": False},
    {"name": "Lucky Diaz",             "stage": "Kidzapalooza Stage",   "day": "2026-08-01", "start": "15:00", "end": "15:30", "headliner": False},
    {"name": "The Happiness Club",     "stage": "Kidzapalooza Stage",   "day": "2026-08-01", "start": "16:00", "end": "16:30", "headliner": False},
    {"name": "Q Brothers",             "stage": "Kidzapalooza Stage",   "day": "2026-08-01", "start": "17:15", "end": "17:45", "headliner": False},
    # BMI Stage
    {"name": "The Creekers",           "stage": "BMI Stage",            "day": "2026-08-01", "start": "13:00", "end": "13:40", "headliner": False},
    {"name": "Next of Kin",            "stage": "BMI Stage",            "day": "2026-08-01", "start": "14:10", "end": "14:50", "headliner": False},
    {"name": "Ink",                    "stage": "BMI Stage",            "day": "2026-08-01", "start": "15:20", "end": "16:00", "headliner": False},
    {"name": "Calder Allen",           "stage": "BMI Stage",            "day": "2026-08-01", "start": "16:30", "end": "17:10", "headliner": False},
    {"name": "Jae Stephens",           "stage": "BMI Stage",            "day": "2026-08-01", "start": "17:40", "end": "18:20", "headliner": False},
    {"name": "Ryman",                  "stage": "BMI Stage",            "day": "2026-08-01", "start": "18:50", "end": "19:30", "headliner": False},
    # Airbnb Stage
    {"name": "Nat Myers",              "stage": "Airbnb Stage",         "day": "2026-08-01", "start": "12:00", "end": "12:30", "headliner": False},
    {"name": "Villanelle",             "stage": "Airbnb Stage",         "day": "2026-08-01", "start": "12:50", "end": "13:30", "headliner": False},
    {"name": "Die Spitz",              "stage": "Airbnb Stage",         "day": "2026-08-01", "start": "13:50", "end": "14:30", "headliner": False},
    {"name": "Frost Children",         "stage": "Airbnb Stage",         "day": "2026-08-01", "start": "14:50", "end": "15:30", "headliner": False},
    {"name": "Quadeca",                "stage": "Airbnb Stage",         "day": "2026-08-01", "start": "16:00", "end": "16:45", "headliner": False},
    {"name": "Sienna Spiro",           "stage": "Airbnb Stage",         "day": "2026-08-01", "start": "17:15", "end": "18:00", "headliner": False},
    {"name": "KWN",                    "stage": "Airbnb Stage",         "day": "2026-08-01", "start": "18:30", "end": "19:15", "headliner": False},
    {"name": "Cameron Whitcomb",       "stage": "Airbnb Stage",         "day": "2026-08-01", "start": "19:45", "end": "20:30", "headliner": False},
    {"name": "DJ Trixie Mattel",       "stage": "Airbnb Stage",         "day": "2026-08-01", "start": "21:00", "end": "22:00", "headliner": False},
    # Tito's Stage
    {"name": "Chezile",                "stage": "Tito's Stage",         "day": "2026-08-01", "start": "12:45", "end": "13:30", "headliner": False},
    {"name": "Chace",                  "stage": "Tito's Stage",         "day": "2026-08-01", "start": "13:30", "end": "14:15", "headliner": False},
    {"name": "Goldie Boutilier",       "stage": "Tito's Stage",         "day": "2026-08-01", "start": "14:15", "end": "15:15", "headliner": False},
    {"name": "Momma",                  "stage": "Tito's Stage",         "day": "2026-08-01", "start": "16:15", "end": "17:15", "headliner": False},
    {"name": "BBNO$",                  "stage": "Tito's Stage",         "day": "2026-08-01", "start": "18:15", "end": "19:15", "headliner": False},
    {"name": "Chicago Youth Symphony Orchestra", "stage": "Tito's Stage", "day": "2026-08-01", "start": "20:15", "end": "21:00", "headliner": False},
    # Bud Light Stage
    {"name": "Wolf Alice",             "stage": "Bud Light Stage",      "day": "2026-08-01", "start": "15:15", "end": "16:15", "headliner": False},
    {"name": "Clipse",                 "stage": "Bud Light Stage",      "day": "2026-08-01", "start": "17:15", "end": "18:15", "headliner": False},
    {"name": "Ethel Cain",             "stage": "Bud Light Stage",      "day": "2026-08-01", "start": "19:15", "end": "20:15", "headliner": False},
    {"name": "Jennie",                 "stage": "Bud Light Stage",      "day": "2026-08-01", "start": "21:00", "end": "22:00", "headliner": False},

    # ── Sunday August 2, 2026 ───────────────────────────────────────────────
    # T-Mobile Stage
    {"name": "New Constellations",     "stage": "T-Mobile Stage",      "day": "2026-08-02", "start": "13:15", "end": "14:00", "headliner": False},
    {"name": "Adéla",                  "stage": "T-Mobile Stage",      "day": "2026-08-02", "start": "15:00", "end": "15:45", "headliner": False},
    {"name": "Muna",                   "stage": "T-Mobile Stage",      "day": "2026-08-02", "start": "16:45", "end": "17:45", "headliner": False},
    {"name": "Beabadoobee",            "stage": "T-Mobile Stage",      "day": "2026-08-02", "start": "18:45", "end": "19:45", "headliner": False},
    {"name": "Tate McRae",             "stage": "T-Mobile Stage",      "day": "2026-08-02", "start": "20:45", "end": "23:00", "headliner": True},
    # Perry's Stage
    {"name": "Zack Martino",           "stage": "Perry's Stage",        "day": "2026-08-02", "start": "12:00", "end": "12:30", "headliner": False},
    {"name": "Jackie Hollander",       "stage": "Perry's Stage",        "day": "2026-08-02", "start": "12:45", "end": "13:30", "headliner": False},
    {"name": "Westend",                "stage": "Perry's Stage",        "day": "2026-08-02", "start": "13:45", "end": "14:45", "headliner": False},
    {"name": "Riordan",                "stage": "Perry's Stage",        "day": "2026-08-02", "start": "15:00", "end": "16:00", "headliner": False},
    {"name": "Dombresky",              "stage": "Perry's Stage",        "day": "2026-08-02", "start": "16:15", "end": "17:15", "headliner": False},
    {"name": "Duke Dumont",            "stage": "Perry's Stage",        "day": "2026-08-02", "start": "17:45", "end": "18:45", "headliner": False},
    {"name": "Eli Brown",              "stage": "Perry's Stage",        "day": "2026-08-02", "start": "19:00", "end": "20:00", "headliner": False},
    {"name": "The Chainsmokers",       "stage": "Perry's Stage",        "day": "2026-08-02", "start": "20:30", "end": "21:45", "headliner": False},
    # Allianz Stage
    {"name": "Stella Lefty",           "stage": "Allianz Stage",        "day": "2026-08-02", "start": "12:30", "end": "13:15", "headliner": False},
    {"name": "Destin Conrad",          "stage": "Allianz Stage",        "day": "2026-08-02", "start": "14:00", "end": "15:00", "headliner": False},
    {"name": "Amber Mark",             "stage": "Allianz Stage",        "day": "2026-08-02", "start": "15:45", "end": "16:45", "headliner": False},
    {"name": "Jade",                   "stage": "Allianz Stage",        "day": "2026-08-02", "start": "17:45", "end": "18:45", "headliner": False},
    {"name": "Aespa",                  "stage": "Allianz Stage",        "day": "2026-08-02", "start": "19:45", "end": "20:45", "headliner": False},
    # Kidzapalooza Stage
    {"name": "Flor Bromley",           "stage": "Kidzapalooza Stage",   "day": "2026-08-02", "start": "12:00", "end": "12:30", "headliner": False},
    {"name": "Lucky Diaz",             "stage": "Kidzapalooza Stage",   "day": "2026-08-02", "start": "13:30", "end": "14:00", "headliner": False},
    {"name": "Q Brothers",             "stage": "Kidzapalooza Stage",   "day": "2026-08-02", "start": "15:00", "end": "15:30", "headliner": False},
    {"name": "The Happiness Club",     "stage": "Kidzapalooza Stage",   "day": "2026-08-02", "start": "16:00", "end": "16:30", "headliner": False},
    {"name": "Mega Ran",               "stage": "Kidzapalooza Stage",   "day": "2026-08-02", "start": "17:15", "end": "17:45", "headliner": False},
    # BMI Stage
    {"name": "Snacktime",              "stage": "BMI Stage",            "day": "2026-08-02", "start": "13:00", "end": "13:40", "headliner": False},
    {"name": "Surfing for Daisy",      "stage": "BMI Stage",            "day": "2026-08-02", "start": "14:10", "end": "14:50", "headliner": False},
    {"name": "Case Oats",              "stage": "BMI Stage",            "day": "2026-08-02", "start": "15:20", "end": "16:00", "headliner": False},
    {"name": "Justine Skye",           "stage": "BMI Stage",            "day": "2026-08-02", "start": "16:30", "end": "17:10", "headliner": False},
    {"name": "Porch Light",            "stage": "BMI Stage",            "day": "2026-08-02", "start": "17:40", "end": "18:20", "headliner": False},
    {"name": "Will Swinton",           "stage": "BMI Stage",            "day": "2026-08-02", "start": "18:50", "end": "19:30", "headliner": False},
    # Airbnb Stage
    {"name": "Sunshine",               "stage": "Airbnb Stage",         "day": "2026-08-02", "start": "12:00", "end": "12:30", "headliner": False},
    {"name": "The Bends",              "stage": "Airbnb Stage",         "day": "2026-08-02", "start": "12:50", "end": "13:30", "headliner": False},
    {"name": "After",                  "stage": "Airbnb Stage",         "day": "2026-08-02", "start": "13:50", "end": "14:30", "headliner": False},
    {"name": "Water From Your Eyes",   "stage": "Airbnb Stage",         "day": "2026-08-02", "start": "14:50", "end": "15:30", "headliner": False},
    {"name": "Inji",                   "stage": "Airbnb Stage",         "day": "2026-08-02", "start": "16:00", "end": "16:45", "headliner": False},
    {"name": "Los Retros",             "stage": "Airbnb Stage",         "day": "2026-08-02", "start": "17:15", "end": "18:00", "headliner": False},
    {"name": "Monaleo",                "stage": "Airbnb Stage",         "day": "2026-08-02", "start": "18:30", "end": "19:15", "headliner": False},
    {"name": "Fakemink",               "stage": "Airbnb Stage",         "day": "2026-08-02", "start": "19:45", "end": "20:30", "headliner": False},
    {"name": "ADO",                    "stage": "Airbnb Stage",         "day": "2026-08-02", "start": "21:15", "end": "22:00", "headliner": False},
    # Tito's Stage
    {"name": "Easy Honey",             "stage": "Tito's Stage",         "day": "2026-08-02", "start": "12:45", "end": "13:30", "headliner": False},
    {"name": "Whatmore",               "stage": "Tito's Stage",         "day": "2026-08-02", "start": "13:30", "end": "14:15", "headliner": False},
    {"name": "Cruz Beckham and The Breakers", "stage": "Tito's Stage",  "day": "2026-08-02", "start": "14:15", "end": "15:00", "headliner": False},
    {"name": "Wunderhorse",            "stage": "Tito's Stage",         "day": "2026-08-02", "start": "16:00", "end": "17:00", "headliner": False},
    {"name": "Hot Mulligan",           "stage": "Tito's Stage",         "day": "2026-08-02", "start": "18:00", "end": "19:00", "headliner": False},
    {"name": "Vandelux",               "stage": "Tito's Stage",         "day": "2026-08-02", "start": "20:00", "end": "20:45", "headliner": False},
    # Bud Light Stage
    {"name": "Waylon Wyatt",           "stage": "Bud Light Stage",      "day": "2026-08-02", "start": "15:00", "end": "16:00", "headliner": False},
    {"name": "Yoasobi",                "stage": "Bud Light Stage",      "day": "2026-08-02", "start": "17:00", "end": "18:00", "headliner": False},
    {"name": "Turnstile",              "stage": "Bud Light Stage",      "day": "2026-08-02", "start": "19:00", "end": "20:00", "headliner": False},
    {"name": "The XX",                 "stage": "Bud Light Stage",      "day": "2026-08-02", "start": "20:45", "end": "22:00", "headliner": False},
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    """Convert an artist name to a URL-safe slug."""
    text = text.lower().strip()
    # Replace common punctuation / special chars
    text = re.sub(r"[&,']", "", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text


def get_supabase() -> Client:
    return create_client(
        os.environ["NEXT_PUBLIC_SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )


def get_festival_id(supabase: Client) -> str:
    """Return the UUID for the lollapalooza festival row."""
    resp = (
        supabase.table("festivals")
        .select("id")
        .eq("slug", FESTIVAL_SLUG)
        .single()
        .execute()
    )
    if not resp.data:
        raise RuntimeError(
            f"Festival '{FESTIVAL_SLUG}' not found in the festivals table. "
            "Run festival_scraper.py first."
        )
    return resp.data["id"]


def upsert_artist(supabase: Client, name: str, dry_run: bool) -> str | None:
    """
    Upsert an artist record and return its UUID.
    On dry-run, returns None (no DB write).
    """
    slug = slugify(name)
    if dry_run:
        return None

    resp = (
        supabase.table("artists")
        .upsert(
            {"slug": slug, "name": name, "genres": [], "tags": []},
            on_conflict="slug",
        )
        .execute()
    )
    if not resp.data:
        raise RuntimeError(f"Failed to upsert artist '{name}'")

    # Fetch back the ID (upsert may or may not return it depending on Supabase version)
    fetch = (
        supabase.table("artists")
        .select("id")
        .eq("slug", slug)
        .single()
        .execute()
    )
    if not fetch.data:
        raise RuntimeError(f"Could not fetch artist ID for slug '{slug}'")
    return fetch.data["id"]


def upsert_lineup_entry(
    supabase: Client,
    festival_id: str,
    artist_id: str,
    entry: dict,
    dry_run: bool,
) -> None:
    """Upsert a single lineup row."""
    row = {
        "festival_id": festival_id,
        "artist_id": artist_id,
        "year": YEAR,
        "stage": entry["stage"],
        "day": entry["day"],
        "set_time_start": entry["start"],
        "set_time_end": entry["end"],
        "is_headliner": entry["headliner"],
    }
    if dry_run:
        return

    supabase.table("lineups").upsert(
        row,
        on_conflict="festival_id,artist_id,year",
    ).execute()


def check_existing_entries(supabase: Client, festival_id: str) -> int:
    """Return count of existing lineup entries for this festival/year."""
    resp = (
        supabase.table("lineups")
        .select("id", count="exact")
        .eq("festival_id", festival_id)
        .eq("year", YEAR)
        .execute()
    )
    return resp.count or 0


def delete_all_entries(supabase: Client, festival_id: str) -> int:
    """Delete ALL lineup rows for this festival/year and return the deleted count."""
    resp = (
        supabase.table("lineups")
        .delete()
        .eq("festival_id", festival_id)
        .eq("year", YEAR)
        .execute()
    )
    return len(resp.data) if resp.data else 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed the Lollapalooza 2026 schedule into the lineups table."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview all entries without writing to the database.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-seed even if lineup entries already exist for this festival/year.",
    )
    args = parser.parse_args()

    console.rule("[bold cyan]Lollapalooza 2026 Schedule Seeder[/bold cyan]")

    if args.dry_run:
        console.print("[yellow]DRY RUN — no changes will be written to the database.[/yellow]\n")

    supabase = get_supabase()

    # 1. Resolve festival ID
    console.print(f"[dim]Looking up festival:[/dim] [bold]{FESTIVAL_SLUG}[/bold]")
    festival_id = get_festival_id(supabase) if not args.dry_run else "DRY-RUN-FESTIVAL-ID"
    console.print(f"[green]Festival ID:[/green] {festival_id}\n")

    # 2. Guard against accidental re-seeding — or wipe + replace if --force
    if not args.dry_run:
        existing = check_existing_entries(supabase, festival_id)
        if existing > 0 and not args.force:
            console.print(
                f"[yellow]Found {existing} existing lineup entries for {FESTIVAL_SLUG} {YEAR}.[/yellow]\n"
                "[yellow]Use --force to wipe them and re-seed from the canonical schedule.[/yellow]"
            )
            return
        if existing > 0 and args.force:
            console.print(f"[yellow]Wiping {existing} existing entries…[/yellow]")
            deleted = delete_all_entries(supabase, festival_id)
            console.print(f"[green]Deleted {deleted} old entries. Re-seeding from scratch.[/green]\n")

    # 3. Build a preview table for dry-run
    if args.dry_run:
        table = Table(title=f"Schedule preview — {len(SCHEDULE)} slots", show_lines=False)
        table.add_column("Day", style="cyan", no_wrap=True)
        table.add_column("Stage", style="magenta")
        table.add_column("Artist", style="bold white")
        table.add_column("Start")
        table.add_column("End")
        table.add_column("Headliner", justify="center")
        for entry in SCHEDULE:
            table.add_row(
                entry["day"],
                entry["stage"],
                entry["name"],
                entry["start"],
                entry["end"],
                "[green]YES[/green]" if entry["headliner"] else "",
            )
        console.print(table)
        console.print(f"\n[bold green]Dry run complete.[/bold green] {len(SCHEDULE)} entries would be seeded.")
        return

    # 4. Seed
    errors: list[str] = []
    inserted = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    ) as progress:
        task = progress.add_task("[cyan]Seeding schedule…", total=len(SCHEDULE))

        for entry in SCHEDULE:
            artist_name = entry["name"]
            progress.update(task, description=f"[cyan]{artist_name[:40]}")
            try:
                artist_id = upsert_artist(supabase, artist_name, dry_run=False)
                upsert_lineup_entry(supabase, festival_id, artist_id, entry, dry_run=False)
                inserted += 1
            except Exception as exc:
                errors.append(f"{artist_name}: {exc}")
                console.print(f"[red]  ERROR[/red] {artist_name} — {exc}")
            finally:
                progress.advance(task)

    # 5. Summary
    console.rule()
    console.print(f"[bold green]Done.[/bold green]  {inserted}/{len(SCHEDULE)} lineup entries upserted.")
    if errors:
        console.print(f"[bold red]{len(errors)} error(s):[/bold red]")
        for err in errors:
            console.print(f"  [red]•[/red] {err}")
    else:
        console.print("[green]No errors.[/green]")


if __name__ == "__main__":
    main()
