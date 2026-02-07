#!/usr/bin/env python3
"""
Quorum Phase 2: Intelligent Triage - Secondary Filter
Fetches pre-processed solicitations from partner API and scores against firm capabilities.
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, TypedDict, Optional
from datetime import datetime
from dotenv import load_dotenv

from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

from api_client import fetch_solicitations, map_to_aggregated_rfp

# Load environment variables
load_dotenv()


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class AggregatedRFP(BaseModel):
    """Aggregated information for a single solicitation."""
    rfp_id: str = Field(..., description="Solicitation number or ID")
    agency: Optional[str] = Field(None)
    title: Optional[str] = Field(None)
    naics_codes: List[str] = Field(default_factory=list)
    set_asides: List[str] = Field(default_factory=list)
    contract_value: Optional[str] = Field(None)
    period_of_performance: Optional[str] = Field(None)
    deadline: Optional[str] = Field(None)
    all_requirements: List[Dict[str, str]] = Field(default_factory=list)
    certifications_required: List[str] = Field(default_factory=list)
    clearances_required: List[str] = Field(default_factory=list)
    key_tasks: List[str] = Field(default_factory=list)
    evaluation_criteria: List[str] = Field(default_factory=list)
    documents_analyzed: List[str] = Field(default_factory=list)
    primary_document: Optional[str] = Field(None)


class TriageReport(BaseModel):
    """The final triage report output."""
    rfp_id: str = Field(..., description="Solicitation identifier")
    rfp_title: Optional[str] = Field(None)
    agency: Optional[str] = Field(None)
    match_score: int = Field(..., ge=0, le=100, description="Overall fit score (0-100)")
    recommendation: str = Field(..., description="GO, NO-GO, or CONDITIONAL")
    knockouts: List[Dict[str, str]] = Field(default_factory=list)
    strong_matches: List[Dict[str, str]] = Field(default_factory=list)
    gaps: List[Dict[str, str]] = Field(default_factory=list)
    naics_match: bool = Field(False)
    set_aside_eligible: bool = Field(True)
    technical_summary: str = Field(...)
    recommended_personnel: List[str] = Field(default_factory=list)
    documents_analyzed: List[str] = Field(default_factory=list)
    analysis_timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    # New fields from partner API
    solicitation_number: Optional[str] = Field(None)
    deadline: Optional[str] = Field(None)
    original_url: Optional[str] = Field(None)
    posted_date: Optional[str] = Field(None)


# ============================================================================
# LANGGRAPH STATE SCHEMA
# ============================================================================

class TriageState(TypedDict):
    """State that flows through the LangGraph nodes."""
    # Input
    firm_data_path: str
    api_url: str

    # Fetched solicitations (list of mapped AggregatedRFP dicts)
    solicitations: List[Dict[str, Any]]

    # Current solicitation being scored
    aggregated_rfp: Dict[str, Any]

    # Firm Data
    firm_capabilities: Dict[str, Any]

    # Analysis
    knockouts: List[Dict[str, str]]
    matches: List[Dict[str, str]]
    gaps: List[Dict[str, str]]

    # Final Output
    final_report: Dict[str, Any]


# ============================================================================
# NODE 1: FETCHER (replaces Scanner + Extractor + Aggregator)
# ============================================================================

def node_fetcher(state: TriageState) -> TriageState:
    """
    Node 1: Fetch solicitations from partner API and map to internal format.
    Replaces the old Scanner -> Extractor -> Aggregator pipeline.
    """
    print("[1/2] FETCHER - Retrieving solicitations from partner API...")

    raw_solicitations = fetch_solicitations(state.get("api_url"))
    print(f"  Retrieved {len(raw_solicitations)} solicitation(s)")

    mapped = []
    for sol in raw_solicitations:
        aggregated = map_to_aggregated_rfp(sol)
        mapped.append(aggregated)
        print(f"  Mapped: {aggregated.get('rfp_id')} - {aggregated.get('title', 'No title')}")

    state["solicitations"] = mapped
    return state


# ============================================================================
# NODE 2: SCORER
# ============================================================================

def node_scorer(state: TriageState) -> TriageState:
    """
    Node 2: Score the aggregated RFP against firm capabilities.
    Generate final triage report with recommendation.
    """
    print("\n[2/2] SCORER - Evaluating firm fit...")

    # Load firm data
    with open(state["firm_data_path"], 'r') as f:
        firm_data = json.load(f)

    state["firm_capabilities"] = firm_data
    aggregated = state["aggregated_rfp"]

    # === PROGRAMMATIC CHECKS ===
    knockouts = []
    matches = []
    gaps = []

    # 1. NAICS Code Check
    firm_naics = set(firm_data.get("firm_metadata", {}).get("naics_codes", []))
    rfp_naics = set(aggregated.get("naics_codes", []))
    naics_match = bool(firm_naics & rfp_naics) if rfp_naics else True

    if rfp_naics and not naics_match:
        knockouts.append({
            "type": "NAICS Mismatch",
            "reason": f"RFP requires NAICS {', '.join(rfp_naics)}. Firm has {', '.join(firm_naics)}.",
            "severity": "HIGH"
        })
    elif naics_match and rfp_naics:
        matching_naics = firm_naics & rfp_naics
        matches.append({
            "type": "NAICS Match",
            "detail": f"Firm NAICS codes match: {', '.join(matching_naics)}"
        })

    # 2. Set-Aside Check
    firm_business_types = firm_data.get("firm_metadata", {}).get("business_type", [])
    rfp_set_asides = aggregated.get("set_asides", [])
    set_aside_eligible = True

    set_aside_mapping = {
        "WOSB": ["Woman Owned Small Business (WOSB)", "WOSB"],
        "SDB": ["Small Disadvantaged Business (SDB)", "SDB"],
        "8(a)": ["8(a)"],
        "Minority": ["Minority Owned Business", "Minority Owned"],
        "Small Business": ["Small Business", "Small Business Set-Aside", "Competitive Small Business Set Aside"]
    }

    for sa in rfp_set_asides:
        if sa in ["Full and Open", "Unrestricted"]:
            continue
        matched = False
        for key, values in set_aside_mapping.items():
            if sa in values or any(v in sa for v in values):
                if any(bt in firm_business_types or any(v in bt for v in values) for bt in firm_business_types):
                    matched = True
                    matches.append({
                        "type": "Set-Aside Eligible",
                        "detail": f"Firm qualifies for {sa} set-aside"
                    })
                    break
        if not matched and sa not in ["Full and Open", "Unrestricted", ""]:
            if any(x in sa.upper() for x in ["SDVOSB", "HUBZONE", "8(A)"]) and not any(x in str(firm_business_types).upper() for x in ["SDVOSB", "HUBZONE", "8(A)"]):
                knockouts.append({
                    "type": "Set-Aside Ineligible",
                    "reason": f"RFP requires {sa} set-aside. Firm does not qualify.",
                    "severity": "HIGH"
                })
                set_aside_eligible = False

    # 3. Clearance Check
    rfp_clearances = aggregated.get("clearances_required", [])
    firm_clearance = firm_data.get("firm_metadata", {}).get("clearance_level", "None")

    for clearance in rfp_clearances:
        if clearance and "secret" in clearance.lower():
            if "secret" not in firm_clearance.lower() and "top secret" not in firm_clearance.lower():
                knockouts.append({
                    "type": "Clearance Gap",
                    "reason": f"RFP requires {clearance}. Firm clearance: {firm_clearance}",
                    "severity": "HIGH"
                })

    # === LLM-BASED ANALYSIS ===
    llm = ChatAnthropic(
        model="claude-3-haiku-20240307",
        temperature=0,
        max_tokens=4096
    )

    req_summary = aggregated.get("all_requirements", [])[:30]

    # Include scope summary from partner data for richer context
    scope_context = aggregated.get("scope_summary", "") or ""

    analysis_prompt = f"""Analyze the fit between this RFP and our firm's capabilities.

