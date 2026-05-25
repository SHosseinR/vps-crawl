# VPS Market

This Django project crawls VPS/cloud offers, normalizes them into one schema, stores them in PostgreSQL, and exposes simple unauthenticated APIs for listing and filtering offers. It currently supports:

- IranServer cloud plans, international VPS pages, and GPU VPS page
- ArvanCloud VPS pricing page

## Structure

```text
vps_market/
  manage.py
  vps_market/      # Django project settings, URLs, ASGI/WSGI
  offers/          # Django app: models, API, admin, management commands
  crawlers/        # Provider crawl/parsing code, outside the Django app
```

## Run with Docker

```powershell
docker compose up --build
```

Services:

- `db`: PostgreSQL
- `migrate`: runs Django migrations
- `web`: API on `http://localhost:8000`
- `frontend`: React UI on `http://localhost:5173`
- `nginx`: production-style single origin on `http://localhost`
- `crawler`: periodic crawl worker using the Django ORM

Static files are served by WhiteNoise. The web container runs `collectstatic` on startup so Django admin and Swagger assets work even when `./vps_market` is bind-mounted into the container.

The React app uses relative `/api/...` requests, so it talks to the same browser origin. In Docker, nginx serves the built React app and proxies `/api/` to Django. It also proxies `/admin/` and `/static/` so admin remains usable from the same host.

## Run one crawl

```powershell
docker compose run --rm crawler python vps_market/manage.py crawl_offers
```

Run only one provider:

```powershell
docker compose run --rm crawler python vps_market/manage.py crawl_offers --provider arvancloud
```

## Local development

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
copy .env.example .env
python vps_market/manage.py migrate
python vps_market/manage.py crawl_offers
python vps_market/manage.py runserver
```

Run the React frontend locally:

```powershell
cd frontend
npm install
npm run dev
```

## API

- `GET /api/docs/`
- `GET /api/schema/`
- `GET /api/providers/`
- `GET /api/offers/`
- `GET /api/offers/{id}/`
- `GET /api/statistics/`

Useful offer filters:

- `provider=iranserver`
- `region=iran`
- `region_detail=ir-thr-ba1`
- `country=Iran`
- `has_gpu=true`
- `gpu_model=L40S`
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
- `gpu_specs`: GPU-specific fields linked one-to-one to GPU offers
- `crawl_runs`: status and summary of each crawl run

The primary expansion point is `vps_market/crawlers/providers`. Add a new provider class that returns normalized `Offer` instances, then register it in `vps_market/crawlers/providers/__init__.py`. Persistence stays in `vps_market/offers/services.py` and uses Django models only.

Provider cookies can be set through `.env`:

```text
ARVANCLOUD_COOKIE=...
IRANSERVER_COOKIE=...
```
