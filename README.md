# VPS Market

This Django project crawls VPS/cloud offers, normalizes them into one schema, stores them in PostgreSQL, and exposes simple unauthenticated APIs for listing and filtering offers. It currently supports:

- IranServer cloud plans, international VPS pages, and GPU VPS page
- ArvanCloud VPS pricing page

## Run with Docker

```powershell
docker compose up --build
```

Services:

- `db`: PostgreSQL
- `migrate`: runs Django migrations
- `web`: API on `http://localhost:8000`
- `crawler`: periodic crawl worker using the Django ORM

## Run one crawl

```powershell
docker compose run --rm crawler python manage.py crawl_offers
```

Run only one provider:

```powershell
docker compose run --rm crawler python manage.py crawl_offers --provider arvancloud
```

## Local development

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
copy .env.example .env
python manage.py migrate
python manage.py crawl_offers
python manage.py runserver
```

## API

- `GET /api/providers/`
- `GET /api/offers/`
- `GET /api/offers/{id}/`

Useful offer filters:

- `provider=iranserver`
- `region=iran`
- `country=Iran`
- `has_gpu=true`
- `available=true`
- `billing_period=monthly`
- `min_price_irr=1000000`
- `max_price_irr=50000000`
- `min_cpu_cores=4`
- `min_ram_mb=8192`
- `min_disk_gb=80`
- `search=RTX`
- `ordering=price_amount_irr`
- `ordering=-cpu_cores,price_amount_irr`

## Tables

- `providers`: provider registry
- `server_offers`: normalized VPS/container/GPU offers, with raw source payload in `raw_payload`
- `crawl_runs`: status and summary of each crawl run

The primary expansion point is `vps_market/providers`. Add a new provider class that returns normalized `Offer` instances, then register it in `vps_market/providers/__init__.py`. Persistence stays in `vps_market/services.py` and uses Django models only.
