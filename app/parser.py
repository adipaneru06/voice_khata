"""Hinglish and Hindi transcript parser.

Extracts structured transaction fields from spoken text in Roman (Hinglish)
and Devanagari script: customer, item, quantity, unit, amount, kind, missing fields.
Also detects balance queries and handles ambiguous/missing entities strictly.
"""

import re
from typing import Any, Optional

# ===========================================================================
# DICTIONARIES (Roman, Devanagari, English, and Transliterations)
# ===========================================================================

# Digits mapping (including Devanagari numerals)
DEVANAGARI_DIGITS = {
    "०": "0", "१": "1", "२": "2", "३": "3", "४": "4",
    "५": "5", "६": "6", "७": "7", "८": "8", "९": "9",
}

# Base numbers (0 to 99, fractions, English numbers, and Devanagari transliterations)
NUMBER_WORDS: dict[str, float] = {
    # Fractions & special
    "aadha": 0.5, "adha": 0.5, "आधा": 0.5,
    "paun": 0.75, "पौने": 0.75, "पौन": 0.75,
    "sawa": 1.25, "सवा": 1.25,
    "dedh": 1.5, "dhedh": 1.5, "डेढ़": 1.5, "डेढ": 1.5,
    "dhai": 2.5, "dhaai": 2.5, "ढाई": 2.5,

    # 0 to 10 (Hindi & Devanagari)
    "zero": 0, "शून्य": 0, "ज़ीरो": 0, "जीरो": 0,
    "ek": 1, "एक": 1,
    "do": 2, "दो": 2,
    "teen": 3, "tin": 3, "तीन": 3,
    "char": 4, "chaar": 4, "चार": 4,
    "paanch": 5, "panch": 5, "पांच": 5, "पाँच": 5,
    "chhe": 6, "che": 6, "chheh": 6, "छह": 6, "छः": 6,
    "saat": 7, "सात": 7,
    "aath": 8, "ath": 8, "आठ": 8,
    "nau": 9, "नो": 9, "नौ": 9,
    "das": 10, "दस": 10,

    # 11 to 20 (Hindi & Devanagari)
    "gyarah": 11, "ग्यारह": 11,
    "barah": 12, "बारह": 12,
    "terah": 13, "तेरह": 13,
    "chaudah": 14, "चौदह": 14,
    "pandrah": 15, "पंद्रह": 15,
    "solah": 16, "सोलह": 16,
    "satrah": 17, "सत्रह": 17,
    "atharah": 18, "अठारह": 18,
    "unnis": 19, "उन्नीस": 19,
    "bees": 20, "bis": 20, "बीस": 20,

    # Tens / common numbers (Hindi & Devanagari)
    "ikkees": 21, "इक्कीस": 21,
    "baees": 22, "बाईस": 22,
    "tayees": 23, "तेईस": 23,
    "chaubees": 24, "चौबीस": 24,
    "pachees": 25, "pachis": 25, "पच्चीस": 25, "पचीस": 25,
    "tees": 30, "तीस": 30,
    "paitees": 35, "पैंतीस": 35,
    "chalis": 40, "chaalis": 40, "चालीस": 40,
    "painchalis": 45, "पैंतालीस": 45,
    "pachas": 50, "पचास": 50,
    "saath": 60, "साठ": 60,
    "sattar": 70, "सत्तर": 70,
    "assi": 80, "अस्सी": 80,
    "nabbe": 90, "नब्बे": 90,

    # English number words
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "twenty-five": 25, "thirty": 30, "thirty-five": 35, "forty": 40, "forty-five": 45,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,

    # English numbers in Devanagari (common Prisma STT outputs)
    "वन": 1, "टू": 2, "थ्री": 3, "फोर": 4, "फ़ोर": 4, "फाइव": 5, "फ़ाइव": 5,
    "सिक्स": 6, "सेवन": 7, "एट": 8, "नाइन": 9, "टेन": 10,
    "ट्वेंटी": 20, "ट्वेन्टी": 20, "थर्टी": 30, "फॉर्टी": 40, "फ़िफ्टी": 50, "फिफ्टी": 50,
}

