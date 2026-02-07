# Quorum: Engineering the Capability Contest

## 1. Mission Statement
Quorum is designed to transform government contracting from a "writing contest" (who can hire the best proposal writers) into a "capability contest" (who is actually best for the job). We use Large Language Models (LLMs) and agentic workflows to automate the administrative overhead of the federal procurement lifecycle.

## 2. Core Architectural Pillars
Quorum operates through a four-phase pipeline designed to take a raw federal opportunity and turn it into a high-scoring technical proposal.

### Phase 1: Ingestion & Raw Filtering
**The Inflow:** Scrapers monitor SAM.gov and other portals for active RFIs/RFPs.

**Firm DNA:** A vector database (Pinecone/Chroma) stores "Firm Data," including Capability Statements, past performance, and employee resumes.

**Hard Filters:** Non-LLM filters (NAICS codes, Set-Asides, Deadlines) remove obvious noise.

### Phase 2: Intelligent Triage (The "AI Engineer" Domain)
This is the "Brain" of the system. It uses agentic logic to verify "Fit" before a single word of a proposal is written.

**Knockout Scan:** Fast, low-cost models scan "Instructions to Offerors" for mandatory disqualifiers like facility clearances or ISO certifications.

**Semantic Matching:** High-reasoning agents compare the RFP's Statement of Work (SOW) against the firm's past performance to identify deep technical alignment.

**Match Scoring:** Generates a 0-100 score and risk report for human review.

### Phase 3: Strategic Approval (Human-in-the-Loop)
**The Dashboard:** A UI/UX layer where "Doer-Sellers" review the AI's reasoning.

**Gatekeeping:** A human must approve an opportunity before the system moves to the expensive generative phase.

### Phase 4: Generative Drafting
**Proof Point Retrieval:** The system pulls the exact evidence (bios, project metrics) required for the specific RFP.

**The 80% Draft:** High-reasoning models (e.g., Claude 3.5 Sonnet) generate a compliant, technical response following the required format (Executive Summary, Technical Approach, etc.).

**Compliance Focus:** Ensures the draft matches "Section L" instructions exactly.

## 3. Tech Stack & Engineering Philosophy
**Models:** Multi-model approach (Haiku for speed/cost-effective scans; Sonnet for complex reasoning).

**Context Strategy:** Map-Reduce logic for handling massive government PDFs (often 100+ pages).

**Modular Design:** The AI Engineer focuses on the Triage and Drafting engines. Database and UI management are kept separate.

**Reliability:** Missing a "Knockout" is a critical failure. The system prioritizes accuracy over speed in Phase 2.

## 4. Operational Goals
**Short-term:** Prototype a Phase 2 "Checker" that can accurately flag disqualifiers in an FAA SOW.

**Long-term:** Reduce the time-to-submission for a federal proposal from weeks to hours.

## 5. Setup
See [HOW_TO_RUN.md](HOW_TO_RUN.md) for full setup and usage instructions.
