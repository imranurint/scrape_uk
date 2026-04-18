# UK University Course Scraper

A production-grade system to scrape, store, and serve UK university course data.
Supports 50+ universities through modular, per-university Scrapy spiders.

---

## Architecture Overview

```
Universities (50+)
      │
      ▼
┌─────────────────────────────────────────────┐
│       Scrapy Scheduler + AutoThrottle       │
│  ┌───────────────┐    ┌────────────────┐    │
│  │ Static Spider │    │ Dynamic Spider │    │
│  │  (BS4 only)  │    │ (Playwright+BS4│    │
│  └───────┬───────┘    └───────┬────────┘    │
└──────────┼────────────────────┼─────────────┘
           │   yields item dict │
           ▼                    ▼
┌────────────────────────────────────────────┐
│            Pipeline Chain                 │
│  1. ValidationPipeline   (drop bad items) │
│  2. NormalisationPipeline (AI fallback)   │
│  3. DuplicatesPipeline   (URL dedup)      │
│  4. DatabasePipeline     (upsert PG)      │
└──────────────────┬─────────────────────────┘
                   │
                   ▼
        PostgreSQL (asyncpg)
        ┌─────────────┐
        │ universities│
        │ courses     │ ← GIN full-text index (tsvector)
        │course_detail│
        └──────┬──────┘
               │
               ▼
     FastAPI  :8000
     GET /courses/search
     GET /courses/{id}
     GET /universities
```

---

## Project Structure

```
uk_uni_scraper/
├── config/
│   ├── settings.py          # All Scrapy settings (env-driven)
│   └── database.py          # Async SQLAlchemy engine + session
│
├── scrapers/
│   ├── base_spider.py       # Abstract base: Playwright opt-in, BS4, logging
│   ├── middlewares.py       # Rotating proxy, structured logging, retry backoff
│   └── universities/
│       ├── ucl_spider.py        # UCL (static HTML)
│       └── manchester_spider.py # Manchester (React/JS)
│
├── core/
│   ├── extractor.py         # BeautifulSoup field extractor (multi-selector)
│   ├── ai_extractor.py      # Crawl4AI fallback (markdown + optional LLM)
│   └── normalizer.py        # Raw dict → CourseSchema normalisation
│
├── pipelines/
│   ├── validation.py        # Drop missing-name / bad-URL items
│   ├── normalisation.py     # Trigger AI extractor when BS4 is insufficient
│   ├── duplicates.py        # Per-run URL dedup (O(1))
│   └── database.py          # Batched upsert (25 items/batch)
│
├── models/
│   ├── db.py                # SQLAlchemy ORM (University, Course, CourseDetail)
│   └── schemas.py           # Pydantic v2 (CourseSchema matches output brief)
│
├── api/
│   ├── main.py              # FastAPI app, CORS, health probes, lifespan
│   └── routes/
│       ├── courses.py       # /courses/search, /courses/{id}
│       └── universities.py  # /universities, /universities/{id}
│
├── alembic/                 # DB migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 001_initial.py   # Creates tables + GIN index + search_vector trigger
│
├── tests/
│   ├── test_extractor.py    # BS4 extractor unit tests (HTML fixtures)
│   ├── test_normalizer.py   # Normalizer unit tests
│   └── test_api.py          # FastAPI integration tests (in-memory SQLite)
│
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── scrapy.cfg
├── requirements.txt
└── .env.example
```

---

## Quick Start

### 1. Clone and Configure

```bash
git clone https://github.com/your-org/uk-uni-scraper
cd uk-uni-scraper
cp .env.example .env
# Edit .env with your PostgreSQL credentials
```

### 2. Start with Docker Compose

```bash
# Start PostgreSQL + FastAPI
docker compose up -d postgres api

# Wait for postgres to be healthy, then run migrations
docker compose exec api alembic upgrade head

# Run scrapers (add more spider names as needed)
docker compose --profile scrape up scraper
```

### 3. Run Locally (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# Set env vars
export DATABASE_URL="postgresql+asyncpg://scraper:pass@localhost:5432/uni_scraper"

# Apply migrations
alembic upgrade head

# Run a spider
scrapy crawl ucl -L INFO

