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
