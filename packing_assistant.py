"""CLI entrypoint for packing_assistant."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Dict, List, Tuple

from rules import (
    ItemEstimate,
    TripProfile,
    build_packing_list,
    build_recommendations,
    estimate_item,
    format_trip_snapshot,
    plan_bags,
)
from weather import WeatherBundle, WeatherError, get_weather_bundle

OUTPUT_DIR = Path("output")


def prompt_non_empty(prompt: str) -> str:
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("Input cannot be empty. Please try again.")


def prompt_date(prompt: str) -> date:
    while True:
        raw = input(prompt).strip()
        try:
            return date.fromisoformat(raw)
        except ValueError:
            print("Invalid date format. Use YYYY-MM-DD.")


def prompt_choice(prompt: str, choices: tuple[str, ...]) -> str:
    allowed = {c.lower() for c in choices}
    while True:
        value = input(prompt).strip().lower()
        if value in allowed:
            return value
        print(f"Invalid choice. Expected one of: {', '.join(choices)}")


def prompt_yes_no(prompt: str) -> bool:
    return prompt_choice(prompt, ("yes", "no")) == "yes"


def prompt_positive_int(prompt: str) -> int:
    while True:
        raw = input(prompt).strip()
        try:
            value = int(raw)
            if value > 0:
                return value
        except ValueError:
            pass
        print("Please enter a positive whole number.")


def prompt_positive_float_or_default(prompt: str, default: float) -> float:
    while True:
        raw = input(prompt).strip()
        if raw == "":
            return default
        try:
            value = float(raw)
            if value > 0:
                return value
        except ValueError:
            pass
        print("Please enter a positive number (or press Enter to accept default).")


def add_custom_items(
    packing_sections: Dict[str, List[Tuple[str, int]]],
) -> Dict[str, ItemEstimate]:
    custom_estimates: Dict[str, ItemEstimate] = {}
    add_items = prompt_yes_no("Would you like to add your own custom items? (yes/no): ")
    if not add_items:
        return custom_estimates

    print("\nAdd custom items. Choose a section, then enter item name + quantity.")
    section_names = list(packing_sections.keys())
    while True:
        print("\nAvailable sections:")
        for index, section in enumerate(section_names, start=1):
            print(f"  {index}. {section}")
        print("  done. Finish adding custom items")

        selection = input("Select section number or type 'done': ").strip().lower()
        if selection == "done":
            break

        if not selection.isdigit() or not (1 <= int(selection) <= len(section_names)):
            print("Invalid selection.")
            continue

        selected_section = section_names[int(selection) - 1]
        item_name = prompt_non_empty(f"Item name for {selected_section}: ")
        qty = prompt_positive_int("Quantity needed: ")

        default_estimate = estimate_item(item_name, selected_section)
        print(
            f"Default estimate for '{item_name}': {default_estimate.weight_kg:.2f}kg each, "
            f"{default_estimate.bulk_l:.2f}L each."
        )
        est_weight = prompt_positive_float_or_default("Approx weight per item in kg (Enter for default): ", default_estimate.weight_kg)
        est_bulk = prompt_positive_float_or_default("Approx bulk/space per item in liters (Enter for default): ", default_estimate.bulk_l)
        est_essential = prompt_yes_no("Is this item essential for carry-on? (yes/no): ")

        custom_estimates[item_name.lower()] = ItemEstimate(est_weight, est_bulk, est_essential)

        existing_items = {name.lower(): (idx, current_qty) for idx, (name, current_qty) in enumerate(packing_sections[selected_section])}
        item_key = item_name.lower()
        if item_key in existing_items:
            idx, current_qty = existing_items[item_key]
            packing_sections[selected_section][idx] = (packing_sections[selected_section][idx][0], current_qty + qty)
            print(f"Updated {item_name} to quantity {current_qty + qty}.")
        else:
            packing_sections[selected_section].append((item_name, qty))
            print(f"Added {item_name} x{qty} to {selected_section}.")

        packing_sections[selected_section] = sorted(packing_sections[selected_section])

    return custom_estimates


def render_checklist(
    packing_sections: Dict[str, List[Tuple[str, int]]],
    snapshot: Dict[str, str],
    recommendations: List[str],
    weather_bundle: WeatherBundle | None,
    bag_summary: List[Dict[str, object]],
    item_to_bag: Dict[str, str],
) -> str:
    lines = []
    lines.append("# Packing Checklist")
    lines.append("")

    lines.append("## Trip Snapshot")
    for key, value in snapshot.items():
        lines.append(f"- **{key}:** {value}")
    lines.append("")

    if weather_bundle and weather_bundle.daily:
        lines.append("## Daily Weather Forecast")
        for day in weather_bundle.daily:
            lines.append(
                f"- {day.forecast_date.isoformat()}: "
                f"{day.temp_min_c:.1f}°C to {day.temp_max_c:.1f}°C, "
                f"precip {day.precipitation_mm:.1f} mm, wind {day.wind_max_kmh:.1f} km/h"
            )
        lines.append("")

    lines.append("## Extra Recommendations")
    for tip in recommendations:
        lines.append(f"- {tip}")
    lines.append("")

    lines.append("## Bag Plan (smallest to largest)")
    for bag in bag_summary:
        lines.append(
            f"### {bag['name']} - {bag['weight']}kg/{bag['max_weight']}kg, {bag['bulk']}L/{bag['max_bulk']}L"
        )
        bag_items: List[Tuple[str, int]] = bag["items"]  # type: ignore[assignment]
        if not bag_items:
            lines.append("- (empty)")
        else:
            for item, qty in bag_items:
                lines.append(f"- {item} x{qty}")
        lines.append("")

    for section, items in packing_sections.items():
        lines.append(f"## {section}")
        if not items:
            lines.append("- (none)")
        else:
            for item, qty in items:
                bag = item_to_bag.get(item.lower(), "Unassigned")
                lines.append(f"- [ ] {item} (**Qty: {qty}**, **Bag: {bag}**)" )
        lines.append("")

    lines.append("---")
    lines.append("Generated by packing_assistant")
    return "\n".join(lines)


def save_markdown(content: str, destination_city: str, start_date: date, end_date: date) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    safe_city = "".join(ch for ch in destination_city.lower().replace(" ", "-") if ch.isalnum() or ch == "-")
    file_path = OUTPUT_DIR / f"packing-list-{safe_city}-{start_date.isoformat()}-to-{end_date.isoformat()}.md"
    file_path.write_text(content, encoding="utf-8")
    return file_path


def collect_inputs() -> tuple[str, date, date, str, str, bool, bool, bool, str]:
    destination = prompt_non_empty("Destination city: ")
    start_date = prompt_date("Start date (YYYY-MM-DD): ")
    end_date = prompt_date("End date (YYYY-MM-DD): ")

    while end_date < start_date:
        print("End date cannot be before start date.")
        end_date = prompt_date("End date (YYYY-MM-DD): ")

    travel_type = prompt_choice("Travel type (navy/work/personal): ", ("navy", "work", "personal"))
    workout_plan = prompt_choice("Workout plan (none/light/regular): ", ("none", "light", "regular"))
    laundry_access = prompt_yes_no("Laundry access? (yes/no): ")
    carry_on_only = prompt_yes_no("Carry-on only? (yes/no): ")
    international = prompt_yes_no("International trip? (yes/no): ")
    transport_mode = prompt_choice("Transportation mode (flying/driving): ", ("flying", "driving"))

    return destination, start_date, end_date, travel_type, workout_plan, laundry_access, carry_on_only, international, transport_mode


def main() -> None:
    print("\n=== packing_assistant ===")
    destination, start_date, end_date, travel_type, workout_plan, laundry_access, carry_on_only, international, transport_mode = collect_inputs()

    weather_bundle: WeatherBundle | None = None
    try:
        weather_bundle = get_weather_bundle(destination, start_date, end_date)
        print(
            f"Weather fetched for {weather_bundle.location.name}, {weather_bundle.location.country} "
            f"({len(weather_bundle.daily)} day(s))."
        )
    except WeatherError as exc:
        print(f"Weather fetch failed: {exc}")
        proceed = prompt_yes_no("Proceed without weather data? (yes/no): ")
        if not proceed:
            print("Exiting without generating checklist.")
            return

    profile = TripProfile(
        destination_city=destination,
        destination_country=weather_bundle.location.country if weather_bundle else None,
        start_date=start_date,
        end_date=end_date,
        travel_type=travel_type,
        workout_plan=workout_plan,
        laundry_access=laundry_access,
        carry_on_only=carry_on_only,
        is_international=international,
        transport_mode=transport_mode,
    )

    daily_weather = weather_bundle.daily if weather_bundle else None
    sections = build_packing_list(profile, daily_weather)
    custom_estimates = add_custom_items(sections)

    snapshot = format_trip_snapshot(profile, daily_weather)
    recommendations = build_recommendations(profile, daily_weather)
    bag_summary, item_to_bag = plan_bags(sections, custom_estimates, profile.transport_mode)
    markdown = render_checklist(sections, snapshot, recommendations, weather_bundle, bag_summary, item_to_bag)

    print("\n" + markdown)
    output_path = save_markdown(markdown, destination, start_date, end_date)
    print(f"\nChecklist saved to: {output_path}")


if __name__ == "__main__":
    main()