# Multipliers (sau, hazaar, lakh, crore, hundred, thousand)
MULTIPLIER_WORDS: dict[str, float] = {
    "sau": 100, "so": 100, "सौ": 100, "सैकड़ा": 100,
    "hundred": 100, "हंड्रेड": 100, "हन्ड्रेड": 100,
    "hazaar": 1000, "hazar": 1000, "हज़ार": 1000, "हजार": 1000,
    "thousand": 1000, "थाउजेंड": 1000, "थाउज़ेंड": 1000, "थाउजंड": 1000,
    "lakh": 100000, "lakhs": 100000, "lac": 100000, "lacs": 100000, "लाख": 100000,
    "crore": 10000000, "crores": 10000000, "करोड़": 10000000,
}

# Units (singular / plural / common spellings)
UNIT_MAP: dict[str, str] = {
    "kilo": "kg", "kilos": "kg", "kg": "kg", "kgs": "kg", "किलो": "kg", "किग्रा": "kg", "केजी": "kg",
    "gram": "gram", "grams": "gram", "gm": "gram", "gms": "gram", "ग्राम": "gram", "ग्रा": "gram",
    "litre": "litre", "liter": "litre", "litres": "litre", "liters": "litre", "ltr": "litre", "लीटर": "litre",
    "packet": "packet", "packets": "packet", "pkt": "packet", "pkts": "packet", "पैकेट": "packet",
    "dozen": "dozen", "darjan": "dozen", "दर्जन": "dozen",
    "piece": "piece", "pieces": "piece", "pc": "piece", "pcs": "piece", "पीस": "piece", "नग": "piece",
    "dabba": "packet", "डिब्बा": "packet", "बोतल": "piece", "bottle": "piece",
}

# Items (Hinglish / Hindi -> normalized English)
ITEM_MAP: dict[str, str] = {
    "chawal": "rice", "chaawal": "rice", "चावल": "rice",
    "cheeni": "sugar", "chini": "sugar", "शक्कर": "sugar", "चीनी": "sugar",
    "tel": "oil", "tail": "oil", "तेल": "oil",
    "atta": "flour", "aata": "flour", "आटा": "flour",
    "dal": "lentils", "daal": "lentils", "दाल": "lentils",
    "sabun": "soap", "साबुन": "soap",
    "chai": "tea", "chay": "tea", "चाय": "tea",
    "doodh": "milk", "dudh": "milk", "दूध": "milk",
    "namak": "salt", "नमक": "salt",
    "mirch": "chilli", "मिर्च": "chilli",
    "haldi": "turmeric", "हल्दी": "turmeric",
    "biscuit": "biscuit", "biskut": "biscuit", "बिस्कुट": "biscuit", "बिस्किट": "biscuit",
    "ghee": "ghee", "घी": "ghee",
    "masala": "spices", "मसाला": "spices",
    "bread": "bread", "ब्रेड": "bread",
    "anda": "egg", "ande": "egg", "अंडा": "egg", "अंडे": "egg",
}

# Payment kind keywords
PAYMENT_KIND_MAP: dict[str, str] = {
    # Credit
    "udhaar": "credit", "udhar": "credit", "baaki": "credit", "baki": "credit",
    "credit": "credit", "उधार": "credit", "बाकी": "credit", "क्रेडिट": "credit",

    # Cash
    "cash": "cash", "naqad": "cash", "nakad": "cash", "paid": "cash",
    "कैश": "cash", "नकद": "cash",

    # Payment received / give payment
    "jama": "payment", "जमा": "payment",
    "payment": "payment", "पेमेंट": "payment",
    "receive": "payment", "रिसीव": "payment",
}

