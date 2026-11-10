"""PDF invoice generation using ReportLab.

One-page A4 invoice:
- shop name from SHOP_NAME
- invoice number INV-<entry id>
- date
- customer name
- item, quantity, unit, amount
- payment status (Paid, On credit, or Payment received)
- customer's current balance

Plain black text on white, simple table, no logo or colors.
Rupee symbol (₹) rendered using DejaVuSans.
"""

import os
from datetime import datetime, timezone
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

INVOICES_DIR = os.path.join(os.path.dirname(__file__), "..", "invoices")
FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")

FONT_REGULAR = "Helvetica"
FONT_BOLD = "Helvetica-Bold"


def _register_fonts():
    """Register DejaVuSans (or system fallback) to support the Indian Rupee symbol (₹)."""
    global FONT_REGULAR, FONT_BOLD

    dejavu_reg = os.path.join(FONTS_DIR, "DejaVuSans.ttf")
    dejavu_bold = os.path.join(FONTS_DIR, "DejaVuSans-Bold.ttf")

    if os.path.exists(dejavu_reg):
        try:
            pdfmetrics.registerFont(TTFont("DejaVuSans", dejavu_reg))
            FONT_REGULAR = "DejaVuSans"

            if os.path.exists(dejavu_bold):
                pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", dejavu_bold))
                FONT_BOLD = "DejaVuSans-Bold"
            else:
                FONT_BOLD = "DejaVuSans"
            return
        except Exception:
            pass

    # Fallback to system TrueType fonts that include the ₹ symbol on Windows
    for reg, bold in [
        (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\segoeuib.ttf"),
        (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf"),
    ]:
        if os.path.exists(reg):
            try:
                pdfmetrics.registerFont(TTFont("SystemFont", reg))
                FONT_REGULAR = "SystemFont"
                if os.path.exists(bold):
                    pdfmetrics.registerFont(TTFont("SystemFont-Bold", bold))
                    FONT_BOLD = "SystemFont-Bold"
                else:
                    FONT_BOLD = "SystemFont"
                return
            except Exception:
                pass


_register_fonts()


def _ensure_dir():
    os.makedirs(INVOICES_DIR, exist_ok=True)


def format_payment_status(kind: str) -> str:
    """Format payment status into: Paid, On credit, or Payment received."""
    k = kind.lower().strip()
    if k == "credit":
        return "On credit"
    elif k == "cash":
        return "Paid"
    elif k == "payment":
        return "Payment received"
    return kind.capitalize()


def generate_invoice(
    entry_id: int,
    shop_name: str,
    customer_name: str,
    item: str | None,
    quantity: float | None,
    unit: str | None,
    amount: float,
    kind: str,
    balance: float,
    created_at: datetime | None = None,
) -> str:
    """Generate a clean, black-and-white, one-page A4 PDF invoice.

    Returns:
        The absolute path to the generated PDF invoice.
    """
    _ensure_dir()
    path = os.path.abspath(os.path.join(INVOICES_DIR, f"invoice_{entry_id}.pdf"))

    date_str = (created_at or datetime.now(timezone.utc)).strftime("%d %b %Y, %I:%M %p")
    invoice_no = f"INV-{entry_id}"
    payment_status = format_payment_status(kind)

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    # Strict black and white styling (no logo, no colors)
    c.setFillColorRGB(0, 0, 0)
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(0.5)

    left_margin = 20 * mm
    right_margin = width - 20 * mm
    content_width = right_margin - left_margin

    y = height - 25 * mm

    # 1. Shop Name & Title Header
    c.setFont(FONT_BOLD, 18)
    c.drawString(left_margin, y, shop_name)

    c.setFont(FONT_BOLD, 14)
    c.drawRightString(right_margin, y, "INVOICE")
    y -= 8 * mm

    # Divider line
    c.setLineWidth(1)
    c.line(left_margin, y, right_margin, y)
    c.setLineWidth(0.5)
    y -= 10 * mm

    # 2. Invoice Meta Information
    c.setFont(FONT_BOLD, 10)
    c.drawString(left_margin, y, "Invoice Number:")
    c.setFont(FONT_REGULAR, 10)
    c.drawString(left_margin + 32 * mm, y, invoice_no)

    c.setFont(FONT_BOLD, 10)
    c.drawString(left_margin + 90 * mm, y, "Date:")
    c.setFont(FONT_REGULAR, 10)
    c.drawString(left_margin + 105 * mm, y, date_str)
    y -= 6 * mm

    c.setFont(FONT_BOLD, 10)
    c.drawString(left_margin, y, "Customer:")
    c.setFont(FONT_REGULAR, 10)
    c.drawString(left_margin + 32 * mm, y, customer_name)
    y -= 12 * mm

    # 3. Simple Table (Plain black borders on white)
    # Column coordinates
    col_item = left_margin + 3 * mm
    col_qty = left_margin + 80 * mm
    col_unit = left_margin + 110 * mm
    col_amount = right_margin - 3 * mm

    table_top = y
    row_height = 8 * mm
    header_bottom = table_top - row_height
    data_bottom = header_bottom - row_height

    # Outer table border
    c.rect(left_margin, data_bottom, content_width, row_height * 2, stroke=1, fill=0)

    # Header horizontal separator
    c.line(left_margin, header_bottom, right_margin, header_bottom)

    # Vertical column dividers
    c.line(left_margin + 75 * mm, table_top, left_margin + 75 * mm, data_bottom)
    c.line(left_margin + 105 * mm, table_top, left_margin + 105 * mm, data_bottom)
    c.line(left_margin + 135 * mm, table_top, left_margin + 135 * mm, data_bottom)

    # Table Header text
    c.setFont(FONT_BOLD, 10)
    text_y_header = header_bottom + 2.5 * mm
    c.drawString(col_item, text_y_header, "Item")
    c.drawString(col_qty, text_y_header, "Quantity")
    c.drawString(col_unit, text_y_header, "Unit")
    c.drawRightString(col_amount, text_y_header, "Amount (₹)")

    # Table Data Row text
    c.setFont(FONT_REGULAR, 10)
    text_y_data = data_bottom + 2.5 * mm

    item_display = item if item else ("Payment" if kind == "payment" else "—")
    qty_display = str(int(quantity)) if (quantity is not None and quantity.is_integer()) else (str(quantity) if quantity is not None else "—")
    unit_display = unit if unit else "—"
    amount_display = f"₹{amount:,.2f}"

    c.drawString(col_item, text_y_data, item_display)
    c.drawString(col_qty, text_y_data, qty_display)
    c.drawString(col_unit, text_y_data, unit_display)
    c.drawRightString(col_amount, text_y_data, amount_display)

    y = data_bottom - 12 * mm

    # 4. Payment Status & Current Balance
    c.setFont(FONT_BOLD, 10)
    c.drawString(left_margin, y, "Payment Status:")
    c.setFont(FONT_REGULAR, 10)
    c.drawString(left_margin + 35 * mm, y, payment_status)
    y -= 6 * mm

    c.setFont(FONT_BOLD, 10)
    c.drawString(left_margin, y, "Current Balance:")
    c.setFont(FONT_BOLD, 10)
    balance_display = f"₹{balance:,.2f}"
    c.drawString(left_margin + 35 * mm, y, balance_display)
    y -= 25 * mm

    # 5. Footer (Simple closing note)
    c.setFont(FONT_REGULAR, 9)
    c.drawCentredString(width / 2.0, 20 * mm, "Thank you for your business!")

    # Complete page
    c.showPage()
    c.save()

    with open(path, "wb") as f:
        f.write(buf.getvalue())

    return path
