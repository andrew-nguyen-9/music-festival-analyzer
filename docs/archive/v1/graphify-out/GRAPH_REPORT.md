# Graph Report - .  (2026-06-15)

## Corpus Check
- Corpus is ~45,095 words - fits in a single context window. You may not need a graph.

## Summary
- 548 nodes · 1083 edges · 28 communities (24 shown, 4 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 96 edges (avg confidence: 0.89)
- Token cost: 12,500 input · 3,200 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Festival Pages & App Routing|Festival Pages & App Routing]]
- [[_COMMUNITY_Festival Page Tabs & Lineup Display|Festival Page Tabs & Lineup Display]]
- [[_COMMUNITY_Festival Art Generation Pipeline|Festival Art Generation Pipeline]]
- [[_COMMUNITY_AI Fun Facts & Schedule Seeding|AI Fun Facts & Schedule Seeding]]
- [[_COMMUNITY_Artist Profile Components|Artist Profile Components]]
- [[_COMMUNITY_Festival Theming & Artist Hero|Festival Theming & Artist Hero]]
- [[_COMMUNITY_Artist Enrichment (SpotifyDeezer)|Artist Enrichment (Spotify/Deezer)]]
- [[_COMMUNITY_Festival Grid & Empty States|Festival Grid & Empty States]]
- [[_COMMUNITY_Frontend Dependencies & Config|Frontend Dependencies & Config]]
- [[_COMMUNITY_Festival Discovery Scraper|Festival Discovery Scraper]]
- [[_COMMUNITY_TypeScript Configuration|TypeScript Configuration]]
- [[_COMMUNITY_Festival Dates Enrichment|Festival Dates Enrichment]]
- [[_COMMUNITY_Schedule Scraping (TMSongkickVision)|Schedule Scraping (TM/Songkick/Vision)]]
- [[_COMMUNITY_Lineup Scraping (TMSetlist.fm)|Lineup Scraping (TM/Setlist.fm)]]
- [[_COMMUNITY_Root Layout & Error Pages|Root Layout & Error Pages]]
- [[_COMMUNITY_External API Reference Docs|External API Reference Docs]]
- [[_COMMUNITY_Apple Music & UI Spec|Apple Music & UI Spec]]
- [[_COMMUNITY_Lineup Manager Pipeline|Lineup Manager Pipeline]]
- [[_COMMUNITY_System Architecture Diagram|System Architecture Diagram]]
- [[_COMMUNITY_Media Fetcher (Unsplash)|Media Fetcher (Unsplash)]]
- [[_COMMUNITY_Supabase API & Handoff Docs|Supabase API & Handoff Docs]]
- [[_COMMUNITY_Project Conventions & Roadmap|Project Conventions & Roadmap]]
- [[_COMMUNITY_Project README & Design Notes|Project README & Design Notes]]
- [[_COMMUNITY_Error Boundaries|Error Boundaries]]
- [[_COMMUNITY_Next.js Config|Next.js Config]]
- [[_COMMUNITY_PostCSS Config|PostCSS Config]]
- [[_COMMUNITY_Package JSON|Package JSON]]

## God Nodes (most connected - your core abstractions)
1. `Festival` - 23 edges
2. `accentGradient()` - 18 edges
3. `LineupEntry` - 18 edges
4. `Reveal()` - 17 edges
5. `compilerOptions` - 16 edges
6. `generate_festival_svg()` - 16 edges
7. `Festivals Table` - 15 edges
8. `getSupabase()` - 14 edges
9. `UI Specification Document` - 14 edges
10. `warn()` - 12 edges

## Surprising Connections (you probably didn't know these)
- `Festival Analyzer System Architecture Diagram` --conceptually_related_to--> `Festival Analyzer Tech Stack`  [INFERRED]
  festival_analyzer_architecture.svg → README.md
- `Free Tier Scalability Strategy` --semantically_similar_to--> `Supabase Edge Functions (optional OAuth token proxy)`  [INFERRED] [semantically similar]
  README.md → festival-analyzer/docs/API_REFERENCE.md
