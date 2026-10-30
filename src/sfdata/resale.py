"""Cleaned loaders for the resale / dumped-furniture datasets.

Used by scripts/process_resale.py; mirrors the cleaning in
notebooks/03-resale-and-dumped-furniture.ipynb (keep the two in step).
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from sfdata import fetch

# Registered-business name matches that aren't resellers (reviewed by hand,
# 2026-10-30): "thrifty" car rental, a coach named Goodwill, wine bars and
# contractors named Vintage, Salvation Army housing and admin sites, banks
# matching "antique", a restaurant called The Pawn Shop, ...
NOT_RESALE = re.compile(
    r"car rental|coach|wine|elevator|contractor|construction|transatlantique|cafe|hotel|"
    r"urban development|fair trading|pawnee|vintage spoon|fog city resale|hope house|"
    r"harbor house|silvercrest|arc admin|mcfee|^the pawn shop$",
    re.I,
)
USED_GOODS_NAICS = ["459510", "453310"]  # 2022 / 2017 NAICS: used merchandise stores

SECONDHAND = re.compile(r"\bused\b|second[- ]?hand|2nd hand|antique|vintage|old clothes", re.I)

# Reports about people's belongings or encampments, not dumped furniture. Excluded from
# analysis by default (the explorer page can show them on request). Matched on status
# notes, plus anything routed to the Healthy Streets Operation Center.
ENCAMPMENT = re.compile(r"homeless|encamp|\btents?\b|sleeping|unhoused|\bcamp\b|\bhsoc\b|hot team", re.I)

# Outcome categories from Recology's free-text status notes, checked in this order
# (first match wins). "Bulky item pickup" = residents' scheduled BIR/BIC set-outs, i.e.
# not dumping at all; "Building's responsibility" = items traced to a private property
# or apartment complex that has to book (and sometimes pay for) its own pickup.
OUTCOMES = [
    ("Encampment-related", None),  # set from ENCAMPMENT / agency, below
    ("Duplicate", re.compile(r"duplicate", re.I)),
    ("Gone on arrival", re.compile(r"unable to locate|waste not found|nothing at this location|not out\b|no work needed", re.I)),
    # Before bulky pickup: these notes mention "BIC pickup" as what the building must book.
    ("Building's responsibility", re.compile(r"all items came from|needs? to call for", re.I)),
    ("Bulky item pickup", re.compile(r"\bbir\b|b i r|\bbic\b|bulky.item|recology\.com|scheduled|set out", re.I)),
    ("Building's responsibility", re.compile(r"private|personal property|housing", re.I)),
    ("No access", re.compile(r"no access|inaccessible|bed ?bugs", re.I)),
    ("Referred elsewhere", re.compile(r"reallocate|city can|\bdpw\b", re.I)),
    ("Closed, other", re.compile(r"administrative closure|invalid|insufficient information", re.I)),
    ("Picked up", re.compile(r"case resolved|resolved|done|sweep|debris", re.I)),
]
OUTCOME_NAMES = list(dict.fromkeys(name for name, _ in OUTCOMES)) + ["Closed, no note", "Open"]

# Recology stopped writing free-text status notes on cases closed from this date on: only
# "unable to locate" and "duplicate" (structured statuses) still appear. Every finer outcome,
# and the encampment flag, can only be read from cases closed before it.
NOTES_STOPPED = pd.Timestamp("2026-08-27")

RESPONSE_BINS = [0, 1, 4, 24, float("inf")]
RESPONSE_LABELS = ["under 1 h", "1–4 h", "4–24 h", "over 1 day"]


def outcome_category(note: str, encampment: bool, status: str) -> str:
    if encampment:
        return "Encampment-related"
    if status == "Open":
        return "Open"
    for name, pattern in OUTCOMES[1:]:
        if pattern.search(note):
            return name
    return "Closed, no note" if not note.strip() else "Closed, other"


def dumped_reports(refresh: bool = False) -> pd.DataFrame:
    """311 furniture/mattress reports with parsed times and a normalized outcome."""
    df = fetch.load("dumped_furniture_311", refresh=refresh)
    df = df[df["source"] != "Test"].copy()
    df["requested"] = pd.to_datetime(df["requested_datetime"])
    df["closed"] = pd.to_datetime(df["closed_date"])
    # Status notes mix "Case Resolved" / "case_resolved" spellings; normalize.
    df["outcome"] = (
        df["status_notes"].fillna("").str.lower().str.replace("_", " ")
        .str.strip(" -").str.split(" - ").str[0].replace("", "(no note)")
    )
    notes = df["status_notes"].fillna("").str.replace("_", " ")
    df["encampment"] = notes.str.contains(ENCAMPMENT) | df["agency_responsible"].fillna("").str.contains(
        "Healthy Streets", case=False
    )
    df["outcome_cat"] = [
        outcome_category(n, e, s)
        for n, e, s in zip(notes, df["encampment"], df["status_description"])
    ]
    hours = (df["closed"] - df["requested"]).dt.total_seconds() / 3600
    df["hours_to_close"] = hours.where(hours >= 0)  # a handful close "before" they open
    df["has_notes_era"] = df["closed"] < NOTES_STOPPED
    df["response"] = pd.cut(df["hours_to_close"], RESPONSE_BINS, right=False, labels=RESPONSE_LABELS)
    return df


def used_goods_shops(refresh: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(shops, excluded): open used-goods businesses in SF, and name matches dropped."""
    biz = fetch.load("used_goods_businesses", refresh=refresh)
    biz["naics"] = biz["self_reported_naics_code"].astype("Int64").astype(str)
    biz["rule"] = np.where(biz["naics"].isin(USED_GOODS_NAICS), "naics", "name")
    excluded = biz[(biz.rule == "name") & biz.dba_name.str.contains(NOT_RESALE)]
    shops = biz.drop(excluded.index)
    # No neighborhood = mailing-only or outside SF.
    shops = shops[shops.neighborhoods_analysis_boundaries.notna()].copy()
    xy = shops["location"].str.extract(r"POINT \(([-\d.]+) ([-\d.]+)\)").astype(float)
    shops["lon"], shops["lat"] = xy[0], xy[1]
    return shops, excluded


def street_vendors(refresh: bool = False) -> pd.DataFrame:
    """Active street-vending permits, flagged where the goods described are second-hand."""
    vend = fetch.load("street_vending_permits", refresh=refresh)
    vend["secondhand"] = vend["describewhatyouwillsell"].fillna("").str.contains(SECONDHAND)
    return vend


def relative_by_calendar_day(requested: pd.Series) -> pd.Series:
    """Reports per occurrence of each day-of-month, relative to the average day.

    Normalizes for day 31 existing in only some months (and 29-30 not in February).
    """
    days = pd.date_range(requested.min().normalize(), requested.max().normalize())
    occurrences = pd.Series(days.day).value_counts().sort_index()
    per_day = requested.dt.day.value_counts().sort_index() / occurrences
    return per_day / per_day.mean()
