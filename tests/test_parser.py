"""Tests for Hinglish/Hindi transcript parser (app/parser.py)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.parser import parse


# ---------------------------------------------------------------------------
# 5 Required Cases from SPEC.md Section 7
# ---------------------------------------------------------------------------

def test_spec_case_1_credit():
    # 1. "Sharma ji ko 5 kilo chawal, 600 rupaye, udhaar" gives Sharma ji, rice, 5 kg, 600, credit
    res = parse("Sharma ji ko 5 kilo chawal, 600 rupaye, udhaar")
    assert res["intent"] == "entry"
    assert res["customer"] == "Sharma ji"
    assert res["item"] == "rice"
    assert res["quantity"] == 5
    assert res["unit"] == "kg"
    assert res["amount"] == 600
    assert res["kind"] == "credit"
    assert "amount" not in res["missing"]
    assert "customer" not in res["missing"]


def test_spec_case_2_cash():
    # 2. "Ramesh ko dedh kilo cheeni paanch sau rupaye cash" gives Ramesh, sugar, 1.5 kg, 500, cash
    res = parse("Ramesh ko dedh kilo cheeni paanch sau rupaye cash")
    assert res["intent"] == "entry"
    assert res["customer"] == "Ramesh"
    assert res["item"] == "sugar"
    assert res["quantity"] == 1.5
    assert res["unit"] == "kg"
    assert res["amount"] == 500
    assert res["kind"] == "cash"


def test_spec_case_3_payment():
    # 3. "Sharma ji ne 300 diye" gives Sharma ji, payment, 300
    res = parse("Sharma ji ne 300 diye")
    assert res["intent"] == "entry"
    assert res["customer"] == "Sharma ji"
    assert res["kind"] == "payment"
    assert res["amount"] == 300


def test_spec_case_4_litre():
    # 4. "Gupta ji ko do litre tel, 280 udhaar" gives Gupta ji, oil, 2 litre, 280, credit
    res = parse("Gupta ji ko do litre tel, 280 udhaar")
    assert res["intent"] == "entry"
    assert res["customer"] == "Gupta ji"
    assert res["item"] == "oil"
    assert res["quantity"] == 2
    assert res["unit"] == "litre"
    assert res["amount"] == 280
    assert res["kind"] == "credit"


def test_spec_case_5_balance_query():
    # 5. "Sharma ji ka kitna baaki hai" is detected as a balance query, not an entry
    res = parse("Sharma ji ka kitna baaki hai")
    assert res["intent"] == "balance_query"
    assert res["customer"] == "Sharma ji"


# ---------------------------------------------------------------------------
# Additional Baseline Cases
# ---------------------------------------------------------------------------

def test_compound_number_pandrah_sau():
    # 'pandrah sau rupaye'
    res = parse("Suresh ko pandrah sau rupaye udhaar")
    assert res["amount"] == 1500
    assert res["customer"] == "Suresh"
    assert res["kind"] == "credit"


def test_fraction_sawa_kilo():
    # 'sawa kilo'
    res = parse("Anita ko sawa kilo cheeni 60 rupaye cash")
    assert res["customer"] == "Anita"
    assert res["quantity"] == 1.25
    assert res["unit"] == "kg"
    assert res["item"] == "sugar"
    assert res["amount"] == 60
    assert res["kind"] == "cash"


def test_name_without_ji():
    # a name without 'ji'
    res = parse("Ramesh ko 2 kilo chawal 100 rupaye udhaar")
    assert res["customer"] == "Ramesh"
    assert res["quantity"] == 2
    assert res["unit"] == "kg"
    assert res["item"] == "rice"
    assert res["amount"] == 100
    assert res["kind"] == "credit"


def test_packet_biscuit():
    # 'Sharma ji ko 2 packet biscuit 40 rupaye cash'
    res = parse("Sharma ji ko 2 packet biscuit 40 rupaye cash")
    assert res["customer"] == "Sharma ji"
    assert res["quantity"] == 2
    assert res["unit"] == "packet"
    assert res["item"] == "biscuit"
    assert res["amount"] == 40
    assert res["kind"] == "cash"


def test_missing_amount():
    # a sentence with no amount (amount must be in missing)
    res = parse("Sharma ji ko 5 kilo chawal udhaar")
    assert res["amount"] is None
    assert "amount" in res["missing"]
    assert res["customer"] == "Sharma ji"
    assert res["quantity"] == 5
    assert res["unit"] == "kg"
    assert res["item"] == "rice"
    assert res["kind"] == "credit"


def test_devanagari_sentence():
    # one Devanagari sentence
    res = parse("शर्मा जी को ५ किलो चावल ६०० रुपये उधार")
    assert res["customer"] == "शर्मा जी"
    assert res["quantity"] == 5
    assert res["unit"] == "kg"
    assert res["item"] == "rice"
    assert res["amount"] == 600
    assert res["kind"] == "credit"


# ---------------------------------------------------------------------------
# Prompt 12: Real Prisma Transcripts (Live API Test Cases)
# ---------------------------------------------------------------------------

def test_real_prisma_1_rahul_sharma():
    # Spoken: "Rahul Sharma se 500 rupaye lene hain"
    # Prisma Transcript: "राहुल शर्मा से पाँच सौ रुपये लेने हैं।"
    res = parse("राहुल शर्मा से पाँच सौ रुपये लेने हैं।")
    assert res["customer"] == "राहुल शर्मा"
    assert res["amount"] == 500
    assert res["kind"] == "payment"
    assert "customer" not in res["missing"]
    assert "amount" not in res["missing"]


def test_real_prisma_2_amit_payment():
    # Spoken: "Amit ko 1200 rupaye ka payment karna hai"
    # Prisma Transcript: "अमित को एक हज़ार दो सौ रुपये का पेमेंट करना है।"
    res = parse("अमित को एक हज़ार दो सौ रुपये का पेमेंट करना है।")
    assert res["customer"] == "अमित"
    assert res["amount"] == 1200
    assert res["kind"] == "payment"
    assert "customer" not in res["missing"]
    assert "amount" not in res["missing"]


def test_real_prisma_3_kal_mohan():
    # Spoken: "कल मोहन से दो हजार रुपये लेने हैं"
    # Prisma Transcript: "कल मोहन से दो हज़ार रुपये लेने हैं।"
    # "कल" is stripped as a temporal filler prefix
    res = parse("कल मोहन से दो हज़ार रुपये लेने हैं।")
    assert res["customer"] == "मोहन"
    assert res["amount"] == 2000
    assert res["kind"] == "payment"
    assert "customer" not in res["missing"]
    assert "amount" not in res["missing"]


def test_real_prisma_4_priya_five_hundred():
    # Spoken: "Priya ko five hundred rupees dene hain"
    # Prisma Transcript: "प्रिया को फ़ाइव हंड्रेड रुपीज़ देने हैं।"
    res = parse("प्रिया को फ़ाइव हंड्रेड रुपीज़ देने हैं।")
    assert res["customer"] == "प्रिया"
    assert res["amount"] == 500
    assert res["kind"] == "payment"
    assert "customer" not in res["missing"]
    assert "amount" not in res["missing"]


def test_real_prisma_5_ravi_receive():
    # Spoken: "Ravi se 2500 rupaye receive karne hain"
    # Prisma Transcript: "रवि से दो हज़ार पाँच सौ रुपये रिसीव करने हैं।"
    res = parse("रवि से दो हज़ार पाँच सौ रुपये रिसीव करने हैं।")
    assert res["customer"] == "रवि"
    assert res["amount"] == 2500
    assert res["kind"] == "payment"
    assert "customer" not in res["missing"]
    assert "amount" not in res["missing"]


def test_real_prisma_6_suresh_teen_hazaar():
    # Spoken: "Suresh ko teen hazaar dene hain"
    # Prisma Transcript: "सुरेश को तीन हज़ार देने हैं।"
    res = parse("सुरेश को तीन हज़ार देने हैं।")
    assert res["customer"] == "सुरेश"
    assert res["amount"] == 3000
    assert res["kind"] == "payment"
    assert "customer" not in res["missing"]
    assert "amount" not in res["missing"]


def test_real_prisma_7_rahul_ya_rohit_ambiguous():
    # Spoken: "Rahul ya Rohit se 500 rupaye lene hain"
    # Prisma Transcript: "राहुल या रोहित से पाँच सौ रुपये लेने हैं।"
    # Strict Rule 3 & 5: Ambiguous customer ("ya") must NOT guess. Keep in missing.
    res = parse("राहुल या रोहित से पाँच सौ रुपये लेने हैं।")
    assert res["customer"] is None
    assert "customer" in res["missing"]
    assert res["amount"] == 500
    assert res["kind"] == "payment"


def test_real_prisma_8_mujhe_paise_receive_no_customer_no_amount():
    # Spoken: "Mujhe paise receive karne hain"
    # Prisma Transcript: "मुझे पैसे रिसीव करने हैं।"
    # Strict Rules 1 & 2: "मुझे" is self/pronoun, no customer or amount stated.
    res = parse("मुझे पैसे रिसीव करने हैं।")
    assert res["customer"] is None
    assert "customer" in res["missing"]
    assert res["amount"] is None
    assert "amount" in res["missing"]
    assert res["kind"] == "payment"


def test_real_prisma_9_amit_kuch_paise_vague_amount():
    # Spoken: "Amit ko kuch paise dene hain"
    # Prisma Transcript: "अमित को कुछ पैसे देने हैं।"
    # Strict Rule 1: "kuch paise" is vague. Never guess amount.
    res = parse("अमित को कुछ पैसे देने हैं।")
    assert res["customer"] == "अमित"
    assert res["amount"] is None
    assert "amount" in res["missing"]
    assert res["kind"] == "payment"


def test_real_prisma_10_mohan_pachis_sau():
    # Spoken: "Mohan se pachis sau rupaye lene hain"
    # Prisma Transcript: "मोहन से पच्चीस सौ रुपये लेने हैं।"
    # "पच्चीस सौ" = 25 * 100 = 2500
    res = parse("मोहन से पच्चीस सौ रुपये लेने हैं।")
    assert res["customer"] == "मोहन"
    assert res["amount"] == 2500
    assert res["kind"] == "payment"
    assert "customer" not in res["missing"]
    assert "amount" not in res["missing"]