- `ETL Pipeline Layer (Python + GitHub Actions cron)` --conceptually_related_to--> `ETL Daily Workflow (GitHub Actions)`  [INFERRED]
  festival_analyzer_architecture.svg → festival-analyzer/.github/workflows/etl_daily.yml
- `Frontend Layer (Next.js 14 on Vercel)` --conceptually_related_to--> `UI Specification Document`  [INFERRED]
  festival_analyzer_architecture.svg → festival-analyzer/docs/UI_SPEC.md
- `SocialPost` --references--> `social_posts table`  [INFERRED]
  festival-analyzer/frontend/lib/types.ts → schema.sql

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Artist Page Component Composition** — slug_page_artistpage, components_artisthero_artisthero, components_artistdiscography_artistdiscography, components_festivalappearances_festivalappearances [EXTRACTED 1.00]
- **Core Database Tables (Supabase Schema)** — db_schema_festivals_table, db_schema_artists_table, db_schema_lineups_table, db_schema_media_table, db_schema_social_posts_table, db_schema_fun_facts_table, db_schema_tags_table [EXTRACTED 1.00]
- **Accessibility: Reduced Motion Pattern** — components_customcursor_customcursor, components_draggablenotes_draggablenotes, concept_reduced_motion [EXTRACTED 1.00]
- **Lineup Display Mode Components** — components_lineubbyday_lineupbyday, components_lineupbypopularity_lineupbypopularity, components_lineupgrid_lineupgrid, components_festivalpagetabs_lineuplistview [INFERRED 0.90]
- **Headliner Detection Pattern (duplicated across components)** — components_lineubbyday_computeheadlinerids, components_lineupanalysis_computeheadlinerids, components_festivalpagetabs_computeheadlinerids [EXTRACTED 0.95]
- **Festival Theme Derivation Pipeline** — lib_festival_theme_getfestivaltheme, lib_festival_theme_themetocssvar, components_festivalthemestyle_festivalthemestyle [EXTRACTED 1.00]
- **Festival Data Pipeline: Scraper → Enrichers → DB Tables** — pipeline_festival_scraper_upsert_festivals, pipeline_festival_dates_enricher_enrich_festival_dates, pipeline_festival_art_generator_generate_festival_svg, schema_sql_festivals_table [INFERRED 0.90]
- **Lineup Write Orchestration: Scraper + Seeder + Manager → lineups table** — pipeline_lineup_scraper_write_lineup, pipeline_lolla_schedule_seeder_upsert_lineup_entry, pipeline_schedule_scraper_write_schedule, schema_sql_lineups_table [INFERRED 0.90]
- **Frontend Data Access Layer: supabase client + queries + types** — lib_supabase_getsupabase, lib_queries_getfestivalpagedata, lib_types_festival, lib_types_lineupentry [INFERRED 0.85]
- **ETL Pipeline: Data Sources → Python Scripts → Supabase Storage** — svg_data_sources_layer, svg_etl_pipeline_layer, svg_storage_layer, etl_daily_yml_workflow [EXTRACTED 0.95]
- **Frontend Data Consumption: Supabase API → Next.js Pages → UI Components** — api_ref_supabase_api, svg_frontend_layer, ui_spec_festival_page_template, ui_spec_artist_page_template, handoff_md_resilient_data_layer [INFERRED 0.85]
- **AI Fun Facts Pipeline: Claude API → fun_facts_generator → FunFactsWidget** — api_ref_anthropic_claude_api, etl_daily_yml_generate_fun_facts_job, ui_spec_fun_facts_widget [INFERRED 0.90]

## Communities (28 total, 4 thin omitted)

### Community 0 - "Festival Pages & App Routing"
Cohesion: 0.06
Nodes (62): metadata, PHASES, SOURCES, HomePage(), FeaturedFestivals(), Props, Props, Props (+54 more)

### Community 1 - "Festival Page Tabs & Lineup Display"
Cohesion: 0.06
Nodes (37): computeHeadlinerIds(), FestivalPageTabs(), LineupListView(), ListRow(), Props, Tab, ViewMode, computeHeadlinerIds (LineupByDay) (+29 more)

