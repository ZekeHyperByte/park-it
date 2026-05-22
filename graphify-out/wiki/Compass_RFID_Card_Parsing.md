# Compass RFID Card Parsing

> 24 nodes · cohesion 0.12

## Key Concepts

- **parse_stat()** (18 connections) — `protocols/compass/parser.py`
- **TestParseStat** (10 connections) — `protocols/tests/test_compass_parser.py`
- **_extract_wiegand()** (4 connections) — `protocols/compass/parser.py`
- **parser.py** (4 connections) — `protocols/compass/parser.py`
- **parse_rfid_card()** (3 connections) — `protocols/compass/parser.py`
- **.test_empty_response()** (3 connections) — `protocols/tests/test_compass_parser.py`
- **.test_multiple_inputs()** (3 connections) — `protocols/tests/test_compass_parser.py`
- **.test_stat10_format()** (3 connections) — `protocols/tests/test_compass_parser.py`
- **.test_stat1_format()** (3 connections) — `protocols/tests/test_compass_parser.py`
- **.test_wiegand_w()** (3 connections) — `protocols/tests/test_compass_parser.py`
- **.test_wiegand_x()** (3 connections) — `protocols/tests/test_compass_parser.py`
- **.test_in1_on()** (2 connections) — `protocols/tests/test_compass_parser.py`
- **.test_in2_on()** (2 connections) — `protocols/tests/test_compass_parser.py`
- **Compass controller STAT response parser.  Parses controller responses to extract** (1 connections) — `protocols/compass/parser.py`
- **Extract RFID/UHF card number from response.      Returns:         Tuple of (card** (1 connections) — `protocols/compass/parser.py`
- **Parse a controller response — STAT binary or RSS push event.      Args:** (1 connections) — `protocols/compass/parser.py`
- **Extract card number from Wiegand channel.      Args:         text: Decoded contr** (1 connections) — `protocols/compass/parser.py`
- **Empty response has no inputs.** (1 connections) — `protocols/tests/test_compass_parser.py`
- **Parse Wiegand W (RFID) card.** (1 connections) — `protocols/tests/test_compass_parser.py`
- **Parse Wiegand X (UHF) card.** (1 connections) — `protocols/tests/test_compass_parser.py`
- **Multiple inputs active.** (1 connections) — `protocols/tests/test_compass_parser.py`
- **STAT1 format for IN2.** (1 connections) — `protocols/tests/test_compass_parser.py`
- **STAT10 format for IN1.** (1 connections) — `protocols/tests/test_compass_parser.py`
- **Test STAT response parser.** (1 connections) — `protocols/tests/test_compass_parser.py`

## Relationships

- No strong cross-community connections detected

## Source Files

- `protocols/compass/parser.py`
- `protocols/tests/test_compass_parser.py`

## Audit Trail

- EXTRACTED: 49 (68%)
- INFERRED: 23 (32%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*