RFP INFORMATION:
- Agency: {aggregated.get('agency', 'Unknown')}
- Title: {aggregated.get('title', 'Unknown')}
- Scope Summary: {scope_context}
- Key Tasks: {json.dumps(aggregated.get('key_tasks', []), indent=2)}
- Certifications Required: {json.dumps(aggregated.get('certifications_required', []))}
- Evaluation Criteria: {json.dumps(aggregated.get('evaluation_criteria', []))}
- Sample Requirements: {json.dumps(req_summary, indent=2)}

OUR FIRM'S CAPABILITIES:
- Core Competencies: {json.dumps(firm_data.get('capabilities', {}).get('core_competencies', []))}
- Specialized Expertise: {json.dumps(firm_data.get('capabilities', {}).get('specialized_expertise', []))}
- Past Performance: {json.dumps([pp.get('relevance_points', []) for pp in firm_data.get('past_performance', [])])}
- Key Personnel Expertise: {json.dumps([p.get('expertise', '') for p in firm_data.get('key_personnel', [])])}

ALREADY IDENTIFIED:
- Knockouts: {json.dumps(knockouts)}
- Matches: {json.dumps(matches)}

Analyze and return JSON:
{{
    "additional_matches": [
        {{"type": "category", "detail": "specific match with evidence"}}
    ],
    "gaps": [
        {{"type": "category", "detail": "gap description", "mitigation": "possible solution"}}
    ],
    "technical_summary": "3-4 sentence assessment of overall fit",
    "recommended_personnel": ["names of team members well-suited for this work"],
    "score_adjustment": "number from -20 to +20 based on technical fit beyond NAICS/set-aside"
}}