PAYMENT_PHRASES: list[tuple[str, str]] = [
    # Credit phrases
    ("khate mein", "credit"),
    ("खाते में", "credit"),
    ("खाता में", "credit"),

    # Cash phrases
    ("de diye", "cash"),
    ("दे दिए", "cash"),
    ("दे दिया", "cash"),

    # Payment received phrases
    ("wapas kiye", "payment"),
    ("वापस किए", "payment"),
    ("वापस किया", "payment"),
    ("ne diye", "payment"),
    ("ने दिए", "payment"),
    ("ने दिया", "payment"),
    ("mila hai", "payment"),
    ("mile hain", "payment"),
    ("मिला है", "payment"),
    ("मिले हैं", "payment"),
    ("receive karne", "payment"),
    ("receive karna", "payment"),
    ("रिसीव करने", "payment"),
    ("रिसीव करना", "payment"),
    ("payment karna", "payment"),
    ("payment karne", "payment"),
    ("पेमेंट करना", "payment"),
    ("पेमेंट करने", "payment"),
    ("lene hain", "payment"),
    ("lena hai", "payment"),
    ("लेने हैं", "payment"),
    ("लेना है", "payment"),
    ("dene hain", "payment"),
    ("dena hai", "payment"),
    ("देने हैं", "payment"),
    ("देना है", "payment"),
]

# Balance query indicators
BALANCE_QUERY_WORDS = [
    "kitna baaki", "kitna baki", "kitna udhaar", "kitna udhar",
    "कितना बाकी", "कितना उधार", "kitna bacha", "कितना बचा",
    "balance", "बैलेंस", "hisaab", "hisab", "हिसाब"
]

# Markers identifying the customer name boundary
CUSTOMER_MARKERS = [
    "ke khate", "के खाते", "के खाता",
    "ko", "को", "ka", "का", "ki", "की", "ke", "के", "ne", "ने",
    "se", "से", "to", "from",
]

# Conversational / temporal filler words to strip if preceding a customer name
TEMPORAL_FILLERS = {
    "kal", "aaj", "parso", "कल", "आज", "परसों",
    "sun", "suno", "arre", "are", "अरे", "सुनो", "bhai", "भाई",
}

# Ambiguous conjunctions indicating multiple conflicting customers (Task 4 Rules 3 & 5)
AMBIGUOUS_CONJUNCTIONS = {"ya", "या", "or", "अथवा", "slash"}

# Self-referential / pronoun words that are NOT valid customer names (Task 4 Rule 2)
PRONOUN_WORDS = {
    "mujhe", "मुझे", "mujhko", "मुझको", "hum", "हम", "humko", "हमको", "humein", "हमें",
    "mera", "मेरा", "mere", "मेरे", "meri", "मेरी", "apne", "अपने", "apna", "अपना",
    "self", "me", "myself", "i",
}

# Currency noise words
CURRENCY_WORDS = {
    "rupaye", "rupay", "rupaya", "rs", "inr", "rupees", "rupee",
    "रुपये", "रुपए", "रुपया", "रुपीज", "रुपीज़", "रुपिज",
    "paise", "paisa", "पैसे", "पैसा",
}

# Action / grammatical noise words that must NEVER be extracted as item names
ACTION_AND_NOISE_WORDS = {
    "rupaye", "rupay", "rupaya", "rs", "inr", "rupees", "rupee",
    "रुपये", "रुपए", "रुपया", "रुपीज", "रुपीज़", "रुपिज",
    "paise", "paisa", "पैसे", "पैसा",
    "ka", "ki", "ke", "का", "की", "के", "ko", "को", "se", "से", "ne", "ने",
    "mein", "में", "hai", "है", "hain", "हैं", "tha", "था", "thi", "थी", "the", "थे",
    "aur", "और", "and", "bhi", "भी", "ya", "या", "or",
    "lene", "lena", "लेने", "लेना",
    "dene", "dena", "देने", "देना",
    "karne", "karna", "करना", "करने", "करें", "karein",
    "payment", "पेमेंट", "receive", "रिसीव",
    "kuch", "कुछ", "thoda", "थोड़ा",
    "diye", "diya", "दिए", "दिया", "liye", "liya", "लिए", "लिया",
    "mujhe", "मुझे", "mujhko", "मुझको", "hum", "हम", "humein", "हमें",
}


# ===========================================================================
# HELPER FUNCTIONS
# ===========================================================================

def _replace_devanagari_digits(text: str) -> str:
    """Convert Devanagari numerals to ASCII digits."""
    return "".join(DEVANAGARI_DIGITS.get(ch, ch) for ch in text)


