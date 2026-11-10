# Voice Khata (वॉयस खाता)

> **"Bolo aur bill ban jaye"** — A voice-first ledger and invoicing app for micro-SMEs and small shopkeepers in India.

Voice Khata simplifies bookkeeping for local shop owners. Instead of manually typing or writing on paper ledgers, shopkeepers tap a microphone and speak naturally in Hindi, English, or Hinglish (e.g., *"Sharma ji ko 5 kilo chawal, 600 rupaye, udhaar"* or *"Ramesh ne 300 diye"*). The app automatically extracts transaction details, updates running customer balances, generates downloadable PDF invoices, and speaks an audible Hindi confirmation back to the shopkeeper.

---

## Features

- **Voice Recording & Transcription**: Tap-to-record voice interface using browser `MediaRecorder` converted to 16 kHz mono WAV.
- **Natural Language Parsing**: High-accuracy rule-based parser handling Hindi, English, and Hinglish compound numerals, units, customer names, and transaction types.
- **Editable Confirmation Card**: Visual verification step highlighting missing or ambiguous fields before committing transactions.
- **Customer Ledger & Balances**: Automatic tracking of credit (udhaar), cash sales, and debt settlements.
- **Instant PDF Invoices**: Clean, single-page PDF invoices generated with ReportLab (`INV-<id>`).
- **Spoken Confirmations**: Audio playback confirming successful transactions (e.g., *"Sharma ji ke khate mein 600 rupaye jod diye"*).
- **Mobile-First Design**: Optimized for small smartphone screens (360px+) with zero horizontal scrolling.

---

## Gnani AI Models Used

This project integrates two core models from **Gnani.ai**:

1. **Prisma (Speech-to-Text)**
   - **Model**: `prisma-v3.0`
   - **Endpoint**: `POST https://api.vachana.ai/stt/v3`
   - **Language Code**: `indic-auto` (automatic detection of Indic dialects, Devanagari Hindi, and Roman Hinglish)
   - **Role**: Accurately transcribes shopkeeper speech from 16 kHz mono audio.

2. **Timbre (Text-to-Speech)**
   - **Model**: `timbre-v3.0`
   - **Endpoint**: `POST https://api.vachana.ai/api/v1/tts/inference`
   - **Voice & Language**: `Shivani` (`hi-IN`)
   - **Audio Format**: 16 kHz linear PCM WAV
   - **Role**: Speaks concise Hindi confirmations aloud after saving entries.

---

## Environment Variables

Copy `.env.example` to `.env` to configure the application:

```bash
cp .env.example .env
```

| Variable | Required | Default | Description |
|---|---|---|---|
| `GNANI_API_KEY` | Yes (for live AI) | `""` | API key from Gnani AI / Vachana platform. |
| `MOCK_GNANI` | No | `0` | Set to `1` to run without API keys (offline mock mode). Set to `0` for live STT and TTS. |
| `SHOP_NAME` | No | `My Shop` | Shop name displayed on dashboard headers and PDF invoices. |
| `PORT` | No | `8000` | Port on which the FastAPI server listens (automatically supplied by Render in production). |

> **Security Note:** Never commit your `.env` file or API keys to version control. The `.gitignore` and `.dockerignore` files are preconfigured to ignore `.env`.

---

## Using Mock Mode (`MOCK_GNANI=1`)

To test the application locally or in CI without consuming Gnani API credits or when offline:

1. In your `.env` file, set:
   ```env
   MOCK_GNANI=1
   ```
2. When `MOCK_GNANI=1`:
   - STT returns a canned transcript (*"Sharma ji ko 5 kilo chawal 600 rupaye udhaar"*).
   - TTS returns a synthesized WAV audio tone.
   - No external requests are sent to Gnani AI endpoints.

To switch back to live speech recognition and voice synthesis, set `MOCK_GNANI=0` and provide a valid `GNANI_API_KEY`.

---

## How to Run Locally

### Prerequisites

- **Python 3.11+** installed.
- **ffmpeg** installed on your system PATH (required to convert browser audio formats like WebM/Opus to WAV).
  - *Windows*: Install via `winget install Gyan.FFmpeg` or place `ffmpeg.exe` in the project root.
  - *macOS*: `brew install ffmpeg`
  - *Ubuntu/Debian*: `sudo apt-get install ffmpeg`

### Step-by-Step Setup

1. **Clone the repository**:
   ```bash
   git clone <repo-url>
   cd "Khata voice"
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .venv\Scripts\Activate.ps1
   # macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env and set your GNANI_API_KEY (or set MOCK_GNANI=1 for offline testing)
   ```

5. **(Optional) Seed demo data**:
   ```bash
   python scripts/seed_demo.py --reset
   ```

6. **Start the local development server**:
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

7. **Access the application**:
   Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## Running Tests

The test suite covers API endpoints, database operations, and the parser (including real Gnani Prisma transcripts, compound Hindi numbers, Devanagari numerals, and Hinglish queries):

```bash
pytest tests/ -v
```

All 39 unit and integration tests should pass.

---

## How to Deploy to Render

Voice Khata is containerized with Docker, satisfying browser HTTPS requirements for microphone access (`MediaRecorder` API).

### Step 1: Push Code to GitHub / GitLab

Ensure your repository is pushed to GitHub or GitLab. (Verify that `.env` is NOT tracked in git).

### Step 2: Create a Web Service on Render

1. Log in to your [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** and select **Web Service**.
3. Select **Build and deploy from a Git repository** and connect your repository.

### Step 3: Exact Render Configuration Settings

Configure the following exact settings in the Render setup screen:

- **Name**: `voice-khata` (or your preferred name)
- **Region**: Select the region closest to your users (e.g., `Singapore` or `Frankfurt`)
- **Branch**: `main`
- **Root Directory**: *(leave blank — root of repository)*
- **Runtime / Environment**: **Docker**
- **Instance Type**: **Free** (or Starter)
- **Health Check Path**: `/health`

### Step 4: Configure Environment Variables on Render

In the **Environment Variables** section of the Render service page, add:

| Key | Value | Notes |
|---|---|---|
| `GNANI_API_KEY` | `your_actual_gnani_api_key` | Your secret API key from Gnani AI |
| `MOCK_GNANI` | `0` | Set to `0` for live speech models (or `1` for demo without key) |
| `SHOP_NAME` | `My Shop` | Your shop or business display name |

*(Note: Render automatically populates and passes the `PORT` environment variable to the container, which the Dockerfile uses to start uvicorn).*

### Step 5: Deploy

1. Click **Create Web Service**.
2. Render will build the Docker container (installing `ffmpeg` and Python dependencies), expose the application over HTTPS, and monitor `/health`.
3. Once deployed, open your `https://<service-name>.onrender.com` URL in any mobile or desktop browser and allow microphone permissions.