### Community 2 - "Festival Art Generation Pipeline"
Cohesion: 0.13
Nodes (39): Client, Path, _apply_season(), _build_palette(), _choose_motif(), _circle(), _ellipse(), generate_festival_svg() (+31 more)

### Community 3 - "AI Fun Facts & Schedule Seeding"
Cohesion: 0.09
Nodes (32): Client, Client, build_prompt(), CLAUDE_MODEL constant, generate_fun_facts(), get_lineup_context(), get_supabase(), main() (+24 more)

### Community 4 - "Artist Profile Components"
Cohesion: 0.12
Nodes (31): ArtistDiscography(), Props, ArtistHero(), FestivalAppearances(), FestivalCard(), Festival Accent Color Theming, Idempotent Seed / Upsert Pattern, RLS Public Read / Service Write Pattern (+23 more)

### Community 5 - "Festival Theming & Artist Hero"
Cohesion: 0.14
Nodes (20): Props, FestivalThemeStyle(), Props, MusicPlayerToggle(), Props, LinkBtn(), Props, StreamingWidget() (+12 more)

### Community 6 - "Artist Enrichment (Spotify/Deezer)"
Cohesion: 0.16
Nodes (24): Client, clean_orphans(), Deezer Fallback Strategy, _deezer_search(), enrich_artists(), enrich_from_deezer(), enrich_from_spotify(), fetch_deezer_image() (+16 more)

### Community 7 - "Festival Grid & Empty States"
Cohesion: 0.10
Nodes (17): EmptyState(), Props, CATEGORY_LABELS, CategoryDropdown(), DropdownProps, FestivalGrid(), Filters, formatTag() (+9 more)

### Community 8 - "Frontend Dependencies & Config"
Cohesion: 0.08
Nodes (23): dependencies, framer-motion, next, react, react-dom, @supabase/supabase-js, devDependencies, autoprefixer (+15 more)

### Community 9 - "Festival Discovery Scraper"
Cohesion: 0.18
Nodes (19): BeautifulSoup, Client, _apply_dates(), fetch_wikipedia(), get_supabase(), main(), parse_festivals(), PRIORITY_FESTIVALS (+11 more)

### Community 10 - "TypeScript Configuration"
Cohesion: 0.10
Nodes (19): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+11 more)

### Community 11 - "Festival Dates Enrichment"
Cohesion: 0.18
Nodes (18): date, Client, enrich_festival_dates(), estimate_dates(), FESTIVAL_PATTERNS, fetch_tm_dates(), fetch_wiki_dates(), get_supabase() (+10 more)

### Community 12 - "Schedule Scraping (TM/Songkick/Vision)"
Cohesion: 0.20
Nodes (17): Anthropic, Client, fetch_songkick_schedule(), fetch_tm_schedule(), find_schedule_image(), get_anthropic(), get_supabase(), main() (+9 more)

### Community 13 - "Lineup Scraping (TM/Setlist.fm)"
Cohesion: 0.20
Nodes (16): Client, FESTIVAL_CONFIG, fetch_setlistfm_lineup(), fetch_tm_lineup(), get_supabase(), _is_main_festival_event(), main(), process_festival() (+8 more)

### Community 14 - "Root Layout & Error Pages"
Cohesion: 0.15
Nodes (11): metadata, RootLayout(), NotFound(), CustomCursor(), DraggableNotes(), Note, NOTES, HeroSection() (+3 more)

### Community 15 - "External API Reference Docs"
Cohesion: 0.21
Nodes (15): Anthropic Claude API Integration (fun facts), Instagram Basic Display API Integration, Spotify Web API Integration, Twitter Low-Cost Strategy (oEmbed / nitter proxy), X (Twitter) API v2 Integration, Unsplash API Integration, Unsplash Attribution Requirement, API Reference Document (+7 more)

### Community 16 - "Apple Music & UI Spec"
Cohesion: 0.18
Nodes (11): Apple Music API (MusicKit JS) Integration, Apple Music JWT Token Generation (ES256), Framer Motion Animation Spec, Artist Page Template (/artist/[slug]), UI Specification Document, Festival Index Page Template (/), Festival Page Template (/festival/[slug]), FunFactsWidget Component Spec (+3 more)