def _clean_and_tokenize(text: str) -> list[str]:
    """Clean punctuation, replace devanagari digits, and split tokens."""
    t = _replace_devanagari_digits(text)
    # Replace common punctuation with spaces
    t = re.sub(r"[,।!?;:\"\']", " ", t)
    return t.strip().split()


def _is_number_token(tok: str) -> bool:
    """Check if token is a number word or digit."""
    tok_l = tok.lower()
    if tok_l in NUMBER_WORDS or tok_l in MULTIPLIER_WORDS:
        return True
    try:
        float(tok_l)
        return True
    except ValueError:
        return False


def _parse_compound_number(tokens: list[str], start_idx: int) -> tuple[Optional[float], int]:
    """Parse one or more tokens forming a compound number using additive-multiplier logic.

    Correctly computes:
      - 'ek hazaar do sau' -> 1200
      - 'do hazaar paanch sau' -> 2500
      - 'pachis sau' -> 2500
      - 'five hundred' / 'फ़ाइव हंड्रेड' -> 500
      - 'teen hazaar' -> 3000
      - 'pandrah sau' -> 1500

    Returns (value, next_idx). If no number starts at start_idx, returns (None, start_idx).
    """
    if start_idx >= len(tokens):
        return None, start_idx

    total = 0.0
    current_val: Optional[float] = None
    curr_idx = start_idx

    while curr_idx < len(tokens):
        tok = tokens[curr_idx].lower()

        # Try digit/float
        try:
            num = float(tok)
            if current_val is None:
                current_val = num
            else:
                total += current_val
                current_val = num
            curr_idx += 1
            continue
        except ValueError:
            pass

        # Try NUMBER_WORDS
        if tok in NUMBER_WORDS:
            val = NUMBER_WORDS[tok]
            if current_val is None:
                current_val = val
            elif current_val >= 100 and val < 100:
                current_val += val
            else:
                total += current_val
                current_val = val
            curr_idx += 1
            continue

        # Try MULTIPLIER_WORDS (sau, hazaar, lakh, hundred, thousand, etc.)
        if tok in MULTIPLIER_WORDS:
            mult = MULTIPLIER_WORDS[tok]
            if current_val is None:
                current_val = mult
            else:
                current_val = current_val * mult

            # When reaching thousands or higher, commit multiplier group to total
            if mult >= 1000:
                total += current_val
                current_val = None

            curr_idx += 1
            continue

        break

    if current_val is not None:
        total += current_val

    if curr_idx == start_idx:
        return None, start_idx

    return total, curr_idx


def _clean_customer_name(name_str: str) -> str:
    """Preserve casing and format customer name cleanly."""
    words = name_str.strip().split()
    cleaned = []
    for w in words:
        wl = w.lower()
        if wl in ("ji", "जी"):
            cleaned.append("ji" if wl == "ji" else "जी")
        else:
            cleaned.append(w.capitalize())
    return " ".join(cleaned)


# ===========================================================================
# MAIN PARSER
# ===========================================================================