Be specific. Reference actual capabilities and requirements."""

    messages = [
        SystemMessage(content="You are a capture manager evaluating bid opportunities. Be honest about gaps but also identify genuine strengths."),
        HumanMessage(content=analysis_prompt)
    ]

    response = llm.invoke(messages)

    try:
        analysis = json.loads(response.content)
    except json.JSONDecodeError:
        import re
        json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
        if json_match:
            analysis = json.loads(json_match.group())
        else:
            analysis = {"additional_matches": [], "gaps": [], "technical_summary": "Analysis failed", "recommended_personnel": [], "score_adjustment": 0}

    # Merge LLM findings
    matches.extend(analysis.get("additional_matches", []))
    gaps.extend(analysis.get("gaps", []))

    # === CALCULATE SCORE ===
    base_score = 70
    knockout_penalty = len(knockouts) * 30
    match_bonus = min(len(matches) * 5, 25)
    gap_penalty = min(len(gaps) * 5, 15)
    llm_adjustment = int(analysis.get("score_adjustment", 0))
    llm_adjustment = max(-20, min(20, llm_adjustment))

    final_score = base_score - knockout_penalty + match_bonus - gap_penalty + llm_adjustment
    final_score = max(0, min(100, final_score))

    # Determine recommendation
    if knockouts:
        recommendation = "NO-GO"
    elif final_score >= 70:
        recommendation = "GO"
    elif final_score >= 45:
        recommendation = "CONDITIONAL"
    else:
        recommendation = "NO-GO"

    # Build final report
    report = TriageReport(
        rfp_id=aggregated["rfp_id"],
        rfp_title=aggregated.get("title"),
        agency=aggregated.get("agency"),
        match_score=final_score,
        recommendation=recommendation,
        knockouts=knockouts,
        strong_matches=matches,
        gaps=gaps,
        naics_match=naics_match,
        set_aside_eligible=set_aside_eligible,
        technical_summary=analysis.get("technical_summary", ""),
        recommended_personnel=analysis.get("recommended_personnel", []),
        documents_analyzed=aggregated.get("documents_analyzed", []),
        solicitation_number=aggregated.get("solicitation_number"),
        deadline=aggregated.get("deadline"),
        original_url=aggregated.get("original_url"),
        posted_date=aggregated.get("posted_date"),
    )

    state["final_report"] = report.model_dump()
    state["knockouts"] = knockouts
    state["matches"] = matches
    state["gaps"] = gaps

    print(f"  Match Score: {final_score}/100")
    print(f"  Recommendation: {recommendation}")
    print(f"  Knockouts: {len(knockouts)}")
    print(f"  Strong Matches: {len(matches)}")

    return state


# ============================================================================
# LANGGRAPH WORKFLOW
# ============================================================================

def create_triage_workflow() -> StateGraph:
    """Create the LangGraph state machine workflow (Fetcher -> Scorer)."""
    workflow = StateGraph(TriageState)

    workflow.add_node("fetcher", node_fetcher)
    workflow.add_node("scorer", node_scorer)

    workflow.set_entry_point("fetcher")
    workflow.add_edge("fetcher", "scorer")
    workflow.add_edge("scorer", END)

    return workflow.compile()


# ============================================================================
# MAIN PROCESSING FUNCTION
# ============================================================================

def process_solicitation(aggregated_rfp: Dict[str, Any], firm_data_path: Path, output_dir: Path) -> Dict[str, Any]:
    """
    Score a single solicitation against firm capabilities.
    Uses only the scorer node (data already mapped from API).
    """
    llm_workflow = StateGraph(TriageState)
    llm_workflow.add_node("scorer", node_scorer)
    llm_workflow.set_entry_point("scorer")
    llm_workflow.add_edge("scorer", END)
    compiled = llm_workflow.compile()

    initial_state: TriageState = {
        "firm_data_path": str(firm_data_path),
        "api_url": "",
        "solicitations": [],
        "aggregated_rfp": aggregated_rfp,
        "firm_capabilities": {},
        "knockouts": [],
        "matches": [],
        "gaps": [],
        "final_report": {}
    }

    final_state = compiled.invoke(initial_state)

    # Save report
    report = final_state["final_report"]
    safe_id = report.get("rfp_id", "unknown").replace("/", "_").replace("\\", "_")
    output_path = output_dir / f"triage_report_{safe_id}.json"
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)

    return report


def process_all_from_api(firm_data_path: Path, output_dir: Path, api_url: str = None) -> List[Dict[str, Any]]:
    """
    Fetch all solicitations from partner API and score each one.
    """
    output_dir.mkdir(exist_ok=True)

    # Fetch and map solicitations
    print(f"\n{'='*70}")
    print("QUORUM TRIAGE - Fetching from Partner API")
    print(f"{'='*70}\n")

    raw_solicitations = fetch_solicitations(api_url)

    if not raw_solicitations:
        print("No solicitations found from API.")
        return []

    solicitations = [map_to_aggregated_rfp(sol) for sol in raw_solicitations]
    print(f"Retrieved {len(solicitations)} solicitation(s)\n")

    reports = []

    for idx, aggregated in enumerate(solicitations, 1):
        print(f"\n{'='*70}")
        print(f"[{idx}/{len(solicitations)}] Scoring: {aggregated.get('title', 'Unknown')}")
        print(f"  Agency: {aggregated.get('agency', 'Unknown')}")
        print(f"  NAICS: {', '.join(aggregated.get('naics_codes', []))}")
        print(f"{'='*70}")

        try:
            report = process_solicitation(aggregated, firm_data_path, output_dir)
            reports.append(report)
        except Exception as e:
            print(f"ERROR scoring {aggregated.get('rfp_id')}: {str(e)}")
            import traceback
            traceback.print_exc()
            reports.append({
                "rfp_id": aggregated.get("rfp_id", "Unknown"),
                "match_score": 0,
                "recommendation": "ERROR",
                "error": str(e)
            })

    # Save summary
    summary_path = output_dir / "triage_summary.json"
    summary = {
        "processed_at": datetime.now().isoformat(),
        "source": "partner_api",
        "total_rfps": len(reports),
        "results": [
            {
                "rfp_id": r.get("rfp_id"),
                "score": r.get("match_score", 0),
                "recommendation": r.get("recommendation", "ERROR"),
                "knockouts": len(r.get("knockouts", [])),
                "agency": r.get("agency")
            }
            for r in reports
        ]
    }

    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)

    # Print summary
    print(f"\n{'='*70}")
    print("TRIAGE SUMMARY")
    print(f"{'='*70}\n")
    print(f"{'RFP':<30} {'SCORE':<10} {'RECOMMENDATION':<15} {'KNOCKOUTS':<10}")
    print("-" * 70)

    for r in reports:
        score = r.get("match_score", 0)
        rec = r.get("recommendation", "ERROR")
        kos = len(r.get("knockouts", []))
        rfp_id = r.get('rfp_id', 'Unknown')
        # Truncate long IDs for display
        display_id = rfp_id[:28] if len(rfp_id) > 28 else rfp_id
        print(f"{display_id:<30} {score:<10} {rec:<15} {kos:<10}")

    print(f"\nReports saved to: {output_dir}")

    return reports


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

def main():
    """Main CLI entry point."""
    base_dir = Path(__file__).parent.parent
    firm_data_path = base_dir / "Input" / "My Firm" / "Firm Data.json"
    output_dir = base_dir / "output_reports"

    if not firm_data_path.exists():
        print(f"ERROR: Firm data not found at {firm_data_path}")
        sys.exit(1)

    api_url = os.getenv("QUORUM_API_URL")
    process_all_from_api(firm_data_path, output_dir, api_url)


if __name__ == "__main__":
    main()
