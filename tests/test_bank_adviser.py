"""
Tests for the deterministic financial pre-computation layer.

The synthetic statement text below replicates the real Kreissparkasse
Göppingen PDF-text layout observed in the MCP memory uploads:
  - transaction amounts sit ALONE on their own line
  - debits carry a leading '-', credits are UNSIGNED
  - 'Kontostand am DD.MM.YYYY um HH:MM Uhr <amount>' balance lines
  - Entgeltabschluss annex repeats the fee with a TRAILING minus ('9,90-')
  - Rechnungsabschluss lines like 'Kontostand in EUR am ... 2.144,44 +'

The previous implementation only counted explicitly-signed amounts, which
made all credits (salary!) invisible and triple-counted fees — producing
a wildly negative net (-34k EUR) for an account that was actually growing.
"""
from datetime import date
from unittest.mock import patch

from assistant.banking.bank_adviser import (
    _balance_net_for_month,
    _extract_transaction_totals,
    compute_financial_aggregates,
    parse_german_amount,
)
from assistant.shared.memory_client import MemoryClient


JAN = """\
S Kreissparkasse
Göppingen

Kontoauszug 1/2026
Girokonto 1256081504, DE76 6105 0000 1256 0815 04,  Adel Haidar
Seite 1 von 8
Datum Erläuterung Betrag EUR
Kontostand am 30.12.2025 um 23:04 Uhr             2.593,06
24.01.2026 GutschriftÜberweisung / Wert: 25.01.2026
adesso SE Lohn/Gehalt 00102387/202601
            5.301,70
26.01.2026 Lastschrift
PayPal Europe S.a.r.l. et Cie S.C.A 22-24 Boulevard Royal, 2449 Luxembo urg
1050144860972/PP.6362.PP/. Netflix. com, Ihr Einkauf bei Netflix.com
              -13,99
28.01.2026 GutschriftÜberweisung
Enaam Sabboora Die Miete der Wohnung Februar 2026
            1.100,00
29.01.2026 Lastschrift
Rundfunk ARD, ZDF, DRadio Rundfunk 01.2026 - 03.2026 Beitrags nr. 247625652
              -55,08
30.01.2026 Überweisung Echtzeit / Wert: 28.01.2026
ENAAM SABBOORA Freiwillige Haushaltunterstützung DATUM 28.01.2026, 11.41
UHR
             -400,00
30.01.2026 dig.Karte (Apple Pay)
APCOA DEUTSCHLAND GMBH//STUTTGART/D E 2026-01-28T20:35 Debitk.25 2028-12
               -9,00
30.01.2026 Entgeltabrechnung
siehe Anlage Nr. 1
               -9,90
Kontostand am 30.01.2026 um 20:05 Uhr             8.506,79
Anzahl Anlagen 1
Kontoauszug 1/2026
Seite 8 von 8
Entgeltabschluss: Anlage     1
Entgelte vom 30.12.2025 bis 30.01.2026                               9,90-
Paketpreis                  1 x    9,90                9,90-
 Lastschrift               64 Stück
 Gutschrift Überweisung    15 Stück
                                                            --------------
Abrechnung 30.01.2026                                                9,90-
Es handelt sich hierbei um eine umsatzsteuerfreie Leistung.
Ab 01.01.2026 neuer Zinssatz 11,1200 v.H. für geduldete Kontoüberziehung
"""

# Quarter-end month with a Rechnungsabschluss annex (trailing '+' balances).
MAR = """\
Kontoauszug 3/2026
Girokonto 1256081504, DE76 6105 0000 1256 0815 04,  Adel Haidar
Seite 1 von 8
Datum Erläuterung Betrag EUR
Kontostand am 27.02.2026 um 20:03 Uhr             8.506,79
24.03.2026 GutschriftÜberweisung / Wert: 25.03.2026
adesso SE Lohn/Gehalt 00102387/202603
            3.301,70
26.03.2026 dig.Karte (Apple Pay)
Q1 TS Kuchen//Kuchen/DE 2026-03-25T17:44 Debitk.25 2028-12
             -102,00
31.03.2026 Entgeltabrechnung / Wert: 30.03.2026
siehe Anlage Nr. 1
               -9,90
31.03.2026 Abrechnung 31.03.2026 / Wert: 30.03.2026
siehe Anlage Nr. 2
               -0,06
Kontostand am 31.03.2026 um 20:03 Uhr            11.696,53
Anzahl Anlagen 2
Rechnungsabschluss: Anlage     2
Kontostand in EUR am 30.03.2026                                11.696,59 +
                                                            --------------
Abrechnungszeitraum vom 01.01.2026 bis 30.03.2026
Zinsen für geduldete Kontoüberziehung                                0,06-
                                                            --------------
Abrechnung 31.03.2026                                                0,06-
Kontostand/Rechnungsabschluss in EUR am 30.03.2026             11.696,53 +
"""