def parse(transcript: str) -> dict[str, Any]:
    """Parse a Hinglish or Hindi transcript into structured khata fields.

    Returns:
        dict with keys:
            intent: 'entry' or 'balance_query'
            customer: str or None
            item: str or None
            item_original: str or None
            quantity: float, int, or None
            unit: str or None
            amount: float, int, or None
            kind: 'credit', 'cash', 'payment', or None
            missing: list of missing field names
    """
    raw = transcript.strip()
    norm = _replace_devanagari_digits(raw)
    norm_lower = norm.lower()

    result: dict[str, Any] = {
        "intent": "entry",
        "customer": None,
        "item": None,
        "item_original": None,
        "quantity": None,
        "unit": None,
        "amount": None,
        "kind": None,
        "missing": [],
    }

    # 1. Detect Intent: Balance Query
    for bq in BALANCE_QUERY_WORDS:
        if bq in norm_lower:
            result["intent"] = "balance_query"
            break

    # 2. Detect Kind early
    # Check multi-word phrases first
    for phrase, pkind in PAYMENT_PHRASES:
        if phrase in norm_lower:
            result["kind"] = pkind
            break

    # Regex for "ne ... diye" / "ने ... दिए" (payment received)
    if not result["kind"]:
        if re.search(r"\bne\b.+\bdiye\b", norm_lower) or re.search(r"\bने\b.+\bदिए\b", norm_lower):
            result["kind"] = "payment"

    # Tokenize
    tokens = _clean_and_tokenize(norm)

    # If kind still not detected, check single words
    if not result["kind"]:
        for t in tokens:
            tl = t.lower()
            if tl in PAYMENT_KIND_MAP:
                result["kind"] = PAYMENT_KIND_MAP[tl]
                break

    # 3. Extract Customer
    customer_tokens: list[str] = []
    remaining_tokens: list[str] = []
    marker_found = False

    # Check multi-token markers ("ke khate", "के खाते", "के खाता")
    for i in range(len(tokens)):
        if i + 1 < len(tokens):
            two_word = f"{tokens[i]} {tokens[i+1]}".lower()
            if two_word in ("ke khate", "के खाते", "के खाता"):
                customer_tokens = tokens[:i]
                remaining_tokens = tokens[i+2:]
                marker_found = True
                break

    # Check single-token markers ("ko", "का", "ne", "se", etc.)
    if not marker_found:
        for i, tok in enumerate(tokens):
            if tok.lower() in ("ko", "को", "ka", "का", "ki", "की", "ke", "के", "ne", "ने", "se", "से", "to", "from"):
                customer_tokens = tokens[:i]
                remaining_tokens = tokens[i+1:]
                marker_found = True
                break

    # Fallback: check if leading tokens before numbers/items/units/currency/payment represent customer name
    if not marker_found:
        first_non_name_idx = None
        for i, tok in enumerate(tokens):
            tl = tok.lower()
            if (
                _is_number_token(tok)
                or tl in UNIT_MAP
                or tl in ITEM_MAP
                or tl in PAYMENT_KIND_MAP
                or tl in CURRENCY_WORDS
                or tl in ("kitna", "कितना", "balance", "kuch", "कुछ")
            ):
                first_non_name_idx = i
                break

        if first_non_name_idx is not None and first_non_name_idx > 0:
            potential = [t for t in tokens[:first_non_name_idx] if t.lower() not in ("aur", "and", "और")]
            if potential:
                customer_tokens = potential
                remaining_tokens = tokens[first_non_name_idx:]
                marker_found = True

    if not marker_found:
        remaining_tokens = tokens[:]

    # Strip conversational/temporal fillers from customer tokens (e.g. "kal", "कल")
    while customer_tokens and customer_tokens[0].lower() in TEMPORAL_FILLERS:
        customer_tokens.pop(0)

    # STRICT SAFETY CHECKS ON CUSTOMER NAME (Task 4 Rules 2, 3, 5):
    # Rule 3 & 5: If customer name contains ambiguous conjunctions ("ya", "या", "or"), do NOT guess!
    is_ambiguous_customer = any(t.lower() in AMBIGUOUS_CONJUNCTIONS for t in customer_tokens)
    # Rule 2: If customer tokens only consist of pronouns ("mujhe", "मुझे", etc.), it is NOT a customer!
    is_pronoun_customer = (
        bool(customer_tokens)
        and all(t.lower() in PRONOUN_WORDS for t in customer_tokens)
    )

    if customer_tokens and not is_ambiguous_customer and not is_pronoun_customer:
        result["customer"] = _clean_customer_name(" ".join(customer_tokens))

    # If it's a balance query, we only need customer, and we're done
    if result["intent"] == "balance_query":
        if not result["customer"]:
            result["missing"].append("customer")
        return result

    # 4. Process Remaining Tokens for Quantity, Unit, Amount
    idx = 0
    parsed_numbers: list[tuple[float, int, int]] = []  # (value, start_idx, end_idx)

    while idx < len(remaining_tokens):
        val, next_idx = _parse_compound_number(remaining_tokens, idx)
        if val is not None:
            parsed_numbers.append((val, idx, next_idx))
            idx = next_idx
        else:
            idx += 1

    claimed_token_indices: set[int] = set()

    # Check each parsed number to see if followed immediately by a unit (Quantity + Unit)
    for val, start_i, end_i in parsed_numbers:
        if end_i < len(remaining_tokens):
            next_t = remaining_tokens[end_i].lower()
            if next_t in UNIT_MAP:
                result["quantity"] = int(val) if val.is_integer() else val
                result["unit"] = UNIT_MAP[next_t]
                for k in range(start_i, end_i + 1):
                    claimed_token_indices.add(k)
                continue

    # Standalone unit without preceding number
    if result["quantity"] is None:
        for i, t in enumerate(remaining_tokens):
            if i in claimed_token_indices:
                continue
            tl = t.lower()
            if tl in UNIT_MAP:
                result["unit"] = UNIT_MAP[tl]
                claimed_token_indices.add(i)
                if i > 0 and (i - 1) not in claimed_token_indices:
                    for val, s_i, e_i in parsed_numbers:
                        if e_i == i:
                            result["quantity"] = int(val) if val.is_integer() else val
                            for k in range(s_i, e_i):
                                claimed_token_indices.add(k)
                            break
                break

    # Any remaining un-claimed numbers:
    # First priority: number explicitly followed by currency words
    unclaimed_numbers = [
        (val, s_i, e_i) for val, s_i, e_i in parsed_numbers
        if not any(k in claimed_token_indices for k in range(s_i, e_i))
    ]

    for val, s_i, e_i in unclaimed_numbers:
        if e_i < len(remaining_tokens) and remaining_tokens[e_i].lower() in CURRENCY_WORDS:
            result["amount"] = int(val) if val.is_integer() else val
            for k in range(s_i, e_i + 1):
                claimed_token_indices.add(k)
            break

    # Second priority: take the remaining unclaimed number as amount
    if result["amount"] is None:
        unclaimed_numbers = [
            (val, s_i, e_i) for val, s_i, e_i in parsed_numbers
            if not any(k in claimed_token_indices for k in range(s_i, e_i))
        ]
        if unclaimed_numbers:
            val, s_i, e_i = unclaimed_numbers[-1]
            result["amount"] = int(val) if val.is_integer() else val
            for k in range(s_i, e_i):
                claimed_token_indices.add(k)

    # 5. Extract Item (Only if kind is not pure payment)
    for i, tok in enumerate(remaining_tokens):
        if i in claimed_token_indices:
            continue
        tl = tok.lower()
        if tl in ACTION_AND_NOISE_WORDS or tl in PAYMENT_KIND_MAP or tl in UNIT_MAP:
            continue
        if tl in ITEM_MAP:
            result["item"] = ITEM_MAP[tl]
            result["item_original"] = tok
            claimed_token_indices.add(i)
            break

    # If known item wasn't matched, search for unknown noun word (excluding noise and action words)
    if not result["item"] and result["kind"] != "payment":
        for i, tok in enumerate(remaining_tokens):
            if i in claimed_token_indices:
                continue
            tl = tok.lower()
            if (
                tl in ACTION_AND_NOISE_WORDS
                or tl in PAYMENT_KIND_MAP
                or tl in UNIT_MAP
                or _is_number_token(tok)
            ):
                continue
            result["item"] = tok
            result["item_original"] = tok
            claimed_token_indices.add(i)
            break

    # 6. Populate Missing Fields
    # Strict Rules (Task 4):
    # - Customer and amount are mandatory for all transactions.
    # - Kind is mandatory.
    # - For payment transactions, item, quantity, and unit are not required.
    # - For credit/cash transactions, item is required.
    if not result["customer"]:
        result["missing"].append("customer")

    if result["amount"] is None:
        result["missing"].append("amount")

    if not result["kind"]:
        result["missing"].append("kind")

    if result["kind"] != "payment":
        if not result["item"]:
            result["missing"].append("item")
        if result["quantity"] is None:
            result["missing"].append("quantity")
        if not result["unit"]:
            result["missing"].append("unit")

    return result
