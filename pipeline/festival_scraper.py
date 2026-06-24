"""
festival_scraper.py
-------------------
Scrapes the Wikipedia list of US music festivals and upserts them into Supabase.

Source: https://en.wikipedia.org/wiki/List_of_music_festivals_in_the_United_States

Run:
    python festival_scraper.py                  # full scrape
    python festival_scraper.py --festival "Lollapalooza"  # single festival

Schedule: Weekly via GitHub Actions (etl_weekly.yml)
"""

import os
import re
import time
import logging
import argparse
from slugify import slugify
from dotenv import load_dotenv

import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client
from tenacity import retry, stop_after_attempt, wait_exponential
from rich.console import Console
from rich.progress import track

load_dotenv()
console = Console()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/List_of_music_festivals_in_the_United_States"

# Estimated 2026 dates keyed by slug — computed from historical patterns in
# festival_dates_enricher.py. These are flagged dates_estimated=True so the
# UI shows "~" until the festival officially announces. Update annually.
FESTIVAL_2026_DATES: dict[str, tuple[str, str]] = {
    "lollapalooza":                         ("2026-08-06", "2026-08-09"),
    "coachella":                            ("2026-04-09", "2026-04-18"),
    "electric-daisy-carnival":              ("2026-05-21", "2026-05-23"),
    "south-by-southwest":                   ("2026-03-12", "2026-03-21"),
    "outside-lands":                        ("2026-08-07", "2026-08-09"),
    "ultra-music-festival":                 ("2026-03-20", "2026-03-22"),
    "bonnaroo-music-and-arts-festival":     ("2026-06-11", "2026-06-14"),
    "austin-city-limits-music-festival":    ("2026-10-02", "2026-10-11"),
    "governors-ball":                       ("2026-06-12", "2026-06-14"),
    "stagecoach":                           ("2026-04-24", "2026-04-26"),
    "bottlerock-napa-valley":               ("2026-05-22", "2026-05-24"),
    "rolling-loud":                         ("2026-07-17", "2026-07-19"),
    "firefly-music-festival":               ("2026-06-18", "2026-06-21"),
    "hangout-music-festival":               ("2026-05-15", "2026-05-17"),
    "new-orleans-jazz-heritage-festival":   ("2026-04-24", "2026-05-03"),
    "newport-folk-festival":                ("2026-07-24", "2026-07-26"),
    "essence-festival-of-culture":          ("2026-07-02", "2026-07-05"),
    "life-is-beautiful":                    ("2026-09-18", "2026-09-20"),
    "pitchfork-music-festival":             ("2026-07-10", "2026-07-12"),
    "hard-summer":                          ("2026-08-01", "2026-08-02"),
    "ohana-festival":                       ("2026-09-18", "2026-09-20"),
    "summer-smash":                         ("2026-06-19", "2026-06-21"),
    "when-we-were-young":                   ("2026-10-24", "2026-10-25"),
    "electric-forest":                      ("2026-06-25", "2026-06-28"),
    "voodoo-fest":                          ("2026-10-23", "2026-10-25"),
    "day-n-vegas":                          ("2026-11-06", "2026-11-08"),
    "burning-man":                          ("2026-08-31", "2026-09-08"),
    "shaky-knees-music-festival":           ("2026-05-01", "2026-05-03"),
    "forecastle-festival":                  ("2026-07-10", "2026-07-12"),
    "movement-electronic-music-festival":   ("2026-05-23", "2026-05-25"),
    "riot-fest":                            ("2026-09-11", "2026-09-13"),
    "boston-calling-music-festival":        ("2026-05-23", "2026-05-25"),
    "music-midtown":                        ("2026-09-12", "2026-09-13"),
    "beale-street-music-festival":          ("2026-05-01", "2026-05-03"),
    "newport-jazz-festival":                ("2026-08-07", "2026-08-09"),
    "north-coast-music-festival":           ("2026-08-28", "2026-08-30"),
    "cma-fest":                             ("2026-06-11", "2026-06-14"),
    "chicago-blues-festival":               ("2026-06-05", "2026-06-07"),
    "telluride-bluegrass-festival":         ("2026-06-18", "2026-06-21"),
    "telluride-jazz-festival":              ("2026-08-07", "2026-08-09"),
    "pickathon":                            ("2026-07-31", "2026-08-02"),
    "hardly-strictly-bluegrass":            ("2026-10-02", "2026-10-04"),
    "merlefest":                            ("2026-04-23", "2026-04-26"),
    "spring-awakening-music-festival":      ("2026-06-12", "2026-06-14"),
    "north-coast-music-festival":           ("2026-08-28", "2026-08-30"),
    "faster-horses":                        ("2026-07-17", "2026-07-19"),
    "watershed-festival":                   ("2026-07-31", "2026-08-02"),
    "louder-than-life":                     ("2026-09-25", "2026-09-27"),
    "welcome-to-rockville":                 ("2026-05-08", "2026-05-11"),
    "aftershock-festival":                  ("2026-10-09", "2026-10-11"),
    "suwannee-hulaween":                    ("2026-10-29", "2026-11-01"),
    "sea-hear-now":                         ("2026-09-18", "2026-09-19"),
    "okeechobee-music-and-arts-festival":   ("2026-03-05", "2026-03-08"),
    "lightning-in-a-bottle":               ("2026-05-21", "2026-05-25"),
    "camp-flog-gnaw-carnival":              ("2026-11-07", "2026-11-08"),
    "desert-daze":                          ("2026-10-09", "2026-10-12"),
    "edc-orlando":                          ("2026-11-06", "2026-11-08"),
    "dirtybird-campout":                    ("2026-10-02", "2026-10-05"),
}

