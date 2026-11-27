"""Deadline risk: will the remaining work fit before each deadline?

For every open task, demand is all remaining work due on or before its
deadline (earlier deadlines are done first). Capacity is the free study time
until the deadline, scaled by this week's pace (the share of planned chunks
the student really finished). A logistic curve turns demand / capacity into
a probability: half the time needed -> ~5%, exactly enough -> 50%, 1.5x -> ~95%.
"""

import math
from dataclasses import dataclass
from datetime import date

STEEPNESS = 6.0
MIN_PACE = 0.2  # one bad week should not make every deadline look lost


@dataclass
class RiskItem:
    id: int
    title: str
    course: str
    deadline: date
    remaining_minutes: float
    started: bool


@dataclass
class Capacity:
    minutes: float  # free study minutes until the deadline
    days: int  # days with any free time until the deadline


@dataclass
class RiskResult:
    work_item_id: int
    title: str
    course: str
    deadline: date
    remaining_minutes: int
    available_minutes: int
    probability: float
    level: str  # "low" | "medium" | "high"
    suggestion: str


def miss_probability(demand: float, capacity: float) -> float:
    if demand <= 0:
        return 0.0
    if capacity <= 0:
        return 1.0
    return 1 / (1 + math.exp(-STEEPNESS * (demand / capacity - 1)))


def risk_level(probability: float) -> str:
    if probability < 0.3:
        return "low"
    if probability < 0.6:
        return "medium"
    return "high"


def suggestion(item: RiskItem, level: str, demand: float, capacity: Capacity, chunk_minutes: int) -> str:
    if capacity.days == 0 or demand > capacity.minutes:
        return "Δεν φτάνει ο χρόνος. Πρόσθεσε ώρες μελέτης ή ζήτησε παράταση από τον διδάσκοντα ή τη Μονάδα Προσβασιμότητας."
    per_day = demand / capacity.days
    minutes = max(chunk_minutes, math.ceil(per_day / chunk_minutes) * chunk_minutes)
    if level == "low":
        return "Είσαι εντάξει. Συνέχισε όπως πας."
    if not item.started:
        return f"Ξεκίνα σήμερα {minutes} λεπτά."
    return f"Κάνε {minutes} λεπτά κάθε μέρα μέχρι την προθεσμία."


def assess(
    items: list[RiskItem],
    capacity_until,  # callable: deadline -> Capacity
    pace: float,
    chunk_minutes: int,
) -> list[RiskResult]:
    pace = max(MIN_PACE, min(1.0, pace))
    results = []
    demand = 0.0
    for item in sorted(items, key=lambda i: i.deadline):
        demand += item.remaining_minutes
        cap = capacity_until(item.deadline)
        effective = cap.minutes * pace
        probability = miss_probability(demand, effective)
        level = risk_level(probability)
        results.append(
            RiskResult(
                work_item_id=item.id,
                title=item.title,
                course=item.course,
                deadline=item.deadline,
                remaining_minutes=round(item.remaining_minutes),
                available_minutes=round(effective),
                probability=round(probability, 2),
                level=level,
                suggestion=suggestion(item, level, demand, Capacity(effective, cap.days), chunk_minutes),
            )
        )
    return results
