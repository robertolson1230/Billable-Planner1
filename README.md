# packing_assistant

A Python 3.11 command-line packing checklist generator that uses Open-Meteo weather forecasts.

## Features
- Collects trip inputs interactively:
  - destination city
  - start/end dates (YYYY-MM-DD)
  - travel type (`navy`, `work`, `personal`)
  - workout plan (`none`, `light`, `regular`)
  - laundry and carry-on preferences
  - international flag (for travel adapter suggestion)
  - transportation mode (`flying`, `driving`)
- Fetches location + daily forecast from Open-Meteo (no API key required).
- Builds a packing checklist with quantities based on:
  - trip length
  - weather conditions
  - travel type
  - workout plan
  - laundry / carry-on constraints
- Includes a smart **Electronics & Cords** section.
- Uses markdown checkboxes with explicit quantity display for each item.
- Lets you add your own custom items and quantities to any packing section.
- Lets you provide custom approximate weight + bulk for new items and whether they are carry-on essential.
- Creates a bag plan from smallest to largest bag (transport-aware):
  - personal item
  - carry-on
  - one or more checked bags (23kg max each)
- Tries to keep important items in carry-on and avoids exceeding each bag's weight and bulk capacity.
- Flying mode intentionally packs lighter; driving mode allows more flexibility and larger bag capacities.
- Prints results to console and writes Markdown output under `./output`.
- Handles invalid dates/city and network failures with fallback to continue without weather.

## Project structure
- `packing_assistant.py` - CLI entry point
- `weather.py` - Open-Meteo geocoding + forecast fetch/parsing
- `rules.py` - packing logic/rules, recommendation logic, and bag planning heuristics
- `output/` - generated markdown files
- `requirements.txt`

## Setup
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run
```bash
python3.11 packing_assistant.py
```

## Notes
- Forecast availability depends on Open-Meteo coverage and date window.
- If weather fetch fails, the app offers to proceed without weather data.
- Weight/bulk values are best-effort estimates to help with planning, not exact baggage measurements.