# Manual enrichment for the top festivals (Phase 1-2 priority list)
# These fill in fields Wikipedia doesn't have (social handles, colors, etc.)
PRIORITY_FESTIVALS = {
    # ── Big 6 ────────────────────────────────────────────────────
    "Lollapalooza": {
        "city": "Chicago", "state": "IL", "venue": "Grant Park",
        "instagram_handle": "lollapalooza", "x_handle": "lollapalooza",
        "accent_color": "#FF4500",
        "tags": ["multi-genre", "outdoor", "annual", "flagship", "urban", "summer", "midwest"],
        "website_url": "https://www.lollapalooza.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Lollapalooza",
    },
    "Coachella": {
        "city": "Indio", "state": "CA", "venue": "Empire Polo Club",
        "instagram_handle": "coachella", "x_handle": "coachella",
        "accent_color": "#00A878",
        "tags": ["multi-genre", "outdoor", "annual", "flagship", "camping", "southwest", "spring"],
        "website_url": "https://www.coachella.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Coachella_Valley_Music_and_Arts_Festival",
    },
    "Electric Daisy Carnival": {
        "city": "Las Vegas", "state": "NV", "venue": "Las Vegas Motor Speedway",
        "instagram_handle": "electricdaisycarnival", "x_handle": "EDC_LasVegas",
        "accent_color": "#FF007F",
        "tags": ["edm", "electronic", "outdoor", "annual", "flagship", "southwest", "summer"],
        "website_url": "https://lasvegas.electricdaisycarnival.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Electric_Daisy_Carnival",
    },
    "South by Southwest": {
        "city": "Austin", "state": "TX", "venue": "Multiple Venues",
        "instagram_handle": "sxsw", "x_handle": "sxsw",
        "accent_color": "#E63946",
        "tags": ["multi-genre", "indie", "urban", "annual", "flagship", "southeast", "spring"],
        "website_url": "https://www.sxsw.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/South_by_Southwest",
    },
    "Outside Lands": {
        "city": "San Francisco", "state": "CA", "venue": "Golden Gate Park",
        "instagram_handle": "outsidelands", "x_handle": "outsidelands",
        "accent_color": "#00A878",
        "tags": ["multi-genre", "outdoor", "annual", "flagship", "west-coast", "summer"],
        "website_url": "https://www.sfoutsidelands.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Outside_Lands_Music_and_Arts_Festival",
    },
    "Ultra Music Festival": {
        "city": "Miami", "state": "FL", "venue": "Bayfront Park",
        "instagram_handle": "ultra", "x_handle": "ultra",
        "accent_color": "#00D4FF",
        "tags": ["edm", "electronic", "outdoor", "annual", "flagship", "southeast", "spring"],
        "website_url": "https://ultramusicfestival.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Ultra_Music_Festival",
    },
    # ── 20 Additional Major Festivals ────────────────────────────
    "Bonnaroo Music and Arts Festival": {
        "city": "Manchester", "state": "TN", "venue": "The Farm",
        "instagram_handle": "bonnaroo", "x_handle": "bonnaroo",
        "accent_color": "#FF7A45",
        "tags": ["multi-genre", "outdoor", "annual", "camping", "southeast", "summer"],
        "website_url": "https://www.bonnaroo.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Bonnaroo_Music_and_Arts_Festival",
    },
    "Austin City Limits Music Festival": {
        "city": "Austin", "state": "TX", "venue": "Zilker Park",
        "instagram_handle": "aclfestival", "x_handle": "aclfestival",
        "accent_color": "#E63946",
        "tags": ["multi-genre", "outdoor", "annual", "urban", "southeast", "fall"],
        "website_url": "https://www.aclfestival.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Austin_City_Limits_Music_Festival",
    },
    "Governors Ball": {
        "city": "New York", "state": "NY", "venue": "Flushing Meadows Corona Park",
        "instagram_handle": "governorsballnyc", "x_handle": "GovBallNYC",
        "accent_color": "#7B2FBE",
        "tags": ["multi-genre", "outdoor", "annual", "urban", "northeast", "summer"],
        "website_url": "https://www.governorsballmusicfestival.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Governors_Ball_Music_Festival",
    },
    "Stagecoach": {
        "city": "Indio", "state": "CA", "venue": "Empire Polo Club",
        "instagram_handle": "stagecoachfest", "x_handle": "stagecoachfest",
        "accent_color": "#F59E0B",
        "tags": ["country", "outdoor", "annual", "camping", "southwest", "spring"],
        "website_url": "https://www.stagecoachfestival.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Stagecoach_Festival",
    },
    "BottleRock Napa Valley": {
        "city": "Napa", "state": "CA", "venue": "Napa Valley Expo",
        "instagram_handle": "bottlerocknapavalley", "x_handle": "BottleRockNapa",
        "accent_color": "#FF4500",
        "tags": ["multi-genre", "outdoor", "annual", "west-coast", "spring"],
        "website_url": "https://www.bottlerocknapavalley.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/BottleRock_Napa_Valley",
    },
    "Rolling Loud": {
        "city": "Miami", "state": "FL", "venue": "Hard Rock Stadium",
        "instagram_handle": "rollingloud", "x_handle": "RollingLoud",
        "accent_color": "#FF007F",
        "tags": ["hip-hop", "outdoor", "annual", "southeast", "summer"],
        "website_url": "https://rollingloud.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Rolling_Loud",
    },
    "Firefly Music Festival": {
        "city": "Dover", "state": "DE", "venue": "The Woodlands",
        "instagram_handle": "fireflyfest", "x_handle": "fireflyfest",
        "accent_color": "#00D4FF",
        "tags": ["multi-genre", "outdoor", "annual", "camping", "northeast", "summer"],
        "website_url": "https://fireflyfestival.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Firefly_Music_Festival",
    },
    "Hangout Music Festival": {
        "city": "Gulf Shores", "state": "AL", "venue": "Gulf Shores Public Beach",
        "instagram_handle": "hangoutfest", "x_handle": "hangoutfest",
        "accent_color": "#00A878",
        "tags": ["multi-genre", "outdoor", "annual", "southeast", "spring"],
        "website_url": "https://www.hangoutmusicfest.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Hangout_Music_Festival",
    },
    "New Orleans Jazz & Heritage Festival": {
        "city": "New Orleans", "state": "LA", "venue": "Fair Grounds Race Course",
        "instagram_handle": "nojazzfest", "x_handle": "nojazzfest",
        "accent_color": "#FF7A45",
        "tags": ["jazz", "multi-genre", "outdoor", "annual", "southeast", "spring"],
        "website_url": "https://www.nojazzfest.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/New_Orleans_Jazz_%26_Heritage_Festival",
    },
    "Newport Folk Festival": {
        "city": "Newport", "state": "RI", "venue": "Fort Adams State Park",
        "instagram_handle": "newportfolk", "x_handle": "newportfolk",
        "accent_color": "#F59E0B",
        "tags": ["indie", "outdoor", "annual", "northeast", "summer"],
        "website_url": "https://www.newportfolk.org",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Newport_Folk_Festival",
    },
    "Essence Festival of Culture": {
        "city": "New Orleans", "state": "LA", "venue": "Caesars Superdome",
        "instagram_handle": "essencefest", "x_handle": "essencefest",
        "accent_color": "#7B2FBE",
        "tags": ["hip-hop", "r&b", "annual", "southeast", "summer"],
        "website_url": "https://www.essence.com/festival",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Essence_Festival_of_Culture",
    },
    "Life is Beautiful": {
        "city": "Las Vegas", "state": "NV", "venue": "Downtown Las Vegas",
        "instagram_handle": "lifeisbeautiful", "x_handle": "lifeisbeautiful",
        "accent_color": "#00D4FF",
        "tags": ["multi-genre", "outdoor", "annual", "urban", "southwest", "fall"],
        "website_url": "https://lifeisbeautiful.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Life_Is_Beautiful_festival",
    },
    "Pitchfork Music Festival": {
        "city": "Chicago", "state": "IL", "venue": "Union Park",
        "instagram_handle": "pitchforkfest", "x_handle": "pitchforkfest",
        "accent_color": "#E63946",
        "tags": ["indie", "outdoor", "annual", "urban", "midwest", "summer"],
        "website_url": "https://pitchforkmusicfestival.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Pitchfork_Music_Festival",
    },
    "Hard Summer": {
        "city": "Los Angeles", "state": "CA", "venue": "Auto Club Speedway",
        "instagram_handle": "hardfest", "x_handle": "hardfest",
        "accent_color": "#FF007F",
        "tags": ["edm", "electronic", "outdoor", "annual", "west-coast", "summer"],
        "website_url": "https://www.hardfest.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Hard_Summer",
    },
    "Ohana Festival": {
        "city": "Dana Point", "state": "CA", "venue": "Doheny State Beach",
        "instagram_handle": "ohanafest", "x_handle": "ohanafest",
        "accent_color": "#00A878",
        "tags": ["rock", "indie", "outdoor", "annual", "beach", "west-coast", "fall"],
        "website_url": "https://ohanafest.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Ohana_Festival",
    },
    "Summer Smash": {
        "city": "Chicago", "state": "IL", "venue": "Douglass Park",
        "instagram_handle": "summersmashfest", "x_handle": "summersmashfest",
        "accent_color": "#FF4500",
        "tags": ["hip-hop", "outdoor", "annual", "urban", "midwest", "summer"],
        "website_url": "https://www.summersmash.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Summer_Smash",
    },
    "When We Were Young": {
        "city": "Las Vegas", "state": "NV", "venue": "Las Vegas Festival Grounds",
        "instagram_handle": "wwwyfestival", "x_handle": "wwwyfestival",
        "accent_color": "#7B2FBE",
        "tags": ["rock", "outdoor", "annual", "southwest", "fall"],
        "website_url": "https://www.whenwewereyoungfestival.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/When_We_Were_Young_(festival)",
    },
    "Day N Vegas": {
        "city": "Las Vegas", "state": "NV", "venue": "Las Vegas Festival Grounds",
        "instagram_handle": "daynvegas", "x_handle": "daynvegas",
        "accent_color": "#FF007F",
        "tags": ["hip-hop", "outdoor", "annual", "southwest", "fall"],
        "website_url": "https://daynvegas.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Day_N_Vegas",
    },
    "Voodoo Fest": {
        "city": "New Orleans", "state": "LA", "venue": "City Park",
        "instagram_handle": "voodoofest", "x_handle": "voodoofest",
        "accent_color": "#7B2FBE",
        "tags": ["multi-genre", "outdoor", "annual", "southeast", "fall"],
        "website_url": "https://voodoofest.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Voodoo_Experience",
    },
    "Electric Forest": {
        "city": "Rothbury", "state": "MI", "venue": "Double JJ Resort",
        "instagram_handle": "electricforest", "x_handle": "electricforest",
        "accent_color": "#00A878",
        "tags": ["edm", "electronic", "outdoor", "annual", "camping", "midwest", "summer"],
        "website_url": "https://electricforestfestival.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Electric_Forest_Festival",
    },
    # ── Rock / Indie ─────────────────────────────────────────────
    "Shaky Knees Music Festival": {
        "city": "Atlanta", "state": "GA", "venue": "Central Park",
        "instagram_handle": "shakykneesfest", "x_handle": "shakykneesfest",
        "accent_color": "#E63946",
        "tags": ["rock", "indie", "outdoor", "annual", "southeast", "spring"],
        "website_url": "https://shakykneesfestival.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Shaky_Knees_Music_Festival",
    },
    "Ohana Festival": {
        "city": "Dana Point", "state": "CA", "venue": "Doheny State Beach",
        "instagram_handle": "ohanafest", "x_handle": "ohanafest",
        "accent_color": "#00A878",
        "tags": ["rock", "indie", "outdoor", "annual", "west-coast", "fall"],
        "website_url": "https://ohanafest.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Ohana_Festival",
    },
    "Forecastle Festival": {
        "city": "Louisville", "state": "KY", "venue": "Waterfront Park",
        "instagram_handle": "forecastlefest", "x_handle": "forecastlefest",
        "accent_color": "#00D4FF",
        "tags": ["rock", "indie", "outdoor", "annual", "midwest", "summer"],
        "website_url": "https://forecastlefest.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Forecastle_Festival",
    },
    "Innings Festival": {
        "city": "Tempe", "state": "AZ", "venue": "Tempe Beach Park",
        "instagram_handle": "inningsfestival", "x_handle": "inningsfestival",
        "accent_color": "#FF7A45",
        "tags": ["rock", "outdoor", "annual", "southwest", "spring"],
        "website_url": "https://www.inningsfestival.com",
        "wikipedia_url": None,
    },
    "Riot Fest": {
        "city": "Chicago", "state": "IL", "venue": "Douglas Park",
        "instagram_handle": "riotfest", "x_handle": "riotfest",
        "accent_color": "#E63946",
        "tags": ["rock", "punk", "outdoor", "annual", "urban", "midwest", "fall"],
        "website_url": "https://riotfest.org",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Riot_Fest",
    },
    "Boston Calling Music Festival": {
        "city": "Boston", "state": "MA", "venue": "Harvard Athletic Complex",
        "instagram_handle": "bostoncalling", "x_handle": "bostoncalling",
        "accent_color": "#00D4FF",
        "tags": ["multi-genre", "outdoor", "annual", "urban", "northeast", "spring"],
        "website_url": "https://www.bostoncalling.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Boston_Calling_Music_Festival",
    },
    "Louder Than Life": {
        "city": "Louisville", "state": "KY", "venue": "Highland Festival Grounds",
        "instagram_handle": "louderthanlife", "x_handle": "louderthanlife",
        "accent_color": "#7B2FBE",
        "tags": ["rock", "metal", "outdoor", "annual", "midwest", "fall"],
        "website_url": "https://louderthanlifefestival.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Louder_Than_Life",
    },
    "Welcome to Rockville": {
        "city": "Daytona Beach", "state": "FL", "venue": "Daytona International Speedway",
        "instagram_handle": "welcometorockville", "x_handle": "rockvillefest",
        "accent_color": "#E63946",
        "tags": ["rock", "metal", "outdoor", "annual", "southeast", "spring"],
        "website_url": "https://welcometorockvillefestival.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Welcome_to_Rockville",
    },
    "Aftershock Festival": {
        "city": "Sacramento", "state": "CA", "venue": "Discovery Park",
        "instagram_handle": "aftershockfest", "x_handle": "aftershockfest",
        "accent_color": "#FF007F",
        "tags": ["rock", "metal", "outdoor", "annual", "west-coast", "fall"],
        "website_url": "https://aftershockfestival.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Aftershock_Festival",
    },
    "Carolina Country Music Fest": {
        "city": "Myrtle Beach", "state": "SC", "venue": "Myrtle Beach",
        "instagram_handle": "ccmfest", "x_handle": "ccmfest",
        "accent_color": "#F59E0B",
        "tags": ["country", "outdoor", "annual", "southeast", "summer"],
        "website_url": "https://ccmfest.com",
        "wikipedia_url": None,
    },
    # ── Electronic / EDM ─────────────────────────────────────────
    "Movement Electronic Music Festival": {
        "city": "Detroit", "state": "MI", "venue": "Hart Plaza",
        "instagram_handle": "movementdetroit", "x_handle": "movementdetroit",
        "accent_color": "#FF007F",
        "tags": ["electronic", "edm", "outdoor", "annual", "urban", "midwest", "spring"],
        "website_url": "https://movement.us",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Movement_(music_festival)",
    },
    "EDC Orlando": {
        "city": "Orlando", "state": "FL", "venue": "Tinker Field",
        "instagram_handle": "edcorlando", "x_handle": "EDC_Orlando",
        "accent_color": "#FF007F",
        "tags": ["edm", "electronic", "outdoor", "annual", "southeast", "fall"],
        "website_url": "https://orlando.electricdaisycarnival.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Electric_Daisy_Carnival",
    },
    "Dirtybird Campout": {
        "city": "Modesto", "state": "CA", "venue": "Modesto Reservoir",
        "instagram_handle": "dirtybirdrecords", "x_handle": "dirtybirdrecords",
        "accent_color": "#00A878",
        "tags": ["electronic", "edm", "outdoor", "annual", "camping", "west-coast", "fall"],
        "website_url": "https://dirtybirdcampout.com",
        "wikipedia_url": None,
    },
    "Lightning in a Bottle": {
        "city": "Buena Vista Lake", "state": "CA", "venue": "Kern County",
        "instagram_handle": "lightninginabottle", "x_handle": "libfestival",
        "accent_color": "#F59E0B",
        "tags": ["electronic", "edm", "outdoor", "annual", "camping", "west-coast", "spring"],
        "website_url": "https://www.lightninginabottle.org",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Lightning_in_a_Bottle_(festival)",
    },
    "Okeechobee Music and Arts Festival": {
        "city": "Okeechobee", "state": "FL", "venue": "Sunshine Grove",
        "instagram_handle": "okeechobeefest", "x_handle": "okeechobeefest",
        "accent_color": "#00D4FF",
        "tags": ["multi-genre", "electronic", "outdoor", "annual", "camping", "southeast", "spring"],
        "website_url": "https://www.okeechobeefest.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Okeechobee_Music_and_Arts_Festival",
    },
    "Spring Awakening Music Festival": {
        "city": "Chicago", "state": "IL", "venue": "Addams/Medill Park",
        "instagram_handle": "springawakeningfest", "x_handle": "springawakeningfest",
        "accent_color": "#FF007F",
        "tags": ["edm", "electronic", "outdoor", "annual", "urban", "midwest", "summer"],
        "website_url": "https://www.springawakeningfestival.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Spring_Awakening_Music_Festival",
    },
    "Dreamstate": {
        "city": "San Bernardino", "state": "CA", "venue": "NOS Events Center",
        "instagram_handle": "dreamstateusa", "x_handle": "dreamstateusa",
        "accent_color": "#7B2FBE",
        "tags": ["electronic", "edm", "indoor", "annual", "west-coast", "fall"],
        "website_url": "https://dreamstate.us",
        "wikipedia_url": None,
    },
    # ── Hip-Hop / R&B ─────────────────────────────────────────────
    "Rolling Loud California": {
        "city": "Inglewood", "state": "CA", "venue": "Hollywood Park",
        "instagram_handle": "rollingloud", "x_handle": "RollingLoud",
        "accent_color": "#FF007F",
        "tags": ["hip-hop", "outdoor", "annual", "west-coast", "summer"],
        "website_url": "https://rollingloud.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Rolling_Loud",
    },
    "Rolling Loud New York": {
        "city": "Queens", "state": "NY", "venue": "Citi Field",
        "instagram_handle": "rollingloud", "x_handle": "RollingLoud",
        "accent_color": "#FF007F",
        "tags": ["hip-hop", "outdoor", "annual", "northeast", "fall"],
        "website_url": "https://rollingloud.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Rolling_Loud",
    },
    "Summer Smash": {
        "city": "Chicago", "state": "IL", "venue": "Douglass Park",
        "instagram_handle": "summersmashfest", "x_handle": "summersmashfest",
        "accent_color": "#FF4500",
        "tags": ["hip-hop", "outdoor", "annual", "urban", "midwest", "summer"],
        "website_url": "https://www.summersmash.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Summer_Smash",
    },
    "BET Hip Hop Awards Weekend": {
        "city": "Atlanta", "state": "GA", "venue": "Various",
        "instagram_handle": "bet", "x_handle": "bet",
        "accent_color": "#7B2FBE",
        "tags": ["hip-hop", "r&b", "indoor", "annual", "southeast", "fall"],
        "website_url": "https://www.bet.com/shows/bet-hip-hop-awards",
        "wikipedia_url": None,
    },
    # ── Country ───────────────────────────────────────────────────
    "CMA Fest": {
        "city": "Nashville", "state": "TN", "venue": "Nissan Stadium",
        "instagram_handle": "cmafest", "x_handle": "cmafest",
        "accent_color": "#F59E0B",
        "tags": ["country", "outdoor", "annual", "southeast", "summer"],
        "website_url": "https://www.cmafest.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/CMA_Music_Festival",
    },
    "WE Fest": {
        "city": "Detroit Lakes", "state": "MN", "venue": "Soo Pass Ranch",
        "instagram_handle": "wefest", "x_handle": "wefest",
        "accent_color": "#F59E0B",
        "tags": ["country", "outdoor", "annual", "camping", "midwest", "summer"],
        "website_url": "https://www.wefest.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/WE_Fest",
    },
    "Faster Horses": {
        "city": "Brooklyn", "state": "MI", "venue": "Michigan International Speedway",
        "instagram_handle": "fasterhorsesfest", "x_handle": "fasterhorsesfest",
        "accent_color": "#F59E0B",
        "tags": ["country", "outdoor", "annual", "camping", "midwest", "summer"],
        "website_url": "https://www.fasterhorsesmi.com",
        "wikipedia_url": None,
    },
    "Watershed Festival": {
        "city": "George", "state": "WA", "venue": "The Gorge Amphitheatre",
        "instagram_handle": "watershedfest", "x_handle": "watershedfest",
        "accent_color": "#00A878",
        "tags": ["country", "outdoor", "annual", "camping", "west-coast", "summer"],
        "website_url": "https://www.watershedfest.com",
        "wikipedia_url": None,
    },
    "Tortuga Music Festival": {
        "city": "Fort Lauderdale", "state": "FL", "venue": "Fort Lauderdale Beach",
        "instagram_handle": "tortugamusicfest", "x_handle": "tortugamusicfest",
        "accent_color": "#00D4FF",
        "tags": ["country", "rock", "outdoor", "annual", "beach", "southeast", "spring"],
        "website_url": "https://www.tortugamusicfestival.com",
        "wikipedia_url": None,
    },
    "Boots & Hearts": {
        "city": "Bowmanville", "state": "ON", "venue": "Burl's Creek Event Grounds",
        "instagram_handle": "bootsandhearts", "x_handle": "bootsandhearts",
        "accent_color": "#F59E0B",
        "tags": ["country", "outdoor", "annual", "camping", "summer"],
        "website_url": "https://www.bootsandhearts.com",
        "wikipedia_url": None,
    },
    # ── Jazz / Blues ──────────────────────────────────────────────
    "Chicago Blues Festival": {
        "city": "Chicago", "state": "IL", "venue": "Millennium Park",
        "instagram_handle": "chicagobluest", "x_handle": "chicagobluest",
        "accent_color": "#00D4FF",
        "tags": ["blues", "outdoor", "annual", "urban", "midwest", "summer"],
        "website_url": "https://www.chicago.gov/city/en/depts/dca/supp_info/chicago_blues_festival.html",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Chicago_Blues_Festival",
    },
    "Newport Jazz Festival": {
        "city": "Newport", "state": "RI", "venue": "Fort Adams State Park",
        "instagram_handle": "newportjazz", "x_handle": "newportjazz",
        "accent_color": "#7B2FBE",
        "tags": ["jazz", "outdoor", "annual", "northeast", "summer"],
        "website_url": "https://www.newportjazz.org",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Newport_Jazz_Festival",
    },
    "Detroit Jazz Festival": {
        "city": "Detroit", "state": "MI", "venue": "Hart Plaza",
        "instagram_handle": "detroitjazzfest", "x_handle": "detroitjazzfest",
        "accent_color": "#FF7A45",
        "tags": ["jazz", "outdoor", "annual", "urban", "midwest", "summer"],
        "website_url": "https://detroitjazzfest.org",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Detroit_Jazz_Festival",
    },
    "Telluride Jazz Festival": {
        "city": "Telluride", "state": "CO", "venue": "Town Park",
        "instagram_handle": "telluridejazz", "x_handle": "telluridejazz",
        "accent_color": "#00A878",
        "tags": ["jazz", "outdoor", "annual", "mountain", "summer"],
        "website_url": "https://www.telluridejazz.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Telluride_Jazz_Festival",
    },
    # ── Folk / Americana ──────────────────────────────────────────
    "Hardly Strictly Bluegrass": {
        "city": "San Francisco", "state": "CA", "venue": "Golden Gate Park",
        "instagram_handle": "hardlystrictly", "x_handle": "hardlystrictly",
        "accent_color": "#F59E0B",
        "tags": ["folk", "country", "outdoor", "annual", "west-coast", "fall"],
        "website_url": "https://www.hardlystrictlybluegrass.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Hardly_Strictly_Bluegrass",
    },
    "Pickathon": {
        "city": "Happy Valley", "state": "OR", "venue": "Pendarvis Farm",
        "instagram_handle": "pickathon", "x_handle": "pickathon",
        "accent_color": "#FF7A45",
        "tags": ["folk", "indie", "outdoor", "annual", "camping", "west-coast", "summer"],
        "website_url": "https://pickathon.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Pickathon",
    },
    "Telluride Bluegrass Festival": {
        "city": "Telluride", "state": "CO", "venue": "Town Park",
        "instagram_handle": "telluridebluegrass", "x_handle": "telluridebluegrass",
        "accent_color": "#00A878",
        "tags": ["folk", "country", "outdoor", "annual", "camping", "mountain", "summer"],
        "website_url": "https://www.bluegrass.com/telluride",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Telluride_Bluegrass_Festival",
    },
    "MerleFest": {
        "city": "Wilkesboro", "state": "NC", "venue": "Wilkes Community College",
        "instagram_handle": "merlefest", "x_handle": "merlefest",
        "accent_color": "#F59E0B",
        "tags": ["folk", "country", "outdoor", "annual", "southeast", "spring"],
        "website_url": "https://merlefest.org",
        "wikipedia_url": "https://en.wikipedia.org/wiki/MerleFest",
    },
    # ── Multi-genre / Regional ────────────────────────────────────
    "Burning Man": {
        "city": "Black Rock City", "state": "NV", "venue": "Black Rock Desert",
        "instagram_handle": "burningman", "x_handle": "burningman",
        "accent_color": "#FF7A45",
        "tags": ["multi-genre", "edm", "outdoor", "annual", "camping", "southwest", "summer"],
        "website_url": "https://burningman.org",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Burning_Man",
    },
    "Suwannee Hulaween": {
        "city": "Live Oak", "state": "FL", "venue": "Spirit of the Suwannee Music Park",
        "instagram_handle": "suwanneehulaween", "x_handle": "suwanneehulaween",
        "accent_color": "#7B2FBE",
        "tags": ["multi-genre", "electronic", "outdoor", "annual", "camping", "southeast", "fall"],
        "website_url": "https://www.hulaween.com",
        "wikipedia_url": None,
    },
    "Bonnaroo Music and Arts Festival": {
        "city": "Manchester", "state": "TN", "venue": "The Farm",
        "instagram_handle": "bonnaroo", "x_handle": "bonnaroo",
        "accent_color": "#FF7A45",
        "tags": ["multi-genre", "outdoor", "annual", "camping", "southeast", "summer"],
        "website_url": "https://www.bonnaroo.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Bonnaroo_Music_and_Arts_Festival",
    },
    "Hangout Music Festival": {
        "city": "Gulf Shores", "state": "AL", "venue": "Gulf Shores Public Beach",
        "instagram_handle": "hangoutfest", "x_handle": "hangoutfest",
        "accent_color": "#00A878",
        "tags": ["multi-genre", "outdoor", "annual", "beach", "southeast", "spring"],
        "website_url": "https://www.hangoutmusicfest.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Hangout_Music_Festival",
    },
    "North Coast Music Festival": {
        "city": "Chicago", "state": "IL", "venue": "Union Park",
        "instagram_handle": "northcoastfest", "x_handle": "northcoastfest",
        "accent_color": "#00D4FF",
        "tags": ["multi-genre", "electronic", "outdoor", "annual", "urban", "midwest", "summer"],
        "website_url": "https://www.northcoastfestival.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/North_Coast_Music_Festival",
    },
    "Panorama Music Festival": {
        "city": "New York", "state": "NY", "venue": "Randall's Island Park",
        "instagram_handle": "panoramanyc", "x_handle": "panoramanyc",
        "accent_color": "#7B2FBE",
        "tags": ["multi-genre", "outdoor", "annual", "urban", "northeast", "summer"],
        "website_url": "https://www.panoramafestival.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Panorama_Music_Festival",
    },
    "Music Midtown": {
        "city": "Atlanta", "state": "GA", "venue": "Piedmont Park",
        "instagram_handle": "musicmidtown", "x_handle": "musicmidtown",
        "accent_color": "#E63946",
        "tags": ["multi-genre", "outdoor", "annual", "urban", "southeast", "fall"],
        "website_url": "https://www.musicmidtown.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Music_Midtown",
    },
    "Desert Daze": {
        "city": "Perris", "state": "CA", "venue": "Lake Perris",
        "instagram_handle": "desertdaze", "x_handle": "desertdaze",
        "accent_color": "#FF7A45",
        "tags": ["indie", "rock", "outdoor", "annual", "camping", "southwest", "fall"],
        "website_url": "https://desertdaze.org",
        "wikipedia_url": None,
    },
    "Camp Flog Gnaw Carnival": {
        "city": "Los Angeles", "state": "CA", "venue": "Dodger Stadium",
        "instagram_handle": "campfloggnaw", "x_handle": "campfloggnaw",
        "accent_color": "#FF007F",
        "tags": ["hip-hop", "multi-genre", "outdoor", "annual", "west-coast", "fall"],
        "website_url": "https://campfloggnaw.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Camp_Flog_Gnaw_Carnival",
    },
    "FYF Fest": {
        "city": "Los Angeles", "state": "CA", "venue": "Exposition Park",
        "instagram_handle": "fyffest", "x_handle": "fyffest",
        "accent_color": "#E63946",
        "tags": ["indie", "multi-genre", "outdoor", "annual", "west-coast", "summer"],
        "website_url": "https://fyffest.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/FYF_Fest",
    },
    "Meadows Music and Arts Festival": {
        "city": "New York", "state": "NY", "venue": "Citi Field",
        "instagram_handle": "meadowsfestnyc", "x_handle": "meadowsfestnyc",
        "accent_color": "#00A878",
        "tags": ["multi-genre", "outdoor", "annual", "urban", "northeast", "fall"],
        "website_url": "https://www.meadowsfest.com",
        "wikipedia_url": None,
    },
    "Pemberton Music Festival": {
        "city": "Pemberton", "state": "BC", "venue": "Pemberton Festival Site",
        "instagram_handle": "pembertonfest", "x_handle": "pembertonfest",
        "accent_color": "#00A878",
        "tags": ["multi-genre", "outdoor", "annual", "camping", "summer"],
        "website_url": "https://www.pembertonmusicfestival.com",
        "wikipedia_url": None,
    },
    "Lakeshake Festival": {
        "city": "Chicago", "state": "IL", "venue": "Huntington Bank Pavilion",
        "instagram_handle": "lakeshakechicago", "x_handle": "lakeshakechicago",
        "accent_color": "#F59E0B",
        "tags": ["country", "outdoor", "annual", "urban", "midwest", "summer"],
        "website_url": "https://www.lakeshakefestival.com",
        "wikipedia_url": None,
    },
    "Slam Dunk Festival": {
        "city": "Baltimore", "state": "MD", "venue": "Pimlico Race Course",
        "instagram_handle": "slamdunkfest", "x_handle": "slamdunkfest",
        "accent_color": "#E63946",
        "tags": ["punk", "rock", "outdoor", "annual", "northeast", "summer"],
        "website_url": "https://slamdunkfestival.com",
        "wikipedia_url": None,
    },
    "Sea.Hear.Now": {
        "city": "Asbury Park", "state": "NJ", "venue": "Bradley Park",
        "instagram_handle": "seahearnow", "x_handle": "seahearnow",
        "accent_color": "#00D4FF",
        "tags": ["rock", "indie", "outdoor", "annual", "northeast", "fall"],
        "website_url": "https://www.seahearnowfestival.com",
        "wikipedia_url": None,
    },
    "Moon River Music Festival": {
        "city": "Chattanooga", "state": "TN", "venue": "Ross's Landing",
        "instagram_handle": "moonriverfest", "x_handle": "moonriverfest",
        "accent_color": "#00A878",
        "tags": ["indie", "folk", "outdoor", "annual", "southeast", "fall"],
        "website_url": "https://moonriverfestival.com",
        "wikipedia_url": None,
    },
    "Beale Street Music Festival": {
        "city": "Memphis", "state": "TN", "venue": "Tom Lee Park",
        "instagram_handle": "memphisinmay", "x_handle": "memphisinmay",
        "accent_color": "#FF7A45",
        "tags": ["multi-genre", "outdoor", "annual", "southeast", "spring"],
        "website_url": "https://memphisinmay.org",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Beale_Street_Music_Festival",
    },
    "Pointfest": {
        "city": "St. Louis", "state": "MO", "venue": "Hollywood Casino Amphitheatre",
        "instagram_handle": "pointfest", "x_handle": "pointfest",
        "accent_color": "#E63946",
        "tags": ["rock", "outdoor", "annual", "midwest", "summer"],
        "website_url": "https://www.pointfest.com",
        "wikipedia_url": None,
    },
    "Live on the Green": {
        "city": "Nashville", "state": "TN", "venue": "Public Square Park",
        "instagram_handle": "liveonthegreen", "x_handle": "liveonthegreen",
        "accent_color": "#00A878",
        "tags": ["multi-genre", "outdoor", "annual", "urban", "southeast", "summer"],
        "website_url": "https://www.liveonthegreen.net",
        "wikipedia_url": None,
    },
    # ── Las Vegas / Southwest ─────────────────────────────────────
    "When We Were Young": {
        "city": "Las Vegas", "state": "NV", "venue": "Las Vegas Festival Grounds",
        "instagram_handle": "wwwyfestival", "x_handle": "wwwyfestival",
        "accent_color": "#7B2FBE",
        "tags": ["rock", "outdoor", "annual", "southwest", "fall"],
        "website_url": "https://www.whenwewereyoungfestival.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/When_We_Were_Young_(festival)",
    },
    "Day N Vegas": {
        "city": "Las Vegas", "state": "NV", "venue": "Las Vegas Festival Grounds",
        "instagram_handle": "daynvegas", "x_handle": "daynvegas",
        "accent_color": "#FF007F",
        "tags": ["hip-hop", "outdoor", "annual", "southwest", "fall"],
        "website_url": "https://daynvegas.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Day_N_Vegas",
    },
    "Punk in Drublic": {
        "city": "Various", "state": "CA", "venue": "Various",
        "instagram_handle": "punkindrublicfest", "x_handle": "punkindrublicfest",
        "accent_color": "#E63946",
        "tags": ["punk", "rock", "outdoor", "annual", "west-coast", "summer"],
        "website_url": "https://www.punkindrublic.com",
        "wikipedia_url": None,
    },
    # ── New Orleans / Gulf ────────────────────────────────────────
    "New Orleans Jazz & Heritage Festival": {
        "city": "New Orleans", "state": "LA", "venue": "Fair Grounds Race Course",
        "instagram_handle": "nojazzfest", "x_handle": "nojazzfest",
        "accent_color": "#FF7A45",
        "tags": ["jazz", "multi-genre", "outdoor", "annual", "southeast", "spring"],
        "website_url": "https://www.nojazzfest.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/New_Orleans_Jazz_%26_Heritage_Festival",
    },
    "Voodoo Fest": {
        "city": "New Orleans", "state": "LA", "venue": "City Park",
        "instagram_handle": "voodoofest", "x_handle": "voodoofest",
        "accent_color": "#7B2FBE",
        "tags": ["multi-genre", "outdoor", "annual", "southeast", "fall"],
        "website_url": "https://voodoofest.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Voodoo_Experience",
    },
    "Essence Festival of Culture": {
        "city": "New Orleans", "state": "LA", "venue": "Caesars Superdome",
        "instagram_handle": "essencefest", "x_handle": "essencefest",
        "accent_color": "#7B2FBE",
        "tags": ["hip-hop", "r&b", "annual", "southeast", "summer"],
        "website_url": "https://www.essence.com/festival",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Essence_Festival_of_Culture",
    },
}