def test_parse_german_amount():
    assert parse_german_amount("2.593,06") == 2593.06
    assert parse_german_amount("9,90-") == 9.90
    assert parse_german_amount("11.696,53 +".rstrip()) == 11696.53


def test_credits_without_sign_are_counted_as_income():
    credits, debits = _extract_transaction_totals(JAN)
    assert credits == 5301.70 + 1100.00          # salary + rent received
    assert debits == 13.99 + 55.08 + 400.00 + 9.00 + 9.90


def test_fee_annex_and_balance_lines_are_not_transactions():
    # The 9,90 fee is booked once (Entgeltabrechnung line); the annex repeats
    # it 3x with trailing minus and must not be counted. Balance lines
    # (2.593,06 / 8.506,79) must not be counted either.
    credits, debits = _extract_transaction_totals(JAN)
    assert abs(debits - 487.97) < 0.01
    assert credits < 7000  # would be ~17k if balances were counted


def test_rechnungsabschluss_balances_excluded():
    credits, debits = _extract_transaction_totals(MAR)
    assert credits == 3301.70
    assert abs(debits - (102.00 + 9.90 + 0.06)) < 0.01


def test_balance_net_requires_genuine_opening_balance():
    # JAN: opening dated 30.12.2025 (before month) → delta available.
    assert abs(_balance_net_for_month(JAN, "2026-01") - (8506.79 - 2593.06)) < 0.01
    # MAR: opening dated 27.02.2026 → delta uses it; Rechnungsabschluss
    # balances sort between opening and closing and do not corrupt the result.
    assert abs(_balance_net_for_month(MAR, "2026-03") - (11696.53 - 8506.79)) < 0.01
    # Without any pre-month balance line the delta must be rejected.
    no_opening = MAR.replace("Kontostand am 27.02.2026 um 20:03 Uhr             8.506,79\n", "")
    assert _balance_net_for_month(no_opening, "2026-03") is None


def test_compute_financial_aggregates_multi_month():
    statement = (
        f"=== BANK STATEMENT 2026-01 ===\n{JAN}\n\n"
        f"=== BANK STATEMENT 2026-03 ===\n{MAR}"
    )
    with patch("assistant.banking.bank_adviser.date") as mock_date:
        mock_date.today.return_value = date(2026, 6, 12)
        agg = compute_financial_aggregates(statement)

    assert agg["valid"] is True
    jan_net = 8506.79 - 2593.06    # balance delta wins
    mar_net = 11696.53 - 8506.79
    assert abs(agg["monthly_nets"]["2026-01"] - jan_net) < 0.01
    assert abs(agg["monthly_nets"]["2026-03"] - mar_net) < 0.01
    assert abs(agg["savings_ytd"] - (jan_net + mar_net)) < 0.01
    assert abs(agg["net_savings_this_period"] - (jan_net + mar_net)) < 0.01
    assert agg["total_income"] == 5301.70 + 1100.00 + 3301.70
    # Sanity: a healthy positive YTD must never be reported as 'behind' by -34k.
    assert agg["savings_ytd"] > 0


# ── MemoryClient month assignment & dedup ─────────────────────────────────────

def _client() -> MemoryClient:
    return MemoryClient.__new__(MemoryClient)  # skip __init__ (no network/LLM)


def test_statement_month_from_header_beats_mentions():
    client = _client()
    item = {
        "title": "Konto_1256081504-Auszug_2026_0005.pdf (2/4)",
        "content": MAR.replace("3/2026", "5/2026"),
    }
    assert client._statement_month(item) == "2026-05"


def test_statement_month_from_title_fallback():
    client = _client()
    item = {"title": "Konto_1256081504-Auszug_2026_0005.pdf (4/4)", "content": "Hinweise zum Kontoauszug ..."}
    assert client._statement_month(item) == "2026-05"


def test_statement_mentioning_other_months_not_duplicated():
    # 'Rundfunk 01.2026 - 03.2026' in the January statement must not pull it
    # into the March bucket.
    client = _client()
    item = {"title": "Konto_1256081504-Auszug_2026_0001.pdf (1/8)", "content": JAN}
    assert client._statement_month(item) == "2026-01"
    assert client._mentions_month(item["content"], "2026-03")  # old logic would have matched


def test_dedup_collapses_reupload_suffix():
    client = _client()
    items = [
        {"id": "a", "title": "Konto_1256081504-Auszug_2025_0001.pdf (4/4)", "created_at": "2026-01-01"},
        {"id": "b", "title": "Konto_1256081504-Auszug_2025_0001_1.pdf (4/4)", "created_at": "2026-02-01"},
    ]
    deduped = client._deduplicate_by_title(items)
    assert len(deduped) == 1
    assert deduped[0]["id"] == "b"  # newest upload wins