# Start the API
uvicorn api.main:app --reload --port 8000
```

---

## API Reference

### Search Courses
```
GET /courses/search
```

| Param        | Type   | Description                            |
|-------------|--------|----------------------------------------|
| `q`          | string | Keyword search (name + department)     |
| `university` | string | Filter by university name (partial)    |
| `degree`     | string | Filter by degree type (BSc, MSc, …)   |
| `level`      | string | undergraduate / postgraduate / research|
| `min_fee`    | int    | Min UK yearly fee (GBP)               |
| `max_fee`    | int    | Max UK yearly fee (GBP)               |
| `page`       | int    | Page number (default: 1)               |
| `page_size`  | int    | Per-page results (max: 100)            |

**Example:**
```bash
curl "http://localhost:8000/courses/search?q=computer+science&university=UCL&degree=BSc"
```

### Get Course Detail
```
GET /courses/{id}
```
Returns the full `CourseSchema` JSON:
```json
{
  "university": { "name": "UCL", "location": "London, England" },
  "course": {
    "name": "BSc Computer Science",
    "degree": "BSc",
    "level": "undergraduate",
    "department": "Department of Computer Science",
    "study_mode": ["full-time"],
    "duration_years": 3.0,
    "start_month": "September"
  },
  "fees": {
    "uk":            { "yearly": 9250,  "sandwich_year": null, "currency": "GBP" },
    "international": { "yearly": 35000, "sandwich_year": null, "currency": "GBP" }
  },
  "admission": {
    "ucas_code": "G400",
    "application_deadline": { "main": "15 January 2026", "late": null },
    "entry_requirements": "AAA at A-level including Mathematics.",
    "english_requirement": { "ielts": 6.5 }
  },
  "metadata": {
    "url": "https://www.ucl.ac.uk/prospective-students/.../computer-science",
    "scraped_at": "2025-09-01T10:00:00+00:00"
  }
}
```

### List Universities
```
GET /universities
GET /universities/{id}
```

---

## Adding a New University Spider

1. Create `scrapers/universities/<slug>_spider.py`
2. Inherit from `BaseUniversitySpider`
3. Set `name`, `university_name`, `university_location`
4. Set `needs_js = True` if the site uses JS rendering
5. Override `parse_course_list()` and `parse_course()`

**Minimal example:**
```python
from scrapers.base_spider import BaseUniversitySpider

class EdinburghSpider(BaseUniversitySpider):
    name = "edinburgh"
    university_name = "University of Edinburgh"
    university_location = "Edinburgh, Scotland"
    needs_js = False

    start_urls = ["https://www.ed.ac.uk/studying/undergraduate/degrees"]
    course_link_selector = "a.course-link"
    next_page_selector = "a.pagination-next"

    def parse_course_list(self, response):
        for href in response.css(f"{self.course_link_selector}::attr(href)").getall():
            yield self._make_request(response.urljoin(href), callback=self.parse_course)
        yield from self._follow_pagination(response, callback=self.parse_course_list)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
```

That's it. All extraction, normalisation, dedup, and DB persistence are handled by the base class and pipeline chain.

---

## Production Checklist

| Feature | Implementation |
|---|---|
| Rate limiting | AutoThrottle + per-domain concurrent request limit |
| Retry with backoff | `ExponentialBackoffRetryMiddleware` (2, 4, 8, 16s) |
| Proxy rotation | `RotatingProxyMiddleware` (set `PROXY_LIST` in `.env`) |
| Structured logging | `structlog` JSON logs on every request/response |
| Deduplication | URL-based in-memory (per run) + PostgreSQL upsert (cross-run) |
| Full-text search | PostgreSQL GIN index on `tsvector` (name + dept + degree) |
| Schema validation | Pydantic v2 on every item before DB write |
| AI extraction | Crawl4AI fallback (off by default, toggle `USE_AI_EXTRACTOR=true`) |
| Migrations | Alembic versioned migrations |
| Container-ready | Dockerfile + docker-compose with health checks |

---

## Running Tests

```bash
pip install pytest pytest-asyncio aiosqlite httpx
pytest tests/ -v
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | ✅ | — | PostgreSQL async URL |
| `PROXY_LIST` | ❌ | empty | Comma-separated proxy URLs |
| `USE_AI_EXTRACTOR` | ❌ | `false` | Enable Crawl4AI fallback |
| `OPENAI_API_KEY` | ❌ | — | Needed only if using LLM mode |
| `SCRAPY_CONCURRENT_REQUESTS` | ❌ | `16` | Global concurrency |
| `SCRAPY_DOWNLOAD_DELAY` | ❌ | `1.5` | Base delay between requests (s) |
| `SCRAPY_LOG_LEVEL` | ❌ | `INFO` | Scrapy log verbosity |