def get_supabase() -> Client:
    url = os.environ["NEXT_PUBLIC_SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_wikipedia() -> BeautifulSoup:
    console.log("[cyan]Fetching Wikipedia festival list...")
    resp = requests.get(WIKIPEDIA_URL, headers={"User-Agent": "FestivalAnalyzerBot/1.0"}, timeout=15)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def parse_festivals(soup: BeautifulSoup) -> list[dict]:
    """
    Parses the Wikipedia table(s) for US music festivals.
    Returns a list of dicts with festival metadata.
    """
    festivals = []
    tables = soup.find_all("table", class_="wikitable")

    for table in tables:
        rows = table.find_all("tr")[1:]  # skip header
        for row in rows:
            cells = row.find_all(["td", "th"])
            if not cells:
                continue
            try:
                name_cell = cells[0]
                name = name_cell.get_text(strip=True)
                if not name:
                    continue

                # Try to extract Wikipedia link for this festival
                wiki_link = name_cell.find("a", href=True)
                wiki_url = f"https://en.wikipedia.org{wiki_link['href']}" if wiki_link else None

                # Try to extract location from subsequent cells
                city, state = None, None
                if len(cells) > 1:
                    location_text = cells[1].get_text(strip=True)
                    parts = [p.strip() for p in location_text.split(",")]
                    if len(parts) >= 2:
                        city = parts[0]
                        state = parts[1][:2].upper() if parts[1] else None

                festival = {
                    "slug": slugify(name),
                    "name": name,
                    "city": city,
                    "state": state,
                    "wikipedia_url": wiki_url,
                    "tags": [],
                    "is_active": True,
                }

                # Merge in priority data if available
                for priority_name, priority_data in PRIORITY_FESTIVALS.items():
                    if priority_name.lower() in name.lower():
                        festival.update(priority_data)
                        break

                festivals.append(festival)
            except Exception as e:
                log.warning(f"Failed to parse row: {e}")
                continue

    console.log(f"[green]Parsed {len(festivals)} festivals from Wikipedia")
    return festivals


def upsert_festivals(supabase: Client, festivals: list[dict]) -> None:
    """Upserts festival records into Supabase."""
    console.log(f"[cyan]Upserting {len(festivals)} festivals...")
    for festival in track(festivals, description="Upserting festivals..."):
        try:
            supabase.table("festivals").upsert(festival, on_conflict="slug").execute()
        except Exception as e:
            log.error(f"Failed to upsert {festival.get('name')}: {e}")
    console.log("[green]Done upserting festivals")


def _apply_dates(festival: dict, year: int = 2026) -> dict:
    """Merge estimated dates from FESTIVAL_2026_DATES if none are set."""
    slug = festival.get("slug", "")
    if festival.get("start_date"):
        return festival
    if year == 2026 and slug in FESTIVAL_2026_DATES:
        start, end = FESTIVAL_2026_DATES[slug]
        return {**festival, "start_date": start, "end_date": end, "dates_estimated": True}
    return festival


def scrape_single(supabase: Client, festival_name: str) -> None:
    """Upsert a single festival by name from the priority list."""
    name_lower = festival_name.lower()
    match = next(
        (v | {"name": k, "slug": slugify(k)} for k, v in PRIORITY_FESTIVALS.items() if k.lower() == name_lower),
        None
    )
    if not match:
        console.log(f"[red]{festival_name} not found in priority list. Add it to PRIORITY_FESTIVALS first.")
        return
    match = _apply_dates(match)
    supabase.table("festivals").upsert(match, on_conflict="slug").execute()
    console.log(f"[green]Upserted: {festival_name}")


def update_dates_only(supabase: Client, year: int = 2026) -> None:
    """Push dates from FESTIVAL_2026_DATES to any festival rows that still have null start_date."""
    updated = 0
    for slug, (start, end) in FESTIVAL_2026_DATES.items():
        r = supabase.table("festivals").select("id, name, start_date").eq("slug", slug).execute()
        if not r.data:
            console.log(f"[yellow]Not in DB: {slug}")
            continue
        row = r.data[0]
        if row.get("start_date"):
            console.log(f"[dim]{row['name']}: already has dates — skipping")
            continue
        supabase.table("festivals").update({
            "start_date": start,
            "end_date": end,
            "dates_estimated": True,
        }).eq("id", row["id"]).execute()
        console.log(f"[green]Updated dates: {row['name']}  {start} → {end}")
        updated += 1
    console.log(f"[bold green]Done — {updated} festivals updated.")


def main():
    parser = argparse.ArgumentParser(description="Scrape US music festivals into Supabase")
    parser.add_argument("--festival", type=str, help="Scrape only this festival name")
    parser.add_argument("--priority-only", action="store_true", help="Only upsert PRIORITY_FESTIVALS")
    parser.add_argument("--update-dates", action="store_true",
                        help="Push FESTIVAL_2026_DATES to any DB row still missing start_date")
    parser.add_argument("--year", type=int, default=2026, help="Year for estimated dates")
    args = parser.parse_args()

    supabase = get_supabase()

    if args.update_dates:
        update_dates_only(supabase, year=args.year)
        return

    if args.festival:
        scrape_single(supabase, args.festival)
        return

    if args.priority_only:
        festivals = [
            _apply_dates({"name": k, "slug": slugify(k), **v}, year=args.year)
            for k, v in PRIORITY_FESTIVALS.items()
        ]
        upsert_festivals(supabase, festivals)
        return

    soup = fetch_wikipedia()
    festivals = parse_festivals(soup)
    upsert_festivals(supabase, festivals)


if __name__ == "__main__":
    main()
