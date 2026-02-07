#!/usr/bin/env python3
"""
Quorum Dashboard - RFP Triage Visualization
A professional Streamlit dashboard for reviewing RFP triage results.
"""

import json
import streamlit as st
from pathlib import Path
from datetime import datetime
import subprocess
import sys

# Page configuration - must be first Streamlit command
st.set_page_config(
    page_title="Quorum - RFP Triage",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CUSTOM STYLING
# ============================================================================

st.markdown("""
<style>
    /* Main theme colors */
    :root {
        --primary-color: #1e3a5f;
        --secondary-color: #3d5a80;
        --accent-color: #ee6c4d;
        --success-color: #2d6a4f;
        --warning-color: #e9c46a;
        --danger-color: #9b2226;
        --bg-color: #f8f9fa;
        --card-bg: #ffffff;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #1e3a5f 0%, #3d5a80 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        color: white;
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 2.2rem;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    
    .main-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
        font-size: 1rem;
    }
    
    /* Score cards */
    .score-card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-left: 4px solid;
        margin-bottom: 1rem;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .score-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 16px rgba(0,0,0,0.12);
    }
    
    .score-go { border-left-color: #2d6a4f; }
    .score-conditional { border-left-color: #e9c46a; }
    .score-nogo { border-left-color: #9b2226; }
    
    /* Recommendation badges */
    .badge {
        display: inline-block;
        padding: 0.35rem 0.8rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .badge-go { background: #d8f3dc; color: #2d6a4f; }
    .badge-conditional { background: #fff3cd; color: #856404; }
    .badge-nogo { background: #f8d7da; color: #721c24; }
    
    /* Metrics */
    .metric-container {
        background: white;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1e3a5f;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #6c757d;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Detail sections */
    .detail-section {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 1rem 1.2rem;
        margin-bottom: 1rem;
    }
    
    .detail-section h4 {
        margin: 0 0 0.8rem 0;
        color: #1e3a5f;
        font-size: 1rem;
        font-weight: 600;
    }
    
    /* Knockout items */
    .knockout-item {
        background: #fff5f5;
        border-left: 3px solid #9b2226;
        padding: 0.8rem 1rem;
        margin-bottom: 0.5rem;
        border-radius: 0 8px 8px 0;
    }
    
    /* Match items */
    .match-item {
        background: #f0fdf4;
        border-left: 3px solid #2d6a4f;
        padding: 0.8rem 1rem;
        margin-bottom: 0.5rem;
        border-radius: 0 8px 8px 0;
    }
    
    /* Gap items */
    .gap-item {
        background: #fffbeb;
        border-left: 3px solid #d97706;
        padding: 0.8rem 1rem;
        margin-bottom: 0.5rem;
        border-radius: 0 8px 8px 0;
    }
    
    /* Sidebar styling */
    .sidebar .sidebar-content {
        background: #f8f9fa;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #1e3a5f 0%, #3d5a80 100%);
        color: white;
        border: none;
        padding: 0.6rem 1.5rem;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(30, 58, 95, 0.3);
    }
    
    /* Progress bar colors */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #2d6a4f, #40916c);
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_base_paths():
    """Get base paths for the application."""
    base_dir = Path(__file__).parent.parent
    return {
        "base": base_dir,
        "firm_data": base_dir / "Input" / "My Firm" / "Firm Data.json",
        "output": base_dir / "output_reports"
    }


def load_firm_data(firm_path: Path) -> dict:
    """Load firm data from JSON file."""
    if firm_path.exists():
        with open(firm_path, 'r') as f:
            return json.load(f)
    return {}


def load_triage_reports(output_dir: Path) -> list:
    """Load all triage reports from output directory."""
    reports = []
    if output_dir.exists():
        for report_file in output_dir.glob("triage_report_*.json"):
            try:
                with open(report_file, 'r') as f:
                    report = json.load(f)
                    report["_file_path"] = str(report_file)
                    reports.append(report)
            except Exception as e:
                st.error(f"Error loading {report_file.name}: {e}")
    return reports


def load_summary(output_dir: Path) -> dict:
    """Load triage summary if it exists."""
    summary_path = output_dir / "triage_summary.json"
    if summary_path.exists():
        with open(summary_path, 'r') as f:
            return json.load(f)
    return {}


def get_recommendation_badge(recommendation: str) -> str:
    """Get HTML badge for recommendation."""
    badge_class = {
        "GO": "badge-go",
        "CONDITIONAL": "badge-conditional",
        "NO-GO": "badge-nogo",
        "ERROR": "badge-nogo"
    }.get(recommendation, "badge-nogo")
    
    return f'<span class="badge {badge_class}">{recommendation}</span>'


def get_score_color(score: int) -> str:
    """Get color based on score."""
    if score >= 70:
        return "#2d6a4f"
    elif score >= 45:
        return "#d97706"
    else:
        return "#9b2226"


def run_triage_analysis():
    """Run the triage analysis by fetching from partner API."""
    paths = get_base_paths()

    try:
        from triage_check import process_all_from_api
        import os

        api_url = os.getenv("QUORUM_API_URL")

        with st.spinner("Fetching solicitations from partner API and scoring..."):
            reports = process_all_from_api(
                paths["firm_data"],
                paths["output"],
                api_url
            )

        return True, len(reports)
    except Exception as e:
        return False, str(e)


# ============================================================================
# SIDEBAR
# ============================================================================

def render_sidebar():
    """Render the sidebar with firm info and controls."""
    paths = get_base_paths()
    firm_data = load_firm_data(paths["firm_data"])
    
    with st.sidebar:
        st.markdown("### 🏢 Firm Profile")
        
        firm_name = firm_data.get("firm_metadata", {}).get("name", "Not Configured")
        st.markdown(f"**{firm_name}**")
        
        # Business types
        business_types = firm_data.get("firm_metadata", {}).get("business_type", [])
        if business_types:
            for bt in business_types[:3]:
                st.markdown(f"• {bt}")
        
        st.markdown("---")
        
        # NAICS Codes
        naics = firm_data.get("firm_metadata", {}).get("naics_codes", [])
        if naics:
            st.markdown("**NAICS Codes:**")
            st.code(", ".join(naics[:4]))
        
        st.markdown("---")
        
        # Core competencies preview
        competencies = firm_data.get("capabilities", {}).get("core_competencies", [])
        if competencies:
            st.markdown("**Core Competencies:**")
            for comp in competencies[:5]:
                st.markdown(f"• {comp}")
            if len(competencies) > 5:
                st.markdown(f"*...and {len(competencies) - 5} more*")
        
        st.markdown("---")
        
        # Action buttons
        st.markdown("### ⚙️ Actions")
        
        if st.button("🔄 Fetch & Score from API", use_container_width=True):
            success, result = run_triage_analysis()
            if success:
                st.success(f"Scored {result} solicitation(s)")
                st.rerun()
            else:
                st.error(f"Error: {result}")

        if st.button("🗑️ Clear Results", use_container_width=True):
            output_dir = paths["output"]
            if output_dir.exists():
                for f in output_dir.glob("*.json"):
                    f.unlink()
                st.success("Results cleared")
                st.rerun()

        st.markdown("---")
        st.markdown("**API Source:**")
        import os
        api_url = os.getenv("QUORUM_API_URL", "Not configured")
        st.code(api_url[:50] + "..." if len(api_url) > 50 else api_url)


# ============================================================================
# MAIN CONTENT
# ============================================================================

def render_header():
    """Render the main header."""
    st.markdown("""
    <div class="main-header">
        <h1>📋 Quorum RFP Triage</h1>
        <p>Intelligent Government Contract Opportunity Analysis</p>
    </div>
    """, unsafe_allow_html=True)


def render_metrics(reports: list):
    """Render summary metrics."""
    total = len(reports)
    go_count = sum(1 for r in reports if r.get("recommendation") == "GO")
    conditional_count = sum(1 for r in reports if r.get("recommendation") == "CONDITIONAL")
    nogo_count = sum(1 for r in reports if r.get("recommendation") in ["NO-GO", "ERROR"])
    avg_score = sum(r.get("match_score", 0) for r in reports) / total if total > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-value">{total}</div>
            <div class="metric-label">RFPs Analyzed</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-value" style="color: #2d6a4f;">{go_count}</div>
            <div class="metric-label">Recommended</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-value" style="color: #d97706;">{conditional_count}</div>
            <div class="metric-label">Conditional</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-value" style="color: #9b2226;">{nogo_count}</div>
            <div class="metric-label">Not Recommended</div>
        </div>
        """, unsafe_allow_html=True)


def render_rfp_card(report: dict, expanded: bool = False):
    """Render a single RFP result card."""
    rfp_id = report.get("rfp_id", "Unknown")
    score = report.get("match_score", 0)
    recommendation = report.get("recommendation", "ERROR")
    agency = report.get("agency", "Agency not identified")
    title = report.get("rfp_title", "Title not available")
    knockouts = report.get("knockouts", [])
    matches = report.get("strong_matches", [])
    gaps = report.get("gaps", [])
    technical_summary = report.get("technical_summary", "")
    personnel = report.get("recommended_personnel", [])
    documents = report.get("documents_analyzed", [])
    
    # Card styling based on recommendation
    card_class = {
        "GO": "score-go",
        "CONDITIONAL": "score-conditional",
        "NO-GO": "score-nogo",
        "ERROR": "score-nogo"
    }.get(recommendation, "score-nogo")
    
    with st.expander(f"**{rfp_id}** — Score: {score}/100 | {recommendation}", expanded=expanded):
        # Header row
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.markdown(f"**Agency:** {agency}")
            if title:
                st.markdown(f"**Title:** {title}")
            sol_num = report.get("solicitation_number")
            if sol_num:
                st.markdown(f"**Solicitation #:** {sol_num}")
            deadline_val = report.get("deadline")
            if deadline_val:
                st.markdown(f"**Deadline:** {deadline_val}")
            posted = report.get("posted_date")
            if posted:
                st.markdown(f"**Posted:** {posted}")
            sam_url = report.get("original_url")
            if sam_url:
                st.markdown(f"[View on SAM.gov]({sam_url})")
        
        with col2:
            score_color = get_score_color(score)
            st.markdown(f"""
            <div style="text-align: center;">
                <div style="font-size: 2.5rem; font-weight: 700; color: {score_color};">{score}</div>
                <div style="font-size: 0.8rem; color: #6c757d;">MATCH SCORE</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div style="text-align: center; padding-top: 0.5rem;">
                {get_recommendation_badge(recommendation)}
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Technical Summary
        if technical_summary:
            st.markdown("#### 📝 Technical Assessment")
            st.info(technical_summary)
        
        # Knockouts (if any)
        if knockouts:
            st.markdown("#### ⛔ Knockout Disqualifiers")
            for ko in knockouts:
                if isinstance(ko, dict):
                    st.markdown(f"""
                    <div class="knockout-item">
                        <strong>{ko.get('type', 'Issue')}:</strong> {ko.get('reason', ko.get('detail', str(ko)))}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="knockout-item">{ko}</div>
                    """, unsafe_allow_html=True)
        
        # Two columns for matches and gaps
        col_match, col_gap = st.columns(2)
        
        with col_match:
            if matches:
                st.markdown("#### ✅ Strong Matches")
                for match in matches[:5]:
                    if isinstance(match, dict):
                        st.markdown(f"""
                        <div class="match-item">
                            <strong>{match.get('type', 'Match')}:</strong> {match.get('detail', str(match))}
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="match-item">{match}</div>
                        """, unsafe_allow_html=True)
        
        with col_gap:
            if gaps:
                st.markdown("#### ⚠️ Capability Gaps")
                for gap in gaps[:5]:
                    if isinstance(gap, dict):
                        mitigation = gap.get('mitigation', '')
                        st.markdown(f"""
                        <div class="gap-item">
                            <strong>{gap.get('type', 'Gap')}:</strong> {gap.get('detail', str(gap))}
                            {f'<br><em>Mitigation: {mitigation}</em>' if mitigation else ''}
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="gap-item">{gap}</div>
                        """, unsafe_allow_html=True)
        
        # Recommended Personnel
        if personnel:
            st.markdown("#### 👥 Recommended Team")
            st.markdown(", ".join(personnel))
        
        # Documents analyzed
        if documents:
            with st.expander("📄 Documents Analyzed"):
                for doc in documents:
                    st.markdown(f"• {doc}")


def render_empty_state():
    """Render empty state when no reports exist."""
    st.markdown("""
    <div style="text-align: center; padding: 4rem 2rem; background: #f8f9fa; border-radius: 12px; margin: 2rem 0;">
        <div style="font-size: 4rem; margin-bottom: 1rem;">📋</div>
        <h3 style="color: #1e3a5f; margin-bottom: 0.5rem;">No Triage Results Yet</h3>
        <p style="color: #6c757d; margin-bottom: 1.5rem;">
            Click "Fetch & Score from API" in the sidebar to pull solicitations from the partner platform and score them against your firm's capabilities.
        </p>
    </div>
    """, unsafe_allow_html=True)

    import os
    api_url = os.getenv("QUORUM_API_URL")
    if api_url:
        st.info(f"Partner API configured. Ready to fetch solicitations.")
    else:
        st.warning("QUORUM_API_URL not set in .env file. Please configure it to connect to the partner API.")


def render_results_list(reports: list):
    """Render the list of RFP results."""
    # Sort options
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("### 📊 Analysis Results")
    
    with col2:
        sort_option = st.selectbox(
            "Sort by",
            ["Score (High to Low)", "Score (Low to High)", "Name (A-Z)"],
            label_visibility="collapsed"
        )
    
    # Sort reports
    if sort_option == "Score (High to Low)":
        reports = sorted(reports, key=lambda x: x.get("match_score", 0), reverse=True)
    elif sort_option == "Score (Low to High)":
        reports = sorted(reports, key=lambda x: x.get("match_score", 0))
    else:
        reports = sorted(reports, key=lambda x: x.get("rfp_id", ""))
    
    # Filter options
    filter_col1, filter_col2 = st.columns(2)
    
    with filter_col1:
        rec_filter = st.multiselect(
            "Filter by Recommendation",
            ["GO", "CONDITIONAL", "NO-GO"],
            default=["GO", "CONDITIONAL", "NO-GO"]
        )
    
    with filter_col2:
        min_score = st.slider("Minimum Score", 0, 100, 0)
    
    # Apply filters
    filtered_reports = [
        r for r in reports 
        if r.get("recommendation", "ERROR") in rec_filter + (["ERROR"] if "NO-GO" in rec_filter else [])
        and r.get("match_score", 0) >= min_score
    ]
    
    st.markdown(f"*Showing {len(filtered_reports)} of {len(reports)} results*")
    
    # Render cards
    for report in filtered_reports:
        render_rfp_card(report)


# ============================================================================
# MAIN APP
# ============================================================================

def main():
    """Main application entry point."""
    paths = get_base_paths()
    
    # Render sidebar
    render_sidebar()
    
    # Render main content
    render_header()
    
    # Load reports
    reports = load_triage_reports(paths["output"])
    
    if reports:
        # Show metrics
        render_metrics(reports)
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Show results
        render_results_list(reports)
    else:
        render_empty_state()
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #6c757d; font-size: 0.85rem;'>"
        "Quorum - Intelligent RFP Triage System | Built for Government Contractors"
        "</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