### Community 17 - "Lineup Manager Pipeline"
Cohesion: 0.47
Nodes (10): Client, clear_lineup(), delete_orphans(), get_supabase(), list_lineup(), list_orphans(), main(), lineup_manager.py ----------------- CLI tool for viewing and cleaning up lineup (+2 more)

### Community 18 - "System Architecture Diagram"
Cohesion: 0.27
Nodes (11): API Layer (Supabase auto-API, FastAPI optional, OAuth proxy), Apple Music API Data Source, Festival Analyzer System Architecture Diagram, Data Sources Layer (Wikipedia, Spotify, Apple Music, Unsplash/Social), ETL Pipeline Layer (Python + GitHub Actions cron), Frontend Layer (Next.js 14 on Vercel), Hosting and CI/CD Layer (Vercel + GitHub Actions + Supabase), Spotify API Data Source (+3 more)

### Community 19 - "Media Fetcher (Unsplash)"
Cohesion: 0.38
Nodes (9): Client, fetch_for_festival(), fetch_unsplash_photos(), get_supabase(), main(), photo_to_record(), media_fetcher.py ---------------- Fetches festival photography from the Unsplash, Set festivals.hero_image_url to a city image — but only if one isn't     already (+1 more)

### Community 20 - "Supabase API & Handoff Docs"
Cohesion: 0.22
Nodes (9): Supabase API and SDK Integration, Supabase Edge Functions (optional OAuth token proxy), Frontend Build Design Decisions Table, force-dynamic Pages Strategy (keys available later), Frontend Handoff Document, Resilient Data Layer Pattern (empty-safe queries), Runtime Festival Theming System, Festival Color System (accent_color runtime palette) (+1 more)

### Community 21 - "Project Conventions & Roadmap"
Cohesion: 0.33
Nodes (6): Festival Analyzer Project, Idempotent Upsert Pipeline Pattern, Next.js App Router Convention, Festival Analyzer Phase Roadmap, Supabase RLS Security Pattern, Tenacity Retry Pattern for External APIs

### Community 22 - "Project README & Design Notes"
Cohesion: 0.33
Nodes (6): Festival Analyzer (Root README), Pipeline Schedule Table, Free Tier Scalability Strategy, Festival Analyzer Tech Stack, UI Design Reference (Awwwards), UI Design Philosophy (editorial, destination-feel)

## Knowledge Gaps
- **87 isolated node(s):** `metadata`, `SOURCES`, `PHASES`, `PageProps`, `PageProps` (+82 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `festivals table` connect `AI Fun Facts & Schedule Seeding` to `Festival Pages & App Routing`, `Festival Discovery Scraper`, `Festival Art Generation Pipeline`, `Festival Dates Enrichment`?**
  _High betweenness centrality (0.219) - this node is a cross-community bridge._
- **Why does `Festival` connect `Festival Pages & App Routing` to `Festival Page Tabs & Lineup Display`, `AI Fun Facts & Schedule Seeding`, `Festival Grid & Empty States`?**
  _High betweenness centrality (0.159) - this node is a cross-community bridge._
- **Why does `lineups table` connect `AI Fun Facts & Schedule Seeding` to `Festival Pages & App Routing`, `Schedule Scraping (TM/Songkick/Vision)`, `Lineup Scraping (TM/Setlist.fm)`?**
  _High betweenness centrality (0.118) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `Festival` (e.g. with `tailwind.config.ts` and `festivals table`) actually correct?**
  _`Festival` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `metadata`, `SOURCES`, `PHASES` to the rest of the system?**
  _148 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Festival Pages & App Routing` be split into smaller, more focused modules?**
  _Cohesion score 0.06110154905335628 - nodes in this community are weakly interconnected._
- **Should `Festival Page Tabs & Lineup Display` be split into smaller, more focused modules?**
  _Cohesion score 0.06015037593984962 - nodes in this community are weakly interconnected._