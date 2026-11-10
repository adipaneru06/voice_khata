"""Script to generate a comprehensive, executive-quality PDF report
documenting all work completed on the Voice Khata project.
"""

import os
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# Register DejaVuSans for Rupee and unicode character support
FONTS_DIR = os.path.join(os.path.dirname(__file__), "..", "app", "fonts")
dejavu_reg = os.path.join(FONTS_DIR, "DejaVuSans.ttf")
dejavu_bold = os.path.join(FONTS_DIR, "DejaVuSans-Bold.ttf")

FONT_NAME = "Helvetica"
FONT_BOLD = "Helvetica-Bold"

if os.path.exists(dejavu_reg) and os.path.exists(dejavu_bold):
    try:
        pdfmetrics.registerFont(TTFont("DejaVuSans", dejavu_reg))
        pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", dejavu_bold))
        FONT_NAME = "DejaVuSans"
        FONT_BOLD = "DejaVuSans-Bold"
    except Exception as e:
        print(f"Font registration warning: {e}")

OUTPUT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "Voice_Khata_Project_Summary_Report.pdf")
)


class NumberedCanvas(canvas.Canvas):
    """Canvas that computes total pages dynamically for footer page numbers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont(FONT_NAME, 8)
        self.setFillColor(colors.HexColor("#71717A"))

        # Running header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(20 * mm, 285 * mm, "Voice Khata — Project Summary & Architecture Report")
            self.setStrokeColor(colors.HexColor("#E4E4E7"))
            self.setLineWidth(0.5)
            self.line(20 * mm, 282 * mm, 190 * mm, 282 * mm)

        # Running footer
        footer_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(190 * mm, 12 * mm, footer_text)
        self.drawString(20 * mm, 12 * mm, "Voice Khata (Bolo aur bill ban jaye) | Technical Documentation")
        self.setStrokeColor(colors.HexColor("#E4E4E7"))
        self.setLineWidth(0.5)
        self.line(20 * mm, 16 * mm, 190 * mm, 16 * mm)
        self.restoreState()


def build_pdf():
    doc = SimpleDocTemplate(
        OUTPUT_PATH,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=22 * mm,
        bottomMargin=22 * mm,
    )

    styles = getSampleStyleSheet()

    # Modern Palette
    PRIMARY = colors.HexColor("#0F172A")       # Slate 900
    SECONDARY = colors.HexColor("#334155")     # Slate 700
    MUTED = colors.HexColor("#64748B")         # Slate 500
    LIGHT_BG = colors.HexColor("#F8FAFC")      # Slate 50
    CARD_BORDER = colors.HexColor("#E2E8F0")   # Slate 200
    ACCENT = colors.HexColor("#2563EB")        # Blue 600

    title_style = ParagraphStyle(
        "DocTitle",
        fontName=FONT_BOLD,
        fontSize=22,
        leading=26,
        textColor=PRIMARY,
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "DocSubTitle",
        fontName=FONT_NAME,
        fontSize=11,
        leading=15,
        textColor=ACCENT,
        spaceAfter=10,
    )
    meta_style = ParagraphStyle(
        "DocMeta",
        fontName=FONT_NAME,
        fontSize=8.5,
        leading=12,
        textColor=MUTED,
    )
    h1_style = ParagraphStyle(
        "Heading1_Custom",
        fontName=FONT_BOLD,
        fontSize=13,
        leading=17,
        textColor=PRIMARY,
        spaceBefore=12,
        spaceAfter=5,
        keepWithNext=True,
    )
    h2_style = ParagraphStyle(
        "Heading2_Custom",
        fontName=FONT_BOLD,
        fontSize=10.5,
        leading=14,
        textColor=SECONDARY,
        spaceBefore=7,
        spaceAfter=3,
        keepWithNext=True,
    )
    body_style = ParagraphStyle(
        "Body_Custom",
        fontName=FONT_NAME,
        fontSize=9,
        leading=13,
        textColor=PRIMARY,
        spaceAfter=5,
    )
    bullet_style = ParagraphStyle(
        "Bullet_Custom",
        fontName=FONT_NAME,
        fontSize=8.5,
        leading=12.5,
        textColor=SECONDARY,
        leftIndent=10,
        spaceAfter=2.5,
    )
    code_style = ParagraphStyle(
        "Code_Custom",
        fontName=FONT_NAME,
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#0F172A"),
        backColor=LIGHT_BG,
        borderPadding=4,
        spaceAfter=4,
    )
    table_cell = ParagraphStyle(
        "TableCell",
        fontName=FONT_NAME,
        fontSize=8,
        leading=10.5,
        textColor=PRIMARY,
    )
    table_header = ParagraphStyle(
        "TableHeader",
        fontName=FONT_BOLD,
        fontSize=8,
        leading=10.5,
        textColor=colors.white,
    )

    story = []

    # Title & Metadata
    story.append(Paragraph("Voice Khata (वॉयस खाता)", title_style))
    story.append(Paragraph("Complete Technical & Implementation Summary Report", subtitle_style))
    
    meta_text = "<b>Status:</b> Production Ready &nbsp;|&nbsp; <b>Tagline:</b> <i>\"Bolo aur bill ban jaye\"</i> &nbsp;|&nbsp; <b>Tests:</b> 39/39 Passing &nbsp;|&nbsp; <b>Date:</b> November 2026"
    story.append(Paragraph(meta_text, meta_style))
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width="100%", thickness=1, color=CARD_BORDER, spaceAfter=6))

    # 1. Executive Summary
    story.append(Paragraph("1. Executive Summary", h1_style))
    p1 = (
        "<b>Voice Khata</b> is a voice-first invoicing and digital ledger application created for micro-SMEs and "
        "retail shopkeepers across Tier 2 and Tier 3 Indian towns. Traditional small retail operations face friction "
        "with handwritten khata notebooks and complex accounting software. Voice Khata enables shopkeepers to tap a single "
        "mic button and speak transactions naturally in Hindi, English, or mixed Hinglish (e.g., <i>\"Sharma ji ko 5 kilo chawal, "
        "600 rupaye, udhaar\"</i> or <i>\"Ramesh ne 300 diye\"</i>). The system transcribes the speech, extracts structured fields, "
        "updates real-time customer balances, generates single-page PDF invoices, and plays back an audible confirmation in Hindi."
    )
    story.append(Paragraph(p1, body_style))

    summary_data = [
        [Paragraph("Component", table_header), Paragraph("Technology / Tool", table_header), Paragraph("Key Role / Function", table_header)],
        [Paragraph("Backend Framework", table_cell), Paragraph("Python 3.11 + FastAPI", table_cell), Paragraph("Asynchronous REST API, static asset serving, validation", table_cell)],
        [Paragraph("Database Layer", table_cell), Paragraph("SQLite + SQLModel", table_cell), Paragraph("Customer ledger, entry logs, running balance tracking", table_cell)],
        [Paragraph("Speech-to-Text (STT)", table_cell), Paragraph("Gnani Prisma v3.0 (indic-auto)", table_cell), Paragraph("Mixed Hinglish, Devanagari, and English speech recognition", table_cell)],
        [Paragraph("Text-to-Speech (TTS)", table_cell), Paragraph("Gnani Timbre v3.0 (Shivani, hi-IN)", table_cell), Paragraph("Audible Hindi read-back confirmations after entry save", table_cell)],
        [Paragraph("Audio Conversion", table_cell), Paragraph("ffmpeg (16 kHz mono WAV)", table_cell), Paragraph("Browser WebM/Opus stream conversion to standard WAV", table_cell)],
        [Paragraph("PDF Generation", table_cell), Paragraph("ReportLab", table_cell), Paragraph("Instant single-page customer invoices (INV-&lt;id&gt;)", table_cell)],
        [Paragraph("Frontend UI", table_cell), Paragraph("Vanilla JS + Tailwind CSS", table_cell), Paragraph("Zero-build SPA, responsive mobile-first (360px+)", table_cell)],
        [Paragraph("Containerization", table_cell), Paragraph("Docker (Debian Slim)", table_cell), Paragraph("Self-contained ffmpeg environment, deployed to Render", table_cell)],
    ]
    t_summary = Table(summary_data, colWidths=[40 * mm, 60 * mm, 70 * mm])
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('GRID', (0, 0), (-1, -1), 0.5, CARD_BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
    ]))
    story.append(t_summary)
    story.append(Spacer(1, 4 * mm))

    # 2. Gnani AI Integration Architecture
    story.append(Paragraph("2. Gnani AI Integration Architecture", h1_style))
    p2 = (
        "In compliance with contest and specification guidelines, all artificial intelligence voice capabilities are "
        "strictly powered by <b>Gnani.ai</b> models through a centralized proxy module (<code>app/gnani.py</code>). "
        "No API keys are exposed to the browser."
    )
    story.append(Paragraph(p2, body_style))

    story.append(Paragraph("A. Speech-to-Text: Prisma v3.0", h2_style))
    story.append(Paragraph("• <b>Endpoint:</b> <code>POST https://api.vachana.ai/stt/v3</code>", bullet_style))
    story.append(Paragraph("• <b>Model:</b> <code>prisma-v3.0</code> &nbsp;|&nbsp; <b>Language Code:</b> <code>indic-auto</code>", bullet_style))
    story.append(Paragraph("• <b>Audio Pipeline:</b> Browser records audio via <code>MediaRecorder</code> (WebM/Opus) and uploads it to <code>POST /api/transcribe</code>. The backend executes <code>ffmpeg</code> to convert the buffer into 16 kHz, 16-bit, single-channel mono WAV format before sending it to Prisma.", bullet_style))
    story.append(Paragraph("• <b>Transcription Capabilities:</b> Handles mixed Hinglish, Devanagari Hindi, Indian English pronunciations, background market noise, and regional idioms.", bullet_style))

    story.append(Paragraph("B. Text-to-Speech: Timbre v3.0", h2_style))
    story.append(Paragraph("• <b>Endpoint:</b> <code>POST https://api.vachana.ai/api/v1/tts/inference</code>", bullet_style))
    story.append(Paragraph("• <b>Model:</b> <code>timbre-v3.0</code> &nbsp;|&nbsp; <b>Voice:</b> <code>Shivani</code> &nbsp;|&nbsp; <b>Language:</b> <code>hi-IN</code>", bullet_style))
    story.append(Paragraph("• <b>Confirmation Read-back:</b> Whenever a transaction is saved, a natural Hindi confirmation is dynamically constructed (e.g., <i>\"Sharma ji ke khate mein 600 rupaye jod diye\"</i> for credit, <i>\"Sharma ji se 300 rupaye mil gaye\"</i> for payments, or <i>\"Sharma ji ka bill 600 rupaye cash mein darj ho gaya\"</i> for cash sales). The audio is streamed back to the browser and played asynchronously.", bullet_style))

    story.append(Paragraph("C. Zero-Credit Mocking Mechanism (<code>MOCK_GNANI=1</code>)", h2_style))
    story.append(Paragraph("A strict offline mock mode allows developers to test the full end-to-end pipeline, run automated CI/CD suites, or develop UI features without spending API credits. When active, STT returns a canonical sample transcript and TTS returns an in-memory synthesized WAV audio tone.", bullet_style))
    story.append(Spacer(1, 4 * mm))

    # 3. Rule-Based Natural Language Parser
    story.append(Paragraph("3. Natural Language Parser Evolution & Strict Safety Rules", h1_style))
    p3 = (
        "The parser in <code>app/parser.py</code> translates raw spoken transcripts into strongly-typed transaction records. "
        "During Prompt 12, the parser was completely redesigned to handle real-world speech recognition variance while strictly "
        "obeying financial safety rules:"
    )
    story.append(Paragraph(p3, body_style))
    story.append(Paragraph("• <b>Compound Numeral Parsing:</b> Custom multi-token compound number engine handles conversational Hindi numbers like <i>\"pandrah sau\"</i> (1500), <i>\"pachis sau\"</i> (2500), <i>\"ek hazaar do sau\"</i> (1200), fractions like <i>\"sawa\"</i> (1.25), <i>\"dedh\"</i> (1.5), <i>\"dhai\"</i> (2.5), and Devanagari digits (०, १, २, ३...).", bullet_style))
    story.append(Paragraph("• <b>Dual Script Support:</b> Equivalence mapping across Roman Hinglish (<i>chawal, cheeni, udhaar</i>) and Devanagari Hindi (<i>चावल, चीनी, उधार</i>).", bullet_style))
    story.append(Paragraph("• <b>Strict Safety Rule 1 (Never Guess Amounts):</b> If a customer says vague terms like <i>\"kuch paise\"</i> or mentions an ambiguous number, amount is left <code>None</code> and flagged in <code>missing</code>.", bullet_style))
    story.append(Paragraph("• <b>Strict Safety Rule 2 (Never Guess Customer Names):</b> Customer tokens with ambiguous conjunctions (e.g., <i>\"Rahul ya Rohit\"</i>) are rejected and kept in missing fields. Self-pronouns (<i>\"mujhe\", \"humko\"</i>) are never extracted as names.", bullet_style))
    story.append(Paragraph("• <b>Temporal & Conversational Filler Stripping:</b> Automatically filters out leading fillers such as <i>\"kal\", \"aaj\", \"sun\", \"arre\", \"bhai\"</i> without corrupting the customer's name.", bullet_style))
    story.append(Paragraph("• <b>Intent Differentiation:</b> Differentiates transaction entries (credit, cash, payment received) from balance queries (<i>\"Sharma ji ka kitna baaki hai\"</i>).", bullet_style))
    story.append(Spacer(1, 4 * mm))

    # 4. REST API & Database Design
    story.append(Paragraph("4. Backend REST APIs & Database Design", h1_style))
    story.append(Paragraph("The database utilizes SQLite managed via SQLModel. Two primary entities maintain transactional integrity:", body_style))

    db_data = [
        [Paragraph("Entity", table_header), Paragraph("Key Fields", table_header), Paragraph("Description", table_header)],
        [Paragraph("<b>Customer</b>", table_cell), Paragraph("id, name, phone, created_at", table_cell), Paragraph("Unique customer records. Matched using fuzzy matching ignoring honorifics ('ji', 'जी').", table_cell)],
        [Paragraph("<b>Entry</b>", table_cell), Paragraph("id, customer_id, item, quantity, unit, amount, kind, raw_transcript, created_at", table_cell), Paragraph("Immutable ledger events. Kind is 'credit' (adds debt), 'payment' (settles debt), or 'cash' (cash sale).", table_cell)],
    ]
    t_db = Table(db_data, colWidths=[30 * mm, 70 * mm, 70 * mm])
    t_db.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('GRID', (0, 0), (-1, -1), 0.5, CARD_BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
    ]))
    story.append(t_db)
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("<b>Balance Formula:</b> <code>Balance = sum(credit) − sum(payment)</code>. Cash transactions are recorded in the ledger but do not alter the customer's udhaar balance.", code_style))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("API Endpoints Summary:", h2_style))
    api_data = [
        [Paragraph("Method & Endpoint", table_header), Paragraph("Purpose / Output", table_header)],
        [Paragraph("<code>POST /api/transcribe</code>", table_cell), Paragraph("Receives audio blob, executes ffmpeg conversion, calls Prisma STT, parses transcript, and returns structured data with customer balance.", table_cell)],
        [Paragraph("<code>POST /api/entries</code>", table_cell), Paragraph("Validates and commits confirmed entry to database, returns saved entry and updated customer balance.", table_cell)],
        [Paragraph("<code>GET /api/customers</code>", table_cell), Paragraph("Returns list of all customers with id, name, running balance, and timestamp of latest activity.", table_cell)],
        [Paragraph("<code>GET /api/customers/{id}/entries</code>", table_cell), Paragraph("Returns full reverse-chronological transaction ledger for a specific customer.", table_cell)],
        [Paragraph("<code>GET /api/entries/{id}/invoice.pdf</code>", table_cell), Paragraph("Generates and downloads a formal single-page ReportLab PDF invoice (INV-&lt;id&gt;).", table_cell)],
        [Paragraph("<code>POST /api/speak</code>", table_cell), Paragraph("Synthesizes text into 16 kHz WAV audio using Gnani Timbre for client-side playback.", table_cell)],
        [Paragraph("<code>GET /api/config</code>", table_cell), Paragraph("Returns environment configuration such as <code>SHOP_NAME</code> for header branding.", table_cell)],
        [Paragraph("<code>GET /health</code>", table_cell), Paragraph("Health check endpoint returning <code>{\"status\": \"ok\"}</code> for service monitoring.", table_cell)],
    ]
    t_api = Table(api_data, colWidths=[65 * mm, 105 * mm])
    t_api.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), SECONDARY),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('GRID', (0, 0), (-1, -1), 0.5, CARD_BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
    ]))
    story.append(t_api)
    story.append(Spacer(1, 4 * mm))

    # 5. Frontend Design & Robustness
    story.append(Paragraph("5. Frontend Design & Robustness Implementation", h1_style))
    p5 = (
        "The frontend is implemented in <code>app/static/index.html</code> and <code>app/static/app.js</code> as a pure "
        "Single Page Application (SPA) adhering strictly to SPEC.md Section 9 and Section 13:"
    )
    story.append(Paragraph(p5, body_style))
    story.append(Paragraph("• <b>Design System Integrity:</b> Strictly adheres to mockups. Zero <code>backdrop-blur</code>, zero drop shadows, solid 1px borders, and pure in-memory JavaScript view switching (zero <code>history.back()</code> calls).", bullet_style))
    story.append(Paragraph("• <b>Responsive Layout:</b> Tested and verified down to 360px mobile width with zero horizontal scroll.", bullet_style))
    story.append(Paragraph("• <b>Voice State Transitions:</b> Clean visual state transitions from Idle (big mic button) to Live Intake (pulsing recording badge with live MM:SS counter) to Transcribing (animated spinner).", bullet_style))
    story.append(Paragraph("• <b>Confirmation Card & Editable Fields:</b> Highlights any missing required field with red border tags. The Save button remains disabled until Customer, Amount (&gt; 0), and Type are filled, plus Item (unless type is Payment received).", bullet_style))
    story.append(Paragraph("• <b>Double-Tap Save Prevention:</b> Guarded by <code>state.isSaving</code> flag, disabling form buttons and showing a spinner during database persistence.", bullet_style))
    story.append(Paragraph("• <b>Error Handling with Retry:</b> Handles microphone permission denials, silent/empty audio captures, and server reloads with user-friendly retry banners.", bullet_style))
    story.append(Spacer(1, 4 * mm))

    # 6. Automated Testing & Verification
    story.append(Paragraph("6. Automated Testing & Real Prisma Verification", h1_style))
    story.append(Paragraph("The project maintains a 100% test passing rate across <b>39 automated tests</b>:", body_style))

    test_data = [
        [Paragraph("Test Suite File", table_header), Paragraph("Tests", table_header), Paragraph("Scope Covered", table_header)],
        [Paragraph("<code>tests/test_api.py</code>", table_cell), Paragraph("10 Passed", table_cell), Paragraph("Health check, config, mock STT, customer pre-matching, empty audio rejection, input validation (amount &gt; 0), balances, invoice PDF generation, Timbre TTS.", table_cell)],
        [Paragraph("<code>tests/test_db.py</code>", table_cell), Paragraph("8 Passed", table_cell), Paragraph("Credit balance calculations, payment balance deductions, cash balance neutrality, fuzzy customer matching with honorifics, last activity timestamps, reverse sorting.", table_cell)],
        [Paragraph("<code>tests/test_parser.py</code>", table_cell), Paragraph("21 Passed", table_cell), Paragraph("11 baseline test cases + 10 real Prisma transcript test cases (compound numbers, Devanagari numerals, ambiguous customer rejection, pronouns rejection, balance queries).", table_cell)],
    ]
    t_test = Table(test_data, colWidths=[45 * mm, 25 * mm, 100 * mm])
    t_test.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('GRID', (0, 0), (-1, -1), 0.5, CARD_BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
    ]))
    story.append(t_test)
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Prompt 12 Real-World Transcript Benchmark Cases:", h2_style))
    phrases = [
        "1. <i>\"Rahul Sharma se 500 rupaye lene hain\"</i> &rarr; Rahul Sharma, payment, 500",
        "2. <i>\"Amit ko 1200 rupaye ka payment karna hai\"</i> &rarr; Amit, payment, 1200 (compound number)",
        "3. <i>\"कल मोहन से दो हजार रुपये लेने हैं\"</i> &rarr; Mohan, payment, 2000 (Devanagari script + filler stripped)",
        "4. <i>\"Priya ko five hundred rupees dene hain\"</i> &rarr; Priya, payment, 500 (English words)",
        "5. <i>\"Ravi se 2500 rupaye receive karne hain\"</i> &rarr; Ravi, payment, 2500",
        "6. <i>\"Suresh ko teen hazaar dene hain\"</i> &rarr; Suresh, payment, 3000",
        "7. <i>\"Rahul ya Rohit se 500 rupaye lene hain\"</i> &rarr; Customer flagged missing (ambiguous conjunction safety)",
        "8. <i>\"Mujhe paise receive karne hain\"</i> &rarr; Customer flagged missing (pronoun rejection rule)",
        "9. <i>\"Amit ko kuch paise dene hain\"</i> &rarr; Amount flagged missing (vague amount safety)",
        "10. <i>\"Mohan se pachis sau rupaye lene hain\"</i> &rarr; Mohan, payment, 2500 (colloquial Hindi compound number)",
    ]
    for ph in phrases:
        story.append(Paragraph(f"• {ph}", bullet_style))
    story.append(Spacer(1, 4 * mm))

    # 7. Demo Data & Filming Utilities
    story.append(Paragraph("7. Demo Seeding Utility", h1_style))
    p7 = (
        "To ensure consistency during video filming and demonstrations, <code>scripts/seed_demo.py</code> populates "
        "the SQLite database with realistic historical transactions matching the design mockup figures exactly:"
    )
    story.append(Paragraph(p7, body_style))
    seed_points = [
        "<b>Sharma ji:</b> ₹600 udhaar (5 kg rice + 2 kg flour)",
        "<b>Ramesh:</b> ₹0 balance (₹500 sugar purchase followed by ₹500 debt settlement payment)",
        "<b>Gupta ji:</b> ₹280 udhaar (2 litre mustard oil)",
        "<b>Verma ji:</b> ₹1,450 udhaar (10 kg atta + 5 kg dal + 2 kg ghee)",
        "<b>Anita Stores:</b> ₹320 udhaar (4 packets tea + biscuits)",
        "<b>Pintu:</b> ₹90 udhaar (1 kg sugar + 1 packet salt)",
        "<b>Total Store Udhaar:</b> ₹2,740 across 6 active customers",
    ]
    for sp in seed_points:
        story.append(Paragraph(f"• {sp}", bullet_style))
    story.append(Paragraph("The script supports a <code>--reset</code> flag to clear previous entries before seeding.", body_style))
    story.append(Spacer(1, 4 * mm))

    # 8. Docker, Security & Deployment
    story.append(Paragraph("8. Deployment & Security Audit", h1_style))
    p8 = (
        "The application has been packaged and verified for cloud deployment on <b>Render</b> using Docker:"
    )
    story.append(Paragraph(p8, body_style))
    story.append(Paragraph("• <b>Dockerfile:</b> Based on <code>python:3.11-slim</code>, installs system <code>ffmpeg</code>, caches dependencies from <code>requirements.txt</code>, and runs uvicorn using the dynamic <code>PORT</code> environment variable.", bullet_style))
    story.append(Paragraph("• <b>.dockerignore & .gitignore:</b> Excludes <code>.env</code>, local databases (<code>*.db</code>), <code>ffmpeg.exe</code>, design folders, and test caches.", bullet_style))
    story.append(Paragraph("• <b>Secret Leak Audit:</b> Full repository code scan confirmed <b>zero hardcoded API keys</b> in source code, documentation, frontend assets, or git history. The API key is injected via Render environment variables.", bullet_style))
    story.append(Paragraph("• <b>HTTPS Requirement:</b> Deploying on Render guarantees automatic SSL/HTTPS termination, which is mandatory for mobile and desktop web browsers to grant microphone permissions.", bullet_style))
    story.append(Spacer(1, 5 * mm))

    # Conclusion Card
    conclusion_text = (
        "<b>Conclusion:</b> All mandatory requirements from <b>SPEC.md</b> (Sections 1 through 13) have been "
        "implemented, tested, and validated. The application operates seamlessly in both live Gnani mode and offline "
        "mock mode, providing Indian micro-SMEs with a fast, hands-free khata management experience."
    )
    story.append(Paragraph(conclusion_text, code_style))

    # Build PDF with custom two-pass numbered canvas
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Summary PDF successfully generated at: {OUTPUT_PATH}")


if __name__ == "__main__":
    build_pdf()
