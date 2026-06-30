\# Shipping a Data Product: From Raw Telegram Data to an Analytical API



\*A Week 8 case study: building an end-to-end ELT pipeline for Ethiopian medical Telegram channels using Telethon, dbt, YOLOv8, FastAPI, and Dagster.\*



\## Overview



Kara Solutions needed a way to turn unstructured Telegram chatter from Ethiopian medical and pharmaceutical channels into something a business analyst could actually query — top products, channel activity trends, and visual content patterns. This post walks through how I built that pipeline end to end: scraping raw data into a lake, modeling it into a star schema with dbt, enriching it with YOLOv8 object detection, and exposing it through a FastAPI analytical layer, all orchestrated with Dagster.



\## Architecture



The pipeline follows a layered ELT pattern:

Telegram Channels (Telethon)

↓

Raw Data Lake (JSON + images, partitioned by date)

↓

PostgreSQL raw schema (loaded via Python/psycopg2)

↓

dbt staging models (cleaned, typed, deduplicated)

↓

dbt mart models — star schema (dim\_channels, dim\_dates, fct\_messages, fct\_image\_detections)

↓

FastAPI analytical endpoints

↓

Dagster orchestration (scrape → load → transform → enrich, scheduled daily)



\*(Insert your own architecture diagram here — you can sketch this flow in draw.io, Excalidraw, or similar, or describe it as above.)\*



\## Task 1: Scraping and the Data Lake



Using Telethon, I connected to three Ethiopian medical Telegram channels — CheMed123 (general medical products), lobelia4cosmetics (cosmetics and health products), and tikvahpharma1 (pharmaceuticals) — and pulled the most recent messages from each, downloading any attached images along the way.



Raw messages are stored as JSON, partitioned by scrape date and channel name (`data/raw/telegram\_messages/YYYY-MM-DD/channel\_name.json`), preserving the original Telegram API structure. Images are stored separately under `data/raw/images/{channel\_name}/{message\_id}.jpg`. This separation keeps the lake faithful to the source data — nothing is transformed or filtered at this stage, which gives downstream stages full flexibility.



One early data-quality finding: channel sizes varied wildly. CheMed123 and lobelia4cosmetics each had hundreds of recent messages, while tikvahpharma1 only had a handful — a reminder that real-world data sources are rarely uniform, and pipelines need to handle sparse sources gracefully rather than assuming every source behaves the same.



\## Task 2: Star Schema and dbt



Raw JSON isn't analytics-ready, so the next step was building a proper dimensional model.



\*\*Staging layer\*\* (`stg\_telegram\_messages`): casts types, trims and filters empty messages, and adds calculated fields like `message\_length` and `has\_image`.



\*\*Marts layer\*\* — a classic star schema:

\- `dim\_channels`: one row per channel, with aggregated stats (total posts, average views, first/last post date) and a derived `channel\_type` (Medical / Cosmetics / Pharmaceutical)

\- `dim\_dates`: a generated date spine covering the full range of message dates, with day-of-week, week-of-year, quarter, and weekend flags

\- `fct\_messages`: one row per message, with foreign keys to both dimensions



I chose a star schema (over a snowflake schema) because the analytical questions we needed to answer — top products, posting trends, channel comparisons — are best served by simple, fast joins rather than deeply normalized dimension hierarchies. With this data volume, query performance wasn't the constraint; query simplicity for downstream consumers (the API, future BI tools) was.



\*\*Testing\*\*: 15 dbt tests across uniqueness, not-null, and referential integrity constraints, plus two custom data tests — one asserting no message has a future date, another asserting view/forward counts are never negative. All 15 pass.



\*(Insert your dbt docs lineage graph screenshot here)\*



\## Task 3: Enrichment with YOLOv8



Pre-trained object detection models like YOLOv8 don't know what "paracetamol" or "Lobelia face cream" look like — they're trained on general-purpose COCO classes (person, bottle, cup, etc.). Rather than treating this as a limitation, I used it as a heuristic: a `bottle` or `book`-shaped object without a person nearby is probably a product shot; a `person` detected alongside a `bottle` is probably promotional content; a `person` alone is more likely lifestyle content.



