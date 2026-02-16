"""Packing rules for packing assistant."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from math import ceil
from typing import Dict, Iterable, List, Tuple

from weather import DailyWeather


@dataclass
class TripProfile:
    destination_city: str
    destination_country: str | None
    start_date: date
    end_date: date
    travel_type: str
    workout_plan: str
    laundry_access: bool
    carry_on_only: bool
    is_international: bool
    transport_mode: str


@dataclass
class ItemEstimate:
    weight_kg: float
    bulk_l: float
    essential: bool


@dataclass
class BagConfig:
    name: str
    max_weight_kg: float
    max_bulk_l: float


def trip_days(start_date: date, end_date: date) -> int:
    return (end_date - start_date).days + 1


def _infer_climate(weather: Iterable[DailyWeather]) -> str:
    days = list(weather)
    if not days:
        return "mild"

    avg_high = sum(d.temp_max_c for d in days) / len(days)
    avg_low = sum(d.temp_min_c for d in days) / len(days)

    if avg_high >= 28:
        return "hot"
    if avg_low <= 5:
        return "cold"
    return "mild"


def _rainy_days(weather: Iterable[DailyWeather]) -> int:
    return sum(1 for d in weather if d.precipitation_mm >= 1.0)


def _base_outfit_count(days: int, laundry_access: bool, carry_on_only: bool, transport_mode: str) -> int:
    if laundry_access:
        count = min(days, 5)
    else:
        count = days
    if carry_on_only:
        count = min(count, 5)
    if transport_mode == "flying":
        count = min(count, max(2, days - 1))
    elif transport_mode == "driving":
        count = min(days + 1, count + 1)
    return max(count, 2)


def _add(counter: Counter[str], item: str, qty: int) -> None:
    if qty > 0:
        counter[item] += qty


def build_packing_list(profile: TripProfile, weather: List[DailyWeather] | None) -> Dict[str, List[Tuple[str, int]]]:
    days = trip_days(profile.start_date, profile.end_date)
    outfits = _base_outfit_count(days, profile.laundry_access, profile.carry_on_only, profile.transport_mode)

    climate = _infer_climate(weather or [])
    rainy_days = _rainy_days(weather or [])

    clothing = Counter()
    toiletries = Counter()
    travel_docs = Counter()
    workout = Counter()
    electronics = Counter()
    misc = Counter()

    _add(clothing, "Underwear", min(days + 1, outfits + 2 if profile.laundry_access else days + 1))
    _add(clothing, "Socks", min(days + 1, outfits + 2 if profile.laundry_access else days + 1))
    _add(clothing, "T-shirts / Tops", outfits)
    _add(clothing, "Pants / Bottoms", max(2, ceil(outfits / 2)))
    _add(clothing, "Sleepwear", 1)

    if climate == "hot":
        _add(clothing, "Shorts", max(1, ceil(outfits / 2)))
        _add(clothing, "Breathable shirt", 2)
    elif climate == "cold":
        _add(clothing, "Sweater / Fleece", 2)
        _add(clothing, "Warm jacket", 1)
        _add(clothing, "Thermal layer", 2)
    else:
        _add(clothing, "Light jacket", 1)

    if rainy_days > 0:
        _add(clothing, "Rain jacket", 1)
        _add(clothing, "Compact umbrella", 1)

    if profile.travel_type == "work":
        _add(clothing, "Business outfits", min(days, outfits))
        _add(clothing, "Dress shoes", 1)
    elif profile.travel_type == "navy":
        _add(clothing, "Uniform sets", min(days, outfits))
        _add(clothing, "Boots", 1)
    else:
        _add(clothing, "Casual outfit", min(days, outfits))

    _add(toiletries, "Toothbrush", 1)
    _add(toiletries, "Toothpaste", 1)
    _add(toiletries, "Deodorant", 1)
    _add(toiletries, "Shampoo / Soap", 1)
    _add(toiletries, "Medications", 1)

    _add(travel_docs, "ID / Passport", 1)
    _add(travel_docs, "Tickets / Boarding passes", 1)
    _add(travel_docs, "Payment cards + cash", 1)

    if profile.workout_plan == "light":
        _add(workout, "Workout tops", 2)
        _add(workout, "Workout bottoms", 2)
        _add(workout, "Athletic shoes", 1)
    elif profile.workout_plan == "regular":
        _add(workout, "Workout tops", 3)
        _add(workout, "Workout bottoms", 3)
        _add(workout, "Athletic shoes", 1)
        _add(workout, "Recovery band / mobility tool", 1)

    _add(electronics, "Phone", 1)
    _add(electronics, "Phone charger", 1)
    _add(electronics, "Laptop", 1 if profile.travel_type in {"work", "navy"} else 0)
    _add(electronics, "Laptop charger", 1 if profile.travel_type in {"work", "navy"} else 0)
    _add(electronics, "Watch", 1)
    _add(electronics, "Watch charger", 1)
    _add(electronics, "Headphones / Earbuds", 1)
    _add(electronics, "Power bank", 1)
    _add(electronics, "Charging cable organizer", 1)
    if profile.is_international:
        _add(electronics, "Travel adapter", 1)

    if profile.carry_on_only:
        _add(misc, "3-1-1 liquids bag", 1)
    _add(misc, "Reusable water bottle", 1)
    _add(misc, "Snacks", 1)
    _add(misc, "Laundry bag", 1)

    return {
        "Clothing": sorted(clothing.items()),
        "Workout Gear": sorted(workout.items()),
        "Toiletries": sorted(toiletries.items()),
        "Electronics & Cords": sorted(electronics.items()),
        "Travel Docs": sorted(travel_docs.items()),
        "Miscellaneous": sorted(misc.items()),
    }


def format_trip_snapshot(profile: TripProfile, weather: List[DailyWeather] | None) -> Dict[str, str]:
    days = trip_days(profile.start_date, profile.end_date)
    climate = _infer_climate(weather or [])
    rainy = _rainy_days(weather or [])
    return {
        "Destination": f"{profile.destination_city}" + (f", {profile.destination_country}" if profile.destination_country else ""),
        "Dates": f"{profile.start_date.isoformat()} to {profile.end_date.isoformat()} ({days} days)",
        "Travel Type": profile.travel_type,
        "Workout Plan": profile.workout_plan,
        "Laundry Access": "yes" if profile.laundry_access else "no",
        "Carry-on Only": "yes" if profile.carry_on_only else "no",
        "International": "yes" if profile.is_international else "no",
        "Transportation": profile.transport_mode,
        "Weather Summary": "Unavailable" if not weather else f"{climate} with {rainy} rainy day(s)",
    }


def build_recommendations(profile: TripProfile, weather: List[DailyWeather] | None) -> List[str]:
    recommendations: List[str] = []
    days = trip_days(profile.start_date, profile.end_date)
    rainy_days = _rainy_days(weather or [])
    climate = _infer_climate(weather or [])

    if days >= 7:
        recommendations.append("Plan one mid-trip laundry cycle to reduce overpacking.")
    if profile.carry_on_only:
        recommendations.append("Use packing cubes and roll clothes to maximize carry-on space.")
    if profile.transport_mode == "flying":
        recommendations.append("Favor versatile layers and re-wearable outfits for lighter packing.")
    if profile.transport_mode == "driving":
        recommendations.append("Use trunk space for non-essentials but keep daily-use items in carry-on.")
    if rainy_days >= 2:
        recommendations.append("Pack waterproof footwear if you'll be walking a lot.")
    if climate == "cold":
        recommendations.append("Wear your bulkiest layers during travel to save bag space.")
    if climate == "hot":
        recommendations.append("Bring sunscreen and prioritize breathable fabrics.")
    if profile.travel_type == "work":
        recommendations.append("Keep one business outfit wrinkle-safe in a garment folder.")
    if profile.workout_plan != "none":
        recommendations.append("Pack one quick-dry towel for workouts and recovery.")
    if profile.is_international:
        recommendations.append("Download offline maps and store a photo of travel documents.")

    if not recommendations:
        recommendations.append("Check your airline baggage rules before packing.")

    return recommendations


def estimate_item(item_name: str, section: str, custom_estimates: Dict[str, ItemEstimate] | None = None) -> ItemEstimate:
    key = item_name.strip().lower()
    if custom_estimates and key in custom_estimates:
        return custom_estimates[key]

    catalog: Dict[str, ItemEstimate] = {
        "underwear": ItemEstimate(0.08, 0.35, False),
        "socks": ItemEstimate(0.05, 0.25, False),
        "t-shirts / tops": ItemEstimate(0.2, 1.0, False),
        "pants / bottoms": ItemEstimate(0.5, 2.0, False),
        "dress shoes": ItemEstimate(1.2, 8.0, False),
        "boots": ItemEstimate(1.8, 10.0, False),
        "athletic shoes": ItemEstimate(1.0, 7.0, False),
        "toothbrush": ItemEstimate(0.03, 0.1, False),
        "toothpaste": ItemEstimate(0.12, 0.2, False),
        "medications": ItemEstimate(0.1, 0.2, True),
        "phone": ItemEstimate(0.2, 0.2, True),
        "phone charger": ItemEstimate(0.12, 0.2, True),
        "laptop": ItemEstimate(1.7, 3.0, True),
        "laptop charger": ItemEstimate(0.3, 0.5, True),
        "watch": ItemEstimate(0.06, 0.1, True),
        "watch charger": ItemEstimate(0.07, 0.1, True),
        "headphones / earbuds": ItemEstimate(0.25, 0.7, True),
        "power bank": ItemEstimate(0.35, 0.5, True),
        "charging cable organizer": ItemEstimate(0.2, 0.7, False),
        "travel adapter": ItemEstimate(0.2, 0.3, True),
        "id / passport": ItemEstimate(0.05, 0.05, True),
        "tickets / boarding passes": ItemEstimate(0.02, 0.05, True),
        "payment cards + cash": ItemEstimate(0.05, 0.05, True),
    }
    if key in catalog:
        return catalog[key]

    if section == "Clothing":
        return ItemEstimate(0.4, 1.8, False)
    if section == "Workout Gear":
        return ItemEstimate(0.5, 2.5, False)
    if section == "Toiletries":
        return ItemEstimate(0.15, 0.3, False)
    if section == "Electronics & Cords":
        return ItemEstimate(0.25, 0.5, True)
    if section == "Travel Docs":
        return ItemEstimate(0.03, 0.05, True)
    return ItemEstimate(0.2, 0.6, False)


def plan_bags(
    packing_sections: Dict[str, List[Tuple[str, int]]],
    custom_estimates: Dict[str, ItemEstimate] | None = None,
    transport_mode: str = "flying",
) -> Tuple[List[Dict[str, object]], Dict[str, str]]:
    if transport_mode == "driving":
        bag_sequence = [
            BagConfig("Personal Item", 6.0, 20.0),
            BagConfig("Carry-on", 14.0, 55.0),
        ]
        checked_limit_kg = 27.0
        checked_bulk_l = 120.0
    else:
        bag_sequence = [
            BagConfig("Personal Item", 5.0, 18.0),
            BagConfig("Carry-on", 10.0, 40.0),
        ]
        checked_limit_kg = 23.0
        checked_bulk_l = 90.0

    bags: List[Dict[str, object]] = [
        {"name": bag_sequence[0].name, "max_weight": bag_sequence[0].max_weight_kg, "max_bulk": bag_sequence[0].max_bulk_l, "weight": 0.0, "bulk": 0.0, "items": []},
        {"name": bag_sequence[1].name, "max_weight": bag_sequence[1].max_weight_kg, "max_bulk": bag_sequence[1].max_bulk_l, "weight": 0.0, "bulk": 0.0, "items": []},
    ]

    item_to_bag: Dict[str, str] = {}

    def add_checked_bag() -> Dict[str, object]:
        index = sum(1 for b in bags if str(b["name"]).startswith("Checked Bag")) + 1
        bag = {
            "name": f"Checked Bag {index}",
            "max_weight": checked_limit_kg,
            "max_bulk": checked_bulk_l,
            "weight": 0.0,
            "bulk": 0.0,
            "items": [],
        }
        bags.append(bag)
        return bag

    def place_units(section: str, item_name: str, qty: int, estimate: ItemEstimate) -> None:
        target_order = [bags[1], bags[0]] if estimate.essential or section in {"Travel Docs", "Electronics & Cords"} else bags

        for _ in range(qty):
            placed = False
            for bag in target_order:
                if bag["weight"] + estimate.weight_kg <= bag["max_weight"] and bag["bulk"] + estimate.bulk_l <= bag["max_bulk"]:
                    bag["weight"] += estimate.weight_kg
                    bag["bulk"] += estimate.bulk_l
                    bag["items"].append((section, item_name, estimate.weight_kg, estimate.bulk_l))
                    item_to_bag[item_name.lower()] = str(bag["name"])
                    placed = True
                    break
            if not placed:
                checked = add_checked_bag()
                checked["weight"] += estimate.weight_kg
                checked["bulk"] += estimate.bulk_l
                checked["items"].append((section, item_name, estimate.weight_kg, estimate.bulk_l))
                item_to_bag[item_name.lower()] = str(checked["name"])
                target_order = [bags[1], bags[0], *[b for b in bags if str(b["name"]).startswith("Checked Bag")]]

    essentials_first: List[Tuple[str, str, int, ItemEstimate]] = []
    regular: List[Tuple[str, str, int, ItemEstimate]] = []

    for section, items in packing_sections.items():
        for item_name, qty in items:
            estimate = estimate_item(item_name, section, custom_estimates)
            entry = (section, item_name, qty, estimate)
            if estimate.essential or section in {"Travel Docs", "Electronics & Cords"}:
                essentials_first.append(entry)
            else:
                regular.append(entry)

    for section, item_name, qty, estimate in essentials_first + regular:
        place_units(section, item_name, qty, estimate)

    summarized_bags: List[Dict[str, object]] = []
    for bag in bags:
        grouped: Counter[str] = Counter()
        for _, item_name, _, _ in bag["items"]:
            grouped[item_name] += 1
        summarized_bags.append(
            {
                "name": bag["name"],
                "weight": round(float(bag["weight"]), 2),
                "max_weight": bag["max_weight"],
                "bulk": round(float(bag["bulk"]), 2),
                "max_bulk": bag["max_bulk"],
                "items": sorted(grouped.items()),
            }
        )

    return summarized_bags, item_to_bag
