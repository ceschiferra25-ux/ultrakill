# ULTRAKILL Guide

A web guide to the enemies and bosses of **ULTRAKILL**, the fast-paced retro shooter by Arsi "Hakita" Patala / New Blood Interactive.
For every enemy the guide shows its lore, attack patterns, weaknesses and strategies to beat it. Players can share their own tips, and an admin keeps the database up to date.

Built with **HTML, CSS, JavaScript, SQLite and Flask**: the technologies of the course.

## Goals

- Collect in one place, in a consistent format, what a player needs to know about each of the 41 entries (enemies, bosses, secret encounters).
- Let players browse by faction, type or secrets, and search by name or lore, without reloading the page.
- Build a small community: anyone can post a tip on an entry; an admin can moderate tips and add, edit or delete entries.
- Apply the course topics end to end: static and dynamic pages, a web server handling GET, POST, PUT and DELETE requests, a relational database, and client-side scripting with `fetch`.

## Features

| Area | What it does |
|---|---|
| Pages | Home with live statistics, all enemies, factions, bosses, secret encounters, entry detail, admin login, add/edit entry, themed 404/500 pages |
| Filters | Faction, type and text search. Works as a normal GET form; with JavaScript it updates live through the API and keeps the URL shareable |
| Tips | Posted without reloading (`POST /api/...`), validated on client and server, kept in the form if invalid |
| Admin | Login with hashed password; add, edit, delete entries (with optional picture upload); delete tips |
| Security | CSRF tokens on every state-changing request, parameterised SQL, auto-escaped templates, `textContent` in JS, security headers (CSP, X-Frame-Options), upload type/size checks, safe redirects, debug off by default |
| Accessibility | Skip link, labelled fields with inline errors, visible keyboard focus, current page marked in the menu, `aria-live` messages, in-page confirm dialog, reduced-motion support |
| Responsive | Fluid grids; collapsible menu below 760px; forms and filters stack on phones |

## Run it

Requires Python 3.10 or newer.

```bash
# 1. create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. install the dependencies
pip install -r requirements.txt

# 3. start the server (creates database.db with the starting data on first run)
python app.py
```

Open <http://127.0.0.1:5000>.

**Admin login:** username `admin`, password `ultrakill-admin`.
To use different credentials, set them before creating the database:

```bash
export ADMIN_USERNAME=myname ADMIN_PASSWORD='a long password'   # Windows PowerShell: $env:ADMIN_PASSWORD="..."
python init_db.py                                               # rebuilds the database from scratch
```

Optional environment variables: `SECRET_KEY` (signs the session cookie; without it a random key is generated at every start, so admins are logged out on restart), `DATABASE` (path of the SQLite file), `FLASK_DEBUG=1` (development debugger, never in production).

## Tests

```bash
python -m pytest
```

46 tests in `tests/` cover every page, the filters, form validation and escaping, login and permissions, image upload checks, every API method, CSRF protection and error pages. Each test runs on its own temporary database.

## Project structure

```
app.py            application factory, HTML pages, error pages, security headers
api.py            JSON API (GET / POST / PUT / DELETE)
auth.py           admin login/logout, admin_required decorator, CSRF protection
models.py         all SQL queries and validation, shared by pages and API
db.py             SQLite connection per request, schema creation, seeding
schema.sql        tables: entries, comments, admins
seed_data.py      the 41 starting entries (checked against ultrakill.wiki.gg)
init_db.py        rebuilds the database: python init_db.py
templates/        Jinja templates (base layout + one per page, _entry_card partial)
static/css/       style.css, organised in numbered sections
static/js/        main.js: menu, live filters, tips, deletes, toasts, dialog
static/images/    V1 diagram, faction icons (SVG), enemies/ for pictures
tests/            pytest suite
```

## API

| Method | URL | Access | Purpose |
|---|---|---|---|
| GET | `/api/entries?faction=&category=&search=&secret=1` | everyone | list and filter entries |
| GET | `/api/entries/<id>` | everyone | one entry |
| PUT | `/api/entries/<id>` | admin | replace an entry (JSON body, same fields as the form) |
| DELETE | `/api/entries/<id>` | admin | delete an entry and its tips |
| GET | `/api/entries/<id>/comments` | everyone | list tips |
| POST | `/api/entries/<id>/comments` | everyone | add a tip `{author, message}` |
| DELETE | `/api/comments/<id>` | admin | delete a tip |

`POST`, `PUT` and `DELETE` need the `X-CSRF-Token` header (the page exposes it in `<meta name="csrf-token">`). Errors come back as JSON `{"error": ..., "fields": {...}}` with status 400, 401, 404 or 422.

## Database

- `entries`: name (unique), category (`enemy`/`boss`), faction (one of six), Cyber Grind and secret flags, lore, attack patterns, weaknesses, strategies, optional picture, timestamps.
- `comments`: tips linked to an entry; deleted with it (`ON DELETE CASCADE`).
- `admins`: username and password hash (never the plain password).

## Pictures

Cards show `static/images/enemies/<slug>.<ext>` when the file exists and fall back to the faction icon otherwise.
`static/images/enemies/README.md` lists, for every entry, the file name to use and the matching file on the official wiki. Admins can also upload a picture from the entry form (max 2 MB, images only).

## Team and contributions

| Member | Role | Main contributions |
|---|---|---|
| Member 1 | Back end and data | Flask application structure, SQLite schema and seed data, models and validation, admin authentication, CSRF protection, JSON API |
| Member 2 | Interface and content | Page templates, CSS theme, responsive layout, accessibility, faction icons, checking and translating entry content against the wiki |
| Member 3 | Front-end logic, quality and docs | JavaScript (`fetch` filters, tips, deletes, dialog, toasts), pytest suite, README and code documentation |

All three members reviewed each other's code and can explain every part of the project.

## Limitations and future work

- A single admin role: there are no user accounts for people posting tips, so nicknames are not verified.
- No pagination: fine for 41 entries, needed if the database grows a lot.
- Pictures must be added by hand (see above); they are not shipped with the project for copyright reasons.
- The wiki lists a few enemies added in recent updates (e.g. Mirror Reaper, Geryon, Deathcatcher, Providence, Power) that are not in the database yet; an admin can add them from the site.
- For a public deployment: run behind a production WSGI server (e.g. gunicorn), set `SECRET_KEY` and the admin credentials, and add rate limiting on login.

## Credits

ULTRAKILL and its characters © Arsi "Hakita" Patala / New Blood Interactive. Enemy data checked against the official ULTRAKILL wiki (<https://ultrakill.wiki.gg>). Fan-made, non-commercial university project.