This produced a simple but useful four-way classification — `promotional`, `product\_display`, `lifestyle`, `other` — applied across all 268 downloaded images, yielding 524 individual object detections (some images contain multiple objects). Results were loaded into Postgres and joined against the fact tables to produce `fct\_image\_detections`, linking every detection back to its channel and date.



\*\*Limitations worth noting\*\*: COCO's 80 classes are a blunt instrument for domain-specific classification. A box of pills, a tube of cream, and a vial would all likely go undetected or get misclassified as generic objects (or nothing at all) since none of those are COCO classes. A fine-tuned model trained on labeled pharmaceutical product images would meaningfully outperform this heuristic — a clear "potential improvement" for a v2 of this pipeline.



\*(Insert a sample detection result or two here, e.g. screenshot or describe: "X% of lobelia4cosmetics images were product\_display vs Y% promotional")\*



\## Task 4: The Analytical API



With the warehouse built, I exposed it through FastAPI with four endpoints:



\- `GET /api/reports/top-products` — word-frequency analysis across all message text, surfacing the most commonly mentioned terms

\- `GET /api/channels/{channel\_name}/activity` — posting stats for a single channel

\- `GET /api/search/messages?query=...` — keyword search across all messages

\- `GET /api/reports/visual-content` — per-channel breakdown of image categories from the YOLO enrichment



All requests and responses are validated through Pydantic schemas, and FastAPI's automatic OpenAPI documentation made manual testing straightforward via the `/docs` Swagger UI.



\*(Insert your Swagger UI screenshots here — overview page, and 2-3 working endpoint responses)\*



\## Task 5: Orchestration with Dagster



The final piece ties everything together into a single, observable, schedulable pipeline. Using Dagster, I defined four ops — `scrape\_telegram\_data`, `load\_raw\_to\_postgres`, `run\_dbt\_transformations`, `run\_yolo\_enrichment` — chained sequentially into a single job, with a daily 6:00 AM UTC schedule.



Dagster's local UI made it easy to visually confirm the dependency graph was correct before running anything, and the real-time event log during execution made debugging straightforward when something failed partway through.



\*(Insert your Dagster job graph screenshot and a successful/in-progress run screenshot here)\*



\## Data Quality Issues Encountered



\- \*\*Uneven channel volume\*\*: as noted, tikvahpharma1 had drastically fewer messages than the other two channels — handled by writing the scraper to gracefully process however many messages exist rather than assuming a fixed count.

\- \*\*Empty/null message text\*\*: many Telegram messages are media-only with no caption — filtered out in the staging layer rather than the raw layer, preserving the original data while keeping downstream marts clean.

\- \*\*Channel username mismatches\*\*: public-facing channel names don't always match their actual `@username` handles (e.g. "Tikvah Pharma" is `@tikvahpharma1`, not `@tikvahpharma`) — required manual verification via Telegram search before scraping could begin.

\- \*\*Telegram session/2FA quirks\*\*: working with a personal Telegram account meant handling two-step verification during the Telethon login flow, which isn't always obvious from the library's prompts alone.



\## Reflection



\*(Write 2-3 honest paragraphs here in your own words — what was hardest, what you'd do differently with more time, e.g.: incremental/idempotent loading instead of full reloads on each scrape, a fine-tuned object detection model instead of relying on COCO classes, more robust error handling in the scraper for rate limits, deduplication logic for re-scraped messages, etc. This section matters most for the "reflection on challenges, key learnings, and potential improvements" grading criterion — make it specific to what you actually experienced, not generic.)\*



\## Tech Stack



Python, Telethon, PostgreSQL, dbt-postgres, Ultralytics YOLOv8, FastAPI, SQLAlchemy, Pydantic, Dagster.



\---



\*Repository: \[medical-telegram-warehouse](https://github.com/mycodebook123/medical-telegram-warehouse)\*

