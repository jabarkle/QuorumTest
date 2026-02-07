#!/usr/bin/env python3
"""
Quorum API Client - Fetches solicitations from partner's Quorum platform.
Maps partner's pre-processed solicitation data to our internal AggregatedRFP format.
"""

import os
import requests
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

DEFAULT_API_URL = os.getenv(
    "QUORUM_API_URL",
    "https://rca4xjkfei6v6dph5sfetpnv3u0nnbak.lambda-url.us-east-1.on.aws/"
)


def fetch_solicitations(api_url: str = None) -> List[Dict[str, Any]]:
    """
    Fetch solicitations from the partner's Quorum API.

    Returns a list of raw solicitation dicts. Handles both single-object
    and list responses from the API.
    """
    url = api_url or DEFAULT_API_URL
    print(f"  Fetching solicitations from: {url}")

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    data = response.json()

    # Handle different response shapes
    if isinstance(data, list):
        # Unwrap if each item has a "solicitation" wrapper
        solicitations = []
        for item in data:
            if isinstance(item, dict) and "solicitation" in item:
                solicitations.append(item["solicitation"])
            else:
                solicitations.append(item)
        return solicitations
    elif isinstance(data, dict):
        if "solicitation" in data:
            return [data["solicitation"]]
        return [data]

    return []


def map_to_aggregated_rfp(sol: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map a partner solicitation object to our AggregatedRFP format.
    """
    scope = sol.get("scope_of_work") or {}
    project = sol.get("project") or {}
    dates = sol.get("important_dates") or {}
    compliance = sol.get("compliance_requirements") or {}
    contacts = sol.get("contacts") or {}
    clauses = sol.get("applicable_clauses") or {}
    attachments = sol.get("attachments") or {}

    # --- NAICS ---
    naics_codes = []
    naics_code = sol.get("naics_code")
    if naics_code:
        naics_codes.append(str(naics_code))

    # --- Set-asides ---
    set_asides = _extract_set_asides(sol)

    # --- Deadline ---
    deadline = (
        dates.get("proposal_due_date")
        or dates.get("response_date")
        or sol.get("deadline")
    )

    # --- Period of performance ---
    pop = project.get("period_of_performance") or sol.get("period_of_performance")

    # --- Key tasks ---
    key_tasks = scope.get("key_items") or []

    # --- Requirements (from contractor responsibilities + scope) ---
    all_requirements = []
    for resp in (scope.get("contractor_responsibilities") or []):
        all_requirements.append({
            "text": resp,
            "source_document": "API - Scope of Work",
            "type": "mandatory"
        })

    # --- Certifications & clearances ---
    certs, clearances = _extract_certs_and_clearances(compliance, sol)

    # --- Evaluation criteria (from clauses + compliance) ---
    eval_criteria = []
    for clause in (clauses.get("far_clauses") or []):
        if "215" in clause or "evaluation" in clause.lower():
            eval_criteria.append(clause)

    # --- Documents analyzed (from attachments) ---
    docs_analyzed = []
    for doc_type, filename in attachments.items():
        label = doc_type.replace("_", " ").title()
        docs_analyzed.append(f"{filename} ({label})")

    # --- Build the aggregated RFP ---
    return {
        "rfp_id": sol.get("solicitation_number") or sol.get("id", "Unknown"),
        "agency": sol.get("agency"),
        "title": sol.get("title"),
        "naics_codes": naics_codes,
        "set_asides": set_asides,
        "contract_value": sol.get("contract_type"),
        "period_of_performance": pop,
        "deadline": deadline,
        "all_requirements": all_requirements,
        "certifications_required": certs,
        "clearances_required": clearances,
        "key_tasks": key_tasks,
        "evaluation_criteria": eval_criteria,
        "documents_analyzed": docs_analyzed,
        "primary_document": _pick_primary_document(attachments),
        # Extra fields from partner data (used by dashboard)
        "solicitation_number": sol.get("solicitation_number"),
        "notice_type": sol.get("notice_type"),
        "posted_date": sol.get("posted_date"),
        "original_url": sol.get("original_url"),
        "naics_description": sol.get("naics_description"),
        "set_aside_percentage": sol.get("set_aside_percentage"),
        "size_standard": sol.get("size_standard"),
        "scope_summary": scope.get("summary"),
        "contacts": contacts,
        "important_dates": dates,
        "compliance_requirements": compliance,
    }


def _extract_set_asides(sol: Dict[str, Any]) -> List[str]:
    """Derive set-aside types from partner data."""
    set_asides = []
    if sol.get("small_business_set_aside"):
        competition = (sol.get("project") or {}).get("competition_type", "")
        if competition:
            set_asides.append(competition)
        else:
            set_asides.append("Small Business Set-Aside")
    else:
        set_asides.append("Full and Open")
    return set_asides


def _extract_certs_and_clearances(
    compliance: Dict[str, Any], sol: Dict[str, Any]
) -> tuple[List[str], List[str]]:
    """Extract certifications and clearances from compliance data."""
    certs = []
    clearances = []

    for key, value in compliance.items():
        if not isinstance(value, str):
            continue
        val_lower = value.lower()
        if "clearance" in val_lower or "secret" in val_lower:
            clearances.append(value)
        if "certified" in val_lower or "license" in val_lower:
            certs.append(value)

    return certs, clearances


def _pick_primary_document(attachments: Dict[str, str]) -> Optional[str]:
    """Pick the primary document from attachments by priority."""
    priority = [
        "performance_work_statement",
        "statement_of_work",
        "main_solicitation",
    ]
    for key in priority:
        if key in attachments:
            return attachments[key]

    # Return first attachment if none match priority
    if attachments:
        return next(iter(attachments.values()))
    return None
