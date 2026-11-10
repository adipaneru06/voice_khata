# Voice Khata: Project Spec

This file is the source of truth for the project. Read it fully before writing any code, and follow it exactly. Do not add features that are not listed here.

## 1. What we are building

A voice invoicing and ledger (khata) app for micro-SMEs such as small shopkeepers in Tier 2 and Tier 3 towns in India.

A shopkeeper taps a mic and says something like: "Sharma ji ko 5 kilo chawal, 600 rupaye, udhaar". The app:

1. Records the audio and transcribes it with Gnani Prisma (speech to text).
2. Parses the transcript into a structured entry.
3. Shows the entry on a confirmation screen where the shopkeeper can edit it.
4. Saves it to a ledger and updates the customer's running balance.
5. Generates a PDF invoice.
6. Speaks a short confirmation back using Gnani Timbre (text to speech).

Tagline: "Bolo aur bill ban jaye."

Contest requirement: the project must use Gnani AI models or APIs. This app uses Prisma (speech to text) and Timbre (text to speech, beta). Both must be named in the submission.

## 2. Scope

### Must have

- Big mic button: record, send to Prisma, show transcript
- Parse transcript into customer, item, quantity, unit, amount, and payment type (paid or udhaar)
- Confirmation screen with Edit and Save
- Customer ledger with running balance
- PDF invoice for each entry
- Spoken read-back using Timbre

### Nice to have (only if everything above works)

- Voice query: "Sharma ji ka kitna baaki hai?"
- Voice entry for payment received: "Sharma ji ne 300 diye"
- Share invoice on WhatsApp via a `wa.me` link
- Language toggle between Hindi and English UI labels

### Out of scope (do not add)

Logins, multiple shops, GST, inventory, payments, native mobile app, admin panel.

## 3. Tech stack

| Layer | Choice | Notes |
|---|---|---|
| Backend | Python 3.11 + FastAPI | |
| Database | SQLite via SQLModel | Single file, no setup |
| Frontend | Plain HTML + vanilla JS + Tailwind via CDN | Served by FastAPI, no build step |
| Audio capture | Browser `MediaRecorder` API | Needs HTTPS in production (localhost is fine) |
| Audio conversion | ffmpeg on the backend | Browsers record webm/opus. Convert to 16 kHz mono wav unless the Gnani docs say otherwise |
| PDF | ReportLab | Pure Python |
| Parsing | Rule-based Hinglish parser | Optional LLM fallback only if time remains |
| Hosting | Render, Docker deploy | Dockerfile must install ffmpeg |
| Secrets | `.env` locally, Render environment variables in production | |

## 4. Architecture

```
Browser (mic button, confirm screen, ledger)
   |  POST /api/transcribe  (audio blob)
   v
FastAPI backend
   |-- audio.py      convert webm to wav (ffmpeg)
   |-- gnani.py      ONLY file that talks to Gnani (STT + TTS)
   |-- parser.py     Hinglish text to structured entry
   |-- db.py         SQLite models and queries
   |-- invoice.py    PDF generation
   v
SQLite file  +  generated PDFs  +  Timbre audio
```

All Gnani API calls live in `gnani.py` and nowhere else. `gnani.py` must support a `MOCK_GNANI=1` environment variable that returns fixed sample data (a sample transcript and a short silent or sample audio clip), so the rest of the app can be built and tested without spending credits.

Do not invent Gnani endpoints, headers, or request fields. Use only what is in the official documentation provided by the developer. If the details are missing, leave a clearly marked TODO in `gnani.py` and ask.

## 5. Folder structure

```
voice-khata/
  SPEC.md
  README.md
  Dockerfile
  requirements.txt
  .env.example
  .gitignore
  app/
    main.py
    gnani.py
    audio.py
    parser.py
    db.py
    invoice.py
    static/
      index.html
      app.js
  tests/
    test_parser.py
```

`.gitignore` must exclude `.env`, the SQLite database file, generated PDFs, and `__pycache__`.

## 6. Data model

**Customer**
- id
- name
- phone (optional)
- created_at

**Entry**
- id
- customer_id
- item
- quantity
- unit
- amount
- kind: one of `credit` (udhaar), `cash` (paid on the spot), `payment` (money received from the customer)
- raw_transcript
- created_at

**Balance rule:** a customer's balance = sum of `credit` amounts minus sum of `payment` amounts. `cash` entries do not change the balance. Always compute the balance from entries. Never store it as a separate field.

## 7. Parsing rules

The parser takes a transcript string and returns: customer, item, quantity, unit, amount, kind, and a list of missing fields. It must also detect balance queries. It must handle messy spoken Hinglish.

**Customer name**
- The words before "ko", "ka", "ne", or "ke khate".
- Strip honorifics like "ji" only for matching. Keep the name as spoken for display.
- Match against existing customers with fuzzy matching, so "Sharma ji" and "Sharma" map to the same customer.

