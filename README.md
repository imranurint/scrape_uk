# Scrape Project

A Scrapy-based web scraping project for extracting course and university data from various UK institutions.

## Installation

```bash
# Create a virtual environment
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install
```

## Database Setup

Apply database migrations using Alembic:

```bash
alembic upgrade head
```

## Running Scrapers

To run all crawlers:

```bash
scrapy crawl uk_universities
```

To run a specific university spider:

```bash
scrapy crawl <spider_name>
```

## Database Tools

To view database statistics:

```bash
python db_script/data_summary.py
```

To export database data to JSON files in the `data/` directory:

```bash
python db_script/export.py
```

## Project Structure

- `api/`: FastAPI based API for accessing scraped data.
- `scrapers/`: Scrapy spiders and middlewares.
- `models/`: Database models and schemas.
- `db_script/`: Utility scripts for database operations.
- `data/`: Exported JSON data files.
