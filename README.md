## DINGDONG — Watch Store (Django)

This repository is a focused e‑commerce application that sells watches by brand and variant. It is implemented with Django using server-rendered templates and minimal JavaScript enhancements. The main goal is to provide a reliable product catalog (brands, variants, colors), a smooth product detail experience (zoom + thumbnails), robust cart & stock handling, and a simple checkout flow.

Why this project exists
----------------------
- Purpose: a production-like demo of an online watch store where customers browse brands, select product variants (color / size / model), and purchase items.
- Audience: developers building or extending e-commerce features, or stakeholders who want a quick proof-of-concept storefront for watch products.

What makes this project different (design decisions)
---------------------------------------------------
- Django server-rendered templates: keeps SEO, accessibility and initial page performance strong. Also simplifies deployment (no heavy frontend framework required).
- Tailwind-style utility classes in templates: fast UI iterations and consistent styling without a large CSS codebase.
- Progressive enhancement: JavaScript is used to improve UX (image zoom, AJAX variant switching), but core functionality works without JS.
- Data-driven templates: product/variant data, images and stock are rendered by Django. JavaScript reads safe `data-` attributes when necessary (avoids injecting raw template variables directly into scripts).
- Simplicity over complexity: the checkout flow is intentionally minimal so you can plug in payment providers later.

Core components (what each part does)
-----------------------------------
- `Server/` — Django project settings, URL routing, WSGI/ASGI entry points.
- `products/` — Product models, variants, images, and product pages (product detail, thumbnails, variant switching).
- `cart/` — Cart logic, cart templates (add/remove, quantity management), and UI showing stock status.
- `checkout/` — Checkout flow and order creation (starter implementation to extend with real payment gateways).
- `userlogin/` & `uProfile/` — Authentication and user profile pages.
- `admin_panel/` & `dashboard/` — Admin helpers and dashboards for internal staff.
- `media/` — Uploaded images (product photos, banners). Keep file storage in mind when deploying (S3/Cloud storage recommended for production).

Data model overview (high-level)
--------------------------------
- Product — the main item (e.g., "Model X Watch"). Contains brand, category and description.
- Variant — a product variant (color, size, SKU, price, stock). Each variant can have multiple images.
- Image — linked to a variant; templates show one default image and thumbnails for others.
- CartItem / Order — line items referencing a Variant and quantity; orders created during checkout.

Why the cart shows red (what that means)
--------------------------------------
Red UI (for example `bg-red-50` or `border-red-300`) is used intentionally to indicate a problem state for a cart item — typically when:

- The variant is out of stock (stock_available is false) or
- The variant has been marked unavailable (is_available is false)

This visual cue helps the customer identify items that cannot be purchased and encourages them to change the variant or remove the item.

How to build and run this project (developer steps)
--------------------------------------------------
These are concrete steps to get a working local copy.

1) Clone and enter the repository

	```bash
	git clone <your-repo-url>
	cd dingdong-ecommerce
	```

2) Create a virtual environment and activate it (zsh):

	```bash
	python3 -m venv .venv
	source .venv/bin/activate
	```

3) Install dependencies

	```bash
	pip install -r requirements.txt
	```

4) Create a `.env` or set env vars used by `Server/settings.py` (example for sqlite dev):

	```env
	SECRET_KEY=dev-secret
	DEBUG=True
	ALLOWED_HOSTS=localhost,127.0.0.1
	```

5) Run DB migrations and optionally collect static files

	```bash
	python manage.py migrate
	python manage.py collectstatic --noinput
	```

6) Create a superuser and optional demo data

	```bash
	python manage.py createsuperuser
	# Optional: load fixture if present
	# python manage.py loaddata fixtures/demo_products.json
	```

7) Run dev server

	```bash
	python manage.py runserver
	```

8) Visit `http://127.0.0.1:8000/` and browse products. The admin is typically at `/admin/`.

Notes on product images and media
---------------------------------
- Development: `media/` is used for uploaded images. Ensure `MEDIA_URL`/`MEDIA_ROOT` are configured in `Server/settings.py`.
- Production: Use S3 or another cloud storage provider to host images and configure Django's storage backend.

Extending the project (how to add features)
------------------------------------------
- Add payment gateway: implement a payment provider integration in `checkout/` and secure webhooks.
- Improve inventory workflows: add batch updates, back-in-stock notifications, and vendor integrations.
- Add search and filtering: integrate ElasticSearch or Postgres full-text search for product discovery.
- Add CI pipelines and tests: integrate GitHub Actions, add unit and integration tests for cart/checkout.

Troubleshooting tips (common problems and fixes)
-----------------------------------------------
- JS parse errors in templates: avoid putting raw Django variables inside inline JS. Instead, render values into `data-` attributes and read them on DOMContentLoaded.
- Unexpected red items in cart: check cart template conditionals around `item.stock_available` / `item.is_available` and confirm your product variant stock values in the DB.
- Missing images: ensure `MEDIA_ROOT` is readable and `MEDIA_URL` is set; verify that `variant.images` exists for the product in the admin.

Deployment checklist (short)
--------------------------
- Set `DEBUG=False` and configure `ALLOWED_HOSTS`.
- Use a production DB (Postgres), and configure connection credentials securely.
- Configure media storage (S3 recommended) and a strategy for static file serving (CDN).
- Run `python manage.py collectstatic` and serve static files from your CDN or Nginx.
- Use a process manager (systemd) or container orchestration and run Gunicorn/Uvicorn behind Nginx.

Contributor & support notes
---------------------------
- Add tests when changing behavior. Keep product/variant data backwards compatible when possible.
- Open an issue or PR with a clear description and steps to reproduce if something breaks.

License & attribution
---------------------
- Add a `LICENSE` file to the repo. Choose an OSI-approved license if you plan to open-source this project (MIT or Apache-2.0 are common choices).

If you'd like, I can now:
- Add a `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md`.
- Add a `docker-compose.yml` and `Dockerfile` for local reproducible development.
- Add sample fixtures (demo watches, brands, and variants) and a small script to import them.

Tell me which of these extras you'd like and I'll add them next.