**Numbers:** support digits and spoken words.
- ek 1, do 2, teen 3, char 4, paanch 5, chhe 6, saat 7, aath 8, nau 9, das 10
- sau 100, hazaar 1000
- dedh 1.5, dhai 2.5, aadha 0.5, sawa 1.25
- Compound forms such as "paanch sau" = 500 and "dedh hazaar" = 1500

**Units:** kilo, kg, gram, litre, packet, dozen, piece. Map common item words to English (for example "chawal" to rice, "cheeni" to sugar, "tel" to oil) and keep the original word too.

**Payment type words**
- credit: udhaar, udhar, baaki, khate mein, credit
- cash: cash, naqad, paid, de diye
- payment received: "ne diye", "jama", "wapas kiye"

**Missing fields:** if a field cannot be found, leave it empty and list it in the missing fields. The confirmation screen must highlight it. Never guess an amount or a customer name.

**Required test cases** (in `tests/test_parser.py`, all must pass)

1. "Sharma ji ko 5 kilo chawal, 600 rupaye, udhaar" gives Sharma ji, rice, 5 kg, 600, credit
2. "Ramesh ko dedh kilo cheeni paanch sau rupaye cash" gives Ramesh, sugar, 1.5 kg, 500, cash
3. "Sharma ji ne 300 diye" gives Sharma ji, payment, 300
4. "Gupta ji ko do litre tel, 280 udhaar" gives Gupta ji, oil, 2 litre, 280, credit
5. "Sharma ji ka kitna baaki hai" is detected as a balance query, not an entry

## 8. API endpoints

- `POST /api/transcribe`: receives audio, returns transcript and parsed entry
- `POST /api/entries`: saves a confirmed entry, returns the updated balance
- `GET /api/customers`: lists customers with id, name, balance, and last_activity
- `GET /api/customers/{id}/entries`: ledger for one customer
- `GET /api/entries/{id}/invoice.pdf`: PDF invoice
- `POST /api/speak`: text in, Timbre audio out
- `GET /api/config`: returns the shop name (SHOP_NAME) for the frontend
- `GET /health`: health check, also used to wake the server on Render

## 9. Frontend requirements

- Mobile-first, readable on a small phone screen.
- One large mic button. Tap to start, tap to stop (or hold to record).
- After recording: show the transcript, then a confirmation card with editable fields (customer, item, quantity, unit, amount, kind) and a Save button. Missing fields are visibly highlighted.
- After saving: play the spoken confirmation, for example "Sharma ji ke khate mein 600 rupaye jod diye".
- Below the mic: list of customers with balances. Tapping a customer shows their ledger and a link to each invoice PDF.
- Handle errors clearly: microphone permission denied, transcription failed (with a retry button), network error.
- Use Tailwind from the CDN. Keep the design simple.

## 10. Invoice requirements

One-page PDF generated with ReportLab, containing: shop name (a configurable constant), date, customer name, item, quantity, unit, amount, payment status (paid or on credit), and the customer's current balance.

## 11. Rules for the coding agent

- Follow this spec. Do not add features that are not in it.
- Work in small steps and wait for the developer to check each step.
- Never put the API key in frontend code, logs, or committed files. Read it only from the `GNANI_API_KEY` environment variable, on the backend.
- All Gnani calls go through `gnani.py` only.
- Never guess an amount or customer name. Missing fields must be shown on the confirmation screen.
- Keep dependencies minimal and explain any new one before adding it.
- Run the tests after changing the parser.
- If something in this spec is unclear or conflicts with the Gnani documentation, stop and ask instead of guessing.

## 12. Deployment

- Dockerfile installs ffmpeg and runs uvicorn on the port provided by the `PORT` environment variable.
- The app must work over HTTPS on Render, since browsers require it for microphone access.
- README explains how to run locally, how to set `GNANI_API_KEY`, how to use `MOCK_GNANI=1`, and how to deploy to Render.

## 13. Additions

### API change
GET /api/customers returns, for each customer: id, name, balance, last_activity (timestamp of the latest entry, or null).

### Config
SHOP_NAME is read from the environment (default: My Shop). It is used in the app header and on the invoice PDF. It is never hardcoded in views.

### Frontend rules (the design/ folder is the visual source of truth)

- Keep the Tailwind classes, colors, fonts, spacing and borders from design/ exactly.
- No backdrop-blur and no shadows anywhere. Use a solid background with a 1px border instead.
- One single-page app: all views live in index.html and switch with JavaScript. No history.back(). The home screen has no back button.
- Views: home, recording, processing, confirm entry, customer ledger.
- Remove anything not backed by an endpoint: statement modal, payment reminder, manual entry, profile avatar, entry search in the ledger, receipt modal, and the separate invoice preview screen. The settings icon stays but does nothing.
- The document icon on a ledger entry opens /api/entries/{id}/invoice.pdf.
- Ledger entry numbers are shown as INV-<entry id>.
- The confirm screen highlights ANY missing field returned by the parser. Save stays disabled until customer, amount and type are filled, plus item unless the type is payment received.
- Customer rows and the summary card (Total udhaar, customer count) are computed from GET /api/customers. No sample data from the design may remain.
