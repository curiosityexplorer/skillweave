"""
Enterprise Skill Catalog — 47 skills across 12 agents in 2 domains.

Financial Services (6 agents, 24 skills):
  - FS-Agent-1: Portfolio Analysis (4 skills)
  - FS-Agent-2: Risk Assessment (4 skills)
  - FS-Agent-3: Regulatory Compliance (4 skills)
  - FS-Agent-4: Trade Execution (4 skills)
  - FS-Agent-5: Audit Reporting (4 skills)
  - FS-Agent-6: Client Advisory (4 skills)

Healthcare (6 agents, 23 skills):
  - HC-Agent-1: Clinical Decision Support (4 skills)
  - HC-Agent-2: Diagnostic Analysis (4 skills)
  - HC-Agent-3: Treatment Planning (4 skills)
  - HC-Agent-4: Insurance Verification (4 skills)
  - HC-Agent-5: HIPAA Compliance (4 skills)
  - HC-Agent-6: Medical Records (3 skills)
"""

from .models import (
    Agent, AgentSkill, AuthorityLevel, BaseType, DataBoundary,
    DataBoundaryType, OrganizationalPrincipal, Policy, PolicyAction,
    PolicyType, SemanticAnnotation, SkillVersion, TypeSchema,
)

# ═══════════════════════════════════════════════════════════════════════════
# PRINCIPAL HIERARCHY
# ═══════════════════════════════════════════════════════════════════════════

PRINCIPALS = {
    # Enterprise root
    "enterprise": OrganizationalPrincipal(
        id="enterprise", role="Enterprise", authority=AuthorityLevel.ENTERPRISE,
        scope="*", policies=frozenset(), parent_id=None,
    ),
    # Divisions
    "div-finance": OrganizationalPrincipal(
        id="div-finance", role="Finance Division", authority=AuthorityLevel.DIVISION,
        scope="finance/*", policies=frozenset(["SOX-compliance"]), parent_id="enterprise",
    ),
    "div-health": OrganizationalPrincipal(
        id="div-health", role="Healthcare Division", authority=AuthorityLevel.DIVISION,
        scope="healthcare/*", policies=frozenset(["HIPAA-compliance"]), parent_id="enterprise",
    ),
    # Departments
    "dept-portfolio": OrganizationalPrincipal(
        id="dept-portfolio", role="Portfolio Mgmt", authority=AuthorityLevel.DEPARTMENT,
        scope="finance/portfolio", policies=frozenset(), parent_id="div-finance",
    ),
    "dept-risk": OrganizationalPrincipal(
        id="dept-risk", role="Risk Mgmt", authority=AuthorityLevel.DEPARTMENT,
        scope="finance/risk", policies=frozenset(), parent_id="div-finance",
    ),
    "dept-compliance-fin": OrganizationalPrincipal(
        id="dept-compliance-fin", role="Financial Compliance", authority=AuthorityLevel.DEPARTMENT,
        scope="finance/compliance", policies=frozenset(["SOX-compliance"]), parent_id="div-finance",
    ),
    "dept-trading": OrganizationalPrincipal(
        id="dept-trading", role="Trading Desk", authority=AuthorityLevel.DEPARTMENT,
        scope="finance/trading", policies=frozenset(), parent_id="div-finance",
    ),
    "dept-audit": OrganizationalPrincipal(
        id="dept-audit", role="Audit", authority=AuthorityLevel.DEPARTMENT,
        scope="finance/audit", policies=frozenset(["SOX-compliance"]), parent_id="div-finance",
    ),
    "dept-advisory": OrganizationalPrincipal(
        id="dept-advisory", role="Client Advisory", authority=AuthorityLevel.DEPARTMENT,
        scope="finance/advisory", policies=frozenset(), parent_id="div-finance",
    ),
    "dept-clinical": OrganizationalPrincipal(
        id="dept-clinical", role="Clinical", authority=AuthorityLevel.DEPARTMENT,
        scope="healthcare/clinical", policies=frozenset(["HIPAA-compliance"]), parent_id="div-health",
    ),
    "dept-diagnostics": OrganizationalPrincipal(
        id="dept-diagnostics", role="Diagnostics", authority=AuthorityLevel.DEPARTMENT,
        scope="healthcare/diagnostics", policies=frozenset(["HIPAA-compliance"]), parent_id="div-health",
    ),
    "dept-treatment": OrganizationalPrincipal(
        id="dept-treatment", role="Treatment Planning", authority=AuthorityLevel.DEPARTMENT,
        scope="healthcare/treatment", policies=frozenset(["HIPAA-compliance"]), parent_id="div-health",
    ),
    "dept-insurance": OrganizationalPrincipal(
        id="dept-insurance", role="Insurance", authority=AuthorityLevel.DEPARTMENT,
        scope="healthcare/insurance", policies=frozenset(), parent_id="div-health",
    ),
    "dept-compliance-hc": OrganizationalPrincipal(
        id="dept-compliance-hc", role="HC Compliance", authority=AuthorityLevel.DEPARTMENT,
        scope="healthcare/compliance", policies=frozenset(["HIPAA-compliance"]), parent_id="div-health",
    ),
    "dept-records": OrganizationalPrincipal(
        id="dept-records", role="Medical Records", authority=AuthorityLevel.DEPARTMENT,
        scope="healthcare/records", policies=frozenset(["HIPAA-compliance"]), parent_id="div-health",
    ),
}

# ═══════════════════════════════════════════════════════════════════════════
# COMMON POLICIES
# ═══════════════════════════════════════════════════════════════════════════

POLICIES = {
    "pol-sox-read": Policy("pol-sox-read", PolicyType.DATA_ACCESS, PolicyAction.ALLOW,
                           "regulation:SOX", ("financial_data",)),
    "pol-sox-write-deny": Policy("pol-sox-write-deny", PolicyType.DATA_ACCESS, PolicyAction.DENY,
                                  "regulation:SOX", ("unauthorized_financial_write",)),
    "pol-hipaa-phi-access": Policy("pol-hipaa-phi", PolicyType.DATA_ACCESS, PolicyAction.ALLOW,
                                    "regulation:HIPAA", ("covered_entity",)),
    "pol-hipaa-phi-deny": Policy("pol-hipaa-phi-deny", PolicyType.DATA_ACCESS, PolicyAction.DENY,
                                  "regulation:HIPAA", ("non_covered_entity",)),
    "pol-hipaa-share-deny": Policy("pol-hipaa-share-deny", PolicyType.DATA_SHARING, PolicyAction.DENY,
                                    "regulation:HIPAA", ("external_sharing",)),
    "pol-pii-encrypt": Policy("pol-pii-encrypt", PolicyType.DATA_ACCESS, PolicyAction.REQUIRE_ENCRYPTION,
                               "classification:PII", ()),
    "pol-audit-required": Policy("pol-audit-required", PolicyType.AUDIT_REQUIREMENT, PolicyAction.REQUIRE_AUDIT,
                                  "regulation:SOX", ()),
    "pol-trade-approval": Policy("pol-trade-approval", PolicyType.EXECUTION_AUTHORITY, PolicyAction.REQUIRE_APPROVAL,
                                  "action:trade_execution", ("manual_review",)),
    "pol-trade-auto": Policy("pol-trade-auto", PolicyType.EXECUTION_AUTHORITY, PolicyAction.ALLOW,
                              "action:trade_execution", ("automated",)),
    "pol-data-retain-7y": Policy("pol-retain-7y", PolicyType.DATA_RETENTION, PolicyAction.REQUIRE_AUDIT,
                                  "regulation:SOX", ("7_year_retention",)),
    "pol-gdpr-consent": Policy("pol-gdpr-consent", PolicyType.DATA_SHARING, PolicyAction.REQUIRE_APPROVAL,
                                "regulation:GDPR", ("data_subject_consent",)),
}

# ═══════════════════════════════════════════════════════════════════════════
# DATA BOUNDARIES
# ═══════════════════════════════════════════════════════════════════════════

BOUNDARIES = {
    "fin-portfolio": DataBoundary(DataBoundaryType.DEPARTMENT, "dept:portfolio",
                                   frozenset({"dept:risk", "dept:advisory"})),
    "fin-risk": DataBoundary(DataBoundaryType.DEPARTMENT, "dept:risk",
                              frozenset({"dept:portfolio", "dept:compliance-fin", "dept:trading"})),
    "fin-compliance": DataBoundary(DataBoundaryType.DEPARTMENT, "dept:compliance-fin",
                                    frozenset({"dept:risk", "dept:audit", "dept:trading"})),
    "fin-trading": DataBoundary(DataBoundaryType.DEPARTMENT, "dept:trading",
                                 frozenset({"dept:risk", "dept:compliance-fin"})),
    "fin-audit": DataBoundary(DataBoundaryType.DEPARTMENT, "dept:audit",
                               frozenset({"dept:compliance-fin", "dept:portfolio", "dept:risk", "dept:trading"})),
    "fin-advisory": DataBoundary(DataBoundaryType.DEPARTMENT, "dept:advisory",
                                  frozenset({"dept:portfolio"})),
    "hc-clinical": DataBoundary(DataBoundaryType.REGULATORY, "reg:clinical-phi",
                                 frozenset({"reg:diagnostics-phi", "reg:treatment-phi", "reg:compliance-hc"})),
    "hc-diagnostics": DataBoundary(DataBoundaryType.REGULATORY, "reg:diagnostics-phi",
                                    frozenset({"reg:clinical-phi", "reg:treatment-phi"})),
    "hc-treatment": DataBoundary(DataBoundaryType.REGULATORY, "reg:treatment-phi",
                                  frozenset({"reg:clinical-phi", "reg:diagnostics-phi", "reg:compliance-hc"})),
    "hc-insurance": DataBoundary(DataBoundaryType.DEPARTMENT, "dept:insurance",
                                  frozenset()),  # Intentionally no crossings to PHI
    "hc-compliance": DataBoundary(DataBoundaryType.REGULATORY, "reg:compliance-hc",
                                   frozenset({"reg:clinical-phi", "reg:treatment-phi"})),
    "hc-records": DataBoundary(DataBoundaryType.REGULATORY, "reg:records-phi",
                                frozenset({"reg:clinical-phi", "reg:diagnostics-phi", "reg:treatment-phi", "reg:compliance-hc"})),
}


# ═══════════════════════════════════════════════════════════════════════════
# HELPER for building type schemas
# ═══════════════════════════════════════════════════════════════════════════

def _ts(fields, annotations=frozenset()):
    return TypeSchema(
        fields=tuple(fields),
        annotations=frozenset(annotations),
    )

B = BaseType
SA = SemanticAnnotation
AL = AuthorityLevel

# ═══════════════════════════════════════════════════════════════════════════
# FINANCIAL SERVICES SKILLS (24 total)
# ═══════════════════════════════════════════════════════════════════════════

# ── FS-Agent-1: Portfolio Analysis ────────────────────────────────────────
fs_skills_portfolio = [
    AgentSkill(
        id="fs-pa-01", name="Portfolio Valuation",
        description="Computes current market value of a portfolio",
        input_schema=_ts([("portfolio_id", B.TEXTUAL), ("date", B.TEMPORAL)]),
        output_schema=_ts([("portfolio_id", B.TEXTUAL), ("valuation", B.NUMERIC),
                           ("currency", B.TEXTUAL), ("date", B.TEMPORAL)],
                          {SA.SOX_REGULATED, SA.FINANCIAL_PII}),
        required_permissions=frozenset({"read:portfolio", "read:market_data"}),
        policies=frozenset({POLICIES["pol-sox-read"]}),
        data_boundary=BOUNDARIES["fin-portfolio"],
        version=SkillVersion(1, 2, 0, "SOX-2024"),
        semantic_tags=frozenset({"portfolio", "valuation", "market_data", "financial_analysis"}),
        min_authority_level=AL.DEPARTMENT,
    ),
    AgentSkill(
        id="fs-pa-02", name="Asset Allocation Analysis",
        description="Analyzes allocation across asset classes",
        input_schema=_ts([("portfolio_id", B.TEXTUAL), ("valuation", B.NUMERIC)],
                         {SA.SOX_REGULATED}),
        output_schema=_ts([("portfolio_id", B.TEXTUAL), ("allocations", B.JSON_OBJECT),
                           ("risk_score", B.NUMERIC)], {SA.SOX_REGULATED}),
        required_permissions=frozenset({"read:portfolio"}),
        policies=frozenset({POLICIES["pol-sox-read"]}),
        data_boundary=BOUNDARIES["fin-portfolio"],
        version=SkillVersion(1, 2, 0, "SOX-2024"),
        semantic_tags=frozenset({"portfolio", "allocation", "financial_analysis"}),
        min_authority_level=AL.DEPARTMENT,
    ),
    AgentSkill(
        id="fs-pa-03", name="Performance Attribution",
        description="Attributes portfolio returns to factors",
        input_schema=_ts([("portfolio_id", B.TEXTUAL), ("allocations", B.JSON_OBJECT),
                          ("date", B.TEMPORAL)], {SA.SOX_REGULATED}),
        output_schema=_ts([("attribution_report", B.JSON_OBJECT), ("alpha", B.NUMERIC)],
                          {SA.SOX_REGULATED}),
        required_permissions=frozenset({"read:portfolio", "read:benchmarks"}),
        policies=frozenset({POLICIES["pol-sox-read"], POLICIES["pol-audit-required"]}),
        data_boundary=BOUNDARIES["fin-portfolio"],
        version=SkillVersion(1, 1, 0, "SOX-2024"),
        semantic_tags=frozenset({"portfolio", "performance", "attribution", "financial_analysis"}),
        min_authority_level=AL.DEPARTMENT,
    ),
    AgentSkill(
        id="fs-pa-04", name="Sector Exposure Report",
        description="Generates sector-level exposure analysis",
        input_schema=_ts([("portfolio_id", B.TEXTUAL), ("allocations", B.JSON_OBJECT)]),
        output_schema=_ts([("sector_exposures", B.JSON_OBJECT), ("concentration_risk", B.NUMERIC)]),
        required_permissions=frozenset({"read:portfolio"}),
        policies=frozenset({POLICIES["pol-sox-read"]}),
        data_boundary=BOUNDARIES["fin-portfolio"],
        version=SkillVersion(1, 0, 3),
        semantic_tags=frozenset({"portfolio", "sector", "exposure", "risk_minimizing"}),
        min_authority_level=AL.TEAM,
    ),
]

# ── FS-Agent-2: Risk Assessment ──────────────────────────────────────────
fs_skills_risk = [
    AgentSkill(
        id="fs-ra-01", name="VaR Calculation",
        description="Computes Value-at-Risk using Monte Carlo simulation",
        input_schema=_ts([("portfolio_id", B.TEXTUAL), ("valuation", B.NUMERIC),
                          ("risk_score", B.NUMERIC)], {SA.SOX_REGULATED}),
        output_schema=_ts([("var_95", B.NUMERIC), ("var_99", B.NUMERIC),
                           ("risk_report", B.JSON_OBJECT)], {SA.SOX_REGULATED}),
        required_permissions=frozenset({"read:portfolio", "read:market_data", "compute:risk"}),
        policies=frozenset({POLICIES["pol-sox-read"], POLICIES["pol-audit-required"]}),
        data_boundary=BOUNDARIES["fin-risk"],
        version=SkillVersion(2, 0, 1, "SOX-2024"),
        semantic_tags=frozenset({"risk", "var", "risk_minimizing", "conservative_compliance"}),
        min_authority_level=AL.DEPARTMENT,
    ),
    AgentSkill(
        id="fs-ra-02", name="Stress Testing",
        description="Runs stress test scenarios on portfolio",
        input_schema=_ts([("portfolio_id", B.TEXTUAL), ("var_95", B.NUMERIC),
                          ("risk_report", B.JSON_OBJECT)], {SA.SOX_REGULATED}),
        output_schema=_ts([("stress_results", B.JSON_OBJECT), ("worst_case_loss", B.NUMERIC)],
                          {SA.SOX_REGULATED}),
        required_permissions=frozenset({"read:portfolio", "compute:risk"}),
        policies=frozenset({POLICIES["pol-sox-read"]}),
        data_boundary=BOUNDARIES["fin-risk"],
        version=SkillVersion(2, 0, 0, "SOX-2024"),
        semantic_tags=frozenset({"risk", "stress_test", "risk_minimizing"}),
        min_authority_level=AL.DEPARTMENT,
    ),
    AgentSkill(
        id="fs-ra-03", name="Counterparty Risk Analysis",
        description="Evaluates counterparty credit and exposure risk",
        input_schema=_ts([("counterparty_ids", B.JSON_ARRAY), ("exposure_data", B.JSON_OBJECT)]),
        output_schema=_ts([("counterparty_risk_scores", B.JSON_OBJECT),
                           ("aggregate_exposure", B.NUMERIC)], {SA.FINANCIAL_PII}),
        required_permissions=frozenset({"read:counterparty", "read:credit"}),
        policies=frozenset({POLICIES["pol-sox-read"]}),
        data_boundary=BOUNDARIES["fin-risk"],
        version=SkillVersion(1, 1, 0),
        semantic_tags=frozenset({"risk", "counterparty", "credit", "thorough_review"}),
        min_authority_level=AL.DEPARTMENT,
    ),
    AgentSkill(
        id="fs-ra-04", name="Liquidity Risk Assessment",
        description="Assesses portfolio liquidity under various conditions",
        input_schema=_ts([("portfolio_id", B.TEXTUAL), ("allocations", B.JSON_OBJECT)]),
        output_schema=_ts([("liquidity_score", B.NUMERIC), ("days_to_liquidate", B.NUMERIC)]),
        required_permissions=frozenset({"read:portfolio", "read:market_data"}),
        policies=frozenset({POLICIES["pol-sox-read"]}),
        data_boundary=BOUNDARIES["fin-risk"],
        version=SkillVersion(1, 0, 0),
        semantic_tags=frozenset({"risk", "liquidity", "risk_minimizing"}),
        min_authority_level=AL.TEAM,
    ),
]

# ── FS-Agent-3: Regulatory Compliance ────────────────────────────────────
fs_skills_compliance = [
    AgentSkill(
        id="fs-rc-01", name="SOX Compliance Check",
        description="Validates financial reporting against SOX requirements",
        input_schema=_ts([("report_data", B.JSON_OBJECT), ("period", B.TEMPORAL)],
                         {SA.SOX_REGULATED}),
        output_schema=_ts([("compliance_status", B.CATEGORICAL), ("findings", B.JSON_ARRAY),
                           ("remediation_required", B.BOOLEAN)], {SA.SOX_REGULATED}),
        required_permissions=frozenset({"read:financial_reports", "write:compliance_findings"}),
        policies=frozenset({POLICIES["pol-sox-read"], POLICIES["pol-audit-required"],
                           POLICIES["pol-data-retain-7y"]}),
        data_boundary=BOUNDARIES["fin-compliance"],
        version=SkillVersion(3, 0, 0, "SOX-2024"),
        semantic_tags=frozenset({"compliance", "sox", "conservative_compliance", "financial_approval",
                                 "thorough_review"}),
        min_authority_level=AL.DEPARTMENT,
    ),
    AgentSkill(
        id="fs-rc-02", name="AML Screening",
        description="Anti-money laundering screening of transactions",
        input_schema=_ts([("transaction_batch", B.JSON_ARRAY), ("party_ids", B.JSON_ARRAY)],
                         {SA.PII_CLASSIFIED, SA.FINANCIAL_PII}),
        output_schema=_ts([("screening_results", B.JSON_ARRAY), ("flagged_count", B.NUMERIC),
                           ("risk_level", B.CATEGORICAL)], {SA.PII_CLASSIFIED}),
        required_permissions=frozenset({"read:transactions", "read:watchlists"}),
        policies=frozenset({POLICIES["pol-sox-read"], POLICIES["pol-pii-encrypt"]}),
        data_boundary=BOUNDARIES["fin-compliance"],
        version=SkillVersion(2, 1, 0, "SOX-2024"),
        semantic_tags=frozenset({"compliance", "aml", "screening", "conservative_compliance"}),
        min_authority_level=AL.DEPARTMENT,
    ),
    AgentSkill(
        id="fs-rc-03", name="Regulatory Report Generator",
        description="Generates regulatory reports for filing",
        input_schema=_ts([("compliance_status", B.CATEGORICAL), ("findings", B.JSON_ARRAY),
                          ("period", B.TEMPORAL)], {SA.SOX_REGULATED}),
        output_schema=_ts([("report_document", B.BINARY), ("filing_reference", B.TEXTUAL)],
                          {SA.SOX_REGULATED}),
        required_permissions=frozenset({"read:compliance_findings", "write:reports"}),
        policies=frozenset({POLICIES["pol-sox-read"], POLICIES["pol-audit-required"]}),
        data_boundary=BOUNDARIES["fin-compliance"],
        version=SkillVersion(2, 0, 0, "SOX-2024"),
        semantic_tags=frozenset({"compliance", "reporting", "financial_creation"}),
        min_authority_level=AL.DEPARTMENT,
    ),
    AgentSkill(
        id="fs-rc-04", name="Trade Surveillance",
        description="Monitors trades for market manipulation patterns",
        input_schema=_ts([("trade_log", B.JSON_ARRAY), ("date_range", B.TEMPORAL)]),
        output_schema=_ts([("alerts", B.JSON_ARRAY), ("pattern_matches", B.JSON_OBJECT)]),
        required_permissions=frozenset({"read:trades", "read:market_data"}),
        policies=frozenset({POLICIES["pol-sox-read"]}),
        data_boundary=BOUNDARIES["fin-compliance"],
        version=SkillVersion(1, 3, 0),
        semantic_tags=frozenset({"compliance", "surveillance", "trading", "conservative_compliance"}),
        min_authority_level=AL.DEPARTMENT,
    ),
]

# ── FS-Agent-4: Trade Execution ──────────────────────────────────────────
fs_skills_trading = [
    AgentSkill(
        id="fs-te-01", name="Order Placement",
        description="Places trade orders on exchanges",
        input_schema=_ts([("order_spec", B.JSON_OBJECT), ("portfolio_id", B.TEXTUAL)]),
        output_schema=_ts([("order_id", B.TEXTUAL), ("execution_status", B.CATEGORICAL),
                           ("filled_price", B.NUMERIC)], {SA.SOX_REGULATED}),
        required_permissions=frozenset({"write:trades", "read:portfolio"}),
        policies=frozenset({POLICIES["pol-trade-auto"], POLICIES["pol-audit-required"]}),
        data_boundary=BOUNDARIES["fin-trading"],
        version=SkillVersion(3, 1, 0, "SOX-2024"),
        semantic_tags=frozenset({"trading", "execution", "automated_execution",
                                 "aggressive_trading", "risk_maximizing"}),
        min_authority_level=AL.DIVISION,  # High authority for trade execution
    ),
    AgentSkill(
        id="fs-te-02", name="Algorithmic Trading Strategy",
        description="Executes algorithmic trading strategies",
        input_schema=_ts([("strategy_params", B.JSON_OBJECT), ("market_data", B.JSON_OBJECT)]),
        output_schema=_ts([("trade_signals", B.JSON_ARRAY), ("expected_pnl", B.NUMERIC)]),
        required_permissions=frozenset({"write:trades", "read:market_data"}),
        policies=frozenset({POLICIES["pol-trade-auto"]}),
        data_boundary=BOUNDARIES["fin-trading"],
        version=SkillVersion(2, 0, 0),
        semantic_tags=frozenset({"trading", "algorithmic", "automated_execution", "risk_maximizing",
                                 "real_time_processing", "aggressive_trading"}),
        min_authority_level=AL.DIVISION,
    ),
    AgentSkill(
        id="fs-te-03", name="Pre-Trade Compliance Check",
        description="Validates trade orders against compliance rules before execution",
        input_schema=_ts([("order_spec", B.JSON_OBJECT)]),
        output_schema=_ts([("approved", B.BOOLEAN), ("compliance_notes", B.JSON_ARRAY)]),
        required_permissions=frozenset({"read:compliance_rules", "read:trades"}),
        policies=frozenset({POLICIES["pol-sox-read"]}),
        data_boundary=BOUNDARIES["fin-trading"],
        version=SkillVersion(1, 0, 0),
        semantic_tags=frozenset({"trading", "compliance", "conservative_compliance", "thorough_review"}),
        min_authority_level=AL.DEPARTMENT,
    ),
    AgentSkill(
        id="fs-te-04", name="Settlement Processing",
        description="Processes trade settlements and reconciliation",
        input_schema=_ts([("order_id", B.TEXTUAL), ("execution_status", B.CATEGORICAL),
                          ("filled_price", B.NUMERIC)], {SA.SOX_REGULATED}),
        output_schema=_ts([("settlement_id", B.TEXTUAL), ("settlement_status", B.CATEGORICAL)],
                          {SA.SOX_REGULATED}),
        required_permissions=frozenset({"write:settlements", "read:trades"}),
        policies=frozenset({POLICIES["pol-sox-read"], POLICIES["pol-audit-required"]}),
        data_boundary=BOUNDARIES["fin-trading"],
        version=SkillVersion(2, 1, 0, "SOX-2024"),
        semantic_tags=frozenset({"trading", "settlement", "batch_processing"}),
        min_authority_level=AL.DEPARTMENT,
    ),
]

# ── FS-Agent-5: Audit Reporting ──────────────────────────────────────────
fs_skills_audit = [
    AgentSkill(
        id="fs-ar-01", name="Audit Trail Compilation",
        description="Compiles comprehensive audit trails from system logs",
        input_schema=_ts([("date_range", B.TEMPORAL), ("scope", B.TEXTUAL)]),
        output_schema=_ts([("audit_trail", B.JSON_ARRAY), ("entry_count", B.NUMERIC)],
                          {SA.SOX_REGULATED}),
        required_permissions=frozenset({"read:audit_logs", "read:system_logs"}),
        policies=frozenset({POLICIES["pol-sox-read"], POLICIES["pol-audit-required"]}),
        data_boundary=BOUNDARIES["fin-audit"],
        version=SkillVersion(2, 0, 0, "SOX-2024"),
        semantic_tags=frozenset({"audit", "compliance", "reporting", "thorough_review"}),
        min_authority_level=AL.DEPARTMENT,
    ),
    AgentSkill(
        id="fs-ar-02", name="Internal Control Assessment",
        description="Evaluates effectiveness of internal controls",
        input_schema=_ts([("audit_trail", B.JSON_ARRAY), ("control_framework", B.TEXTUAL)],
                         {SA.SOX_REGULATED}),
        output_schema=_ts([("control_ratings", B.JSON_OBJECT), ("deficiencies", B.JSON_ARRAY)],
                          {SA.SOX_REGULATED}),
        required_permissions=frozenset({"read:audit_logs", "read:controls"}),
        policies=frozenset({POLICIES["pol-sox-read"], POLICIES["pol-audit-required"]}),
        data_boundary=BOUNDARIES["fin-audit"],
        version=SkillVersion(1, 1, 0, "SOX-2024"),
        semantic_tags=frozenset({"audit", "controls", "financial_approval", "thorough_review"}),
        min_authority_level=AL.DEPARTMENT,
    ),
    AgentSkill(
        id="fs-ar-03", name="Exception Report Generator",
        description="Identifies and reports policy exceptions",
        input_schema=_ts([("audit_trail", B.JSON_ARRAY)], {SA.SOX_REGULATED}),
        output_schema=_ts([("exceptions", B.JSON_ARRAY), ("severity_distribution", B.JSON_OBJECT)]),
        required_permissions=frozenset({"read:audit_logs"}),
        policies=frozenset({POLICIES["pol-sox-read"]}),
        data_boundary=BOUNDARIES["fin-audit"],
        version=SkillVersion(1, 0, 2),
        semantic_tags=frozenset({"audit", "exceptions", "reporting"}),
        min_authority_level=AL.TEAM,
    ),
    AgentSkill(
        id="fs-ar-04", name="Compliance Dashboard Data",
        description="Aggregates data for compliance dashboards",
        input_schema=_ts([("control_ratings", B.JSON_OBJECT), ("exceptions", B.JSON_ARRAY)]),
        output_schema=_ts([("dashboard_metrics", B.JSON_OBJECT), ("trend_data", B.JSON_ARRAY)]),
        required_permissions=frozenset({"read:audit_logs"}),
        policies=frozenset({POLICIES["pol-sox-read"]}),
        data_boundary=BOUNDARIES["fin-audit"],
        version=SkillVersion(1, 0, 0),
        semantic_tags=frozenset({"audit", "dashboard", "reporting", "data_enrichment"}),
        min_authority_level=AL.TEAM,
    ),
]

# ── FS-Agent-6: Client Advisory ──────────────────────────────────────────
fs_skills_advisory = [
    AgentSkill(
        id="fs-ca-01", name="Client Risk Profiling",
        description="Assesses client risk tolerance and investment profile",
        input_schema=_ts([("client_id", B.TEXTUAL), ("questionnaire_data", B.JSON_OBJECT)],
                         {SA.PII_CLASSIFIED, SA.FINANCIAL_PII}),
        output_schema=_ts([("risk_profile", B.JSON_OBJECT), ("suitability_score", B.NUMERIC)],
                          {SA.PII_CLASSIFIED, SA.FINANCIAL_PII}),
        required_permissions=frozenset({"read:client_data"}),
        policies=frozenset({POLICIES["pol-pii-encrypt"], POLICIES["pol-gdpr-consent"]}),
        data_boundary=BOUNDARIES["fin-advisory"],
        version=SkillVersion(1, 1, 0),
        semantic_tags=frozenset({"advisory", "client", "risk_profiling", "data_minimization"}),
        min_authority_level=AL.DEPARTMENT,
    ),
    AgentSkill(
        id="fs-ca-02", name="Investment Recommendation",
        description="Generates personalized investment recommendations",
        input_schema=_ts([("risk_profile", B.JSON_OBJECT), ("suitability_score", B.NUMERIC),
                          ("portfolio_id", B.TEXTUAL)], {SA.PII_CLASSIFIED}),
        output_schema=_ts([("recommendations", B.JSON_ARRAY), ("rationale", B.TEXTUAL)],
                          {SA.FINANCIAL_PII}),
        required_permissions=frozenset({"read:client_data", "read:portfolio", "read:market_data"}),
        policies=frozenset({POLICIES["pol-pii-encrypt"]}),
        data_boundary=BOUNDARIES["fin-advisory"],
        version=SkillVersion(1, 0, 0),
        semantic_tags=frozenset({"advisory", "recommendations", "revenue_optimization"}),
        min_authority_level=AL.DEPARTMENT,
    ),
    AgentSkill(
        id="fs-ca-03", name="Client Report Generation",
        description="Generates client-facing portfolio reports",
        input_schema=_ts([("portfolio_id", B.TEXTUAL), ("recommendations", B.JSON_ARRAY)]),
        output_schema=_ts([("report_document", B.BINARY), ("summary", B.TEXTUAL)]),
        required_permissions=frozenset({"read:portfolio", "write:reports"}),
        policies=frozenset(),
        data_boundary=BOUNDARIES["fin-advisory"],
        version=SkillVersion(1, 0, 0),
        semantic_tags=frozenset({"advisory", "reporting", "client_facing"}),
        min_authority_level=AL.TEAM,
    ),
    AgentSkill(
        id="fs-ca-04", name="Fee Calculation",
        description="Computes advisory fees based on AUM and performance",
        input_schema=_ts([("portfolio_id", B.TEXTUAL), ("valuation", B.NUMERIC)]),
        output_schema=_ts([("fee_amount", B.NUMERIC), ("fee_breakdown", B.JSON_OBJECT)],
                          {SA.FINANCIAL_PII}),
        required_permissions=frozenset({"read:portfolio", "read:fee_schedules"}),
        policies=frozenset({POLICIES["pol-sox-read"]}),
        data_boundary=BOUNDARIES["fin-advisory"],
        version=SkillVersion(1, 0, 0),
        semantic_tags=frozenset({"advisory", "fees", "revenue_optimization", "financial_creation"}),
        min_authority_level=AL.DEPARTMENT,
    ),
]

# ═══════════════════════════════════════════════════════════════════════════
# HEALTHCARE SKILLS (23 total)
# ═══════════════════════════════════════════════════════════════════════════

# ── HC-Agent-1: Clinical Decision Support ────────────────────────────────
hc_skills_clinical = [
    AgentSkill(
        id="hc-cd-01", name="Patient Risk Stratification",
        description="Stratifies patients by clinical risk factors",
        input_schema=_ts([("patient_id", B.TEXTUAL), ("medical_history", B.JSON_OBJECT)],
                         {SA.PHI, SA.HIPAA_PROTECTED}),
        output_schema=_ts([("risk_category", B.CATEGORICAL), ("risk_factors", B.JSON_ARRAY),
                           ("risk_score", B.NUMERIC)], {SA.PHI, SA.HIPAA_PROTECTED}),
        required_permissions=frozenset({"read:patient_records", "compute:clinical"}),
        policies=frozenset({POLICIES["pol-hipaa-phi-access"]}),
        data_boundary=BOUNDARIES["hc-clinical"],
        version=SkillVersion(2, 0, 0, "HIPAA-v2"),
        semantic_tags=frozenset({"clinical", "risk_stratification", "patient_privacy", "data_minimization"}),
        min_authority_level=AL.DEPARTMENT,
    ),
    AgentSkill(
        id="hc-cd-02", name="Clinical Guideline Matching",
        description="Matches patient conditions to clinical practice guidelines",
        input_schema=_ts([("patient_id", B.TEXTUAL), ("risk_factors", B.JSON_ARRAY),
                          ("conditions", B.JSON_ARRAY)], {SA.PHI, SA.HIPAA_PROTECTED}),
        output_schema=_ts([("matched_guidelines", B.JSON_ARRAY), ("confidence_scores", B.JSON_OBJECT)],
                          {SA.PHI, SA.HIPAA_PROTECTED}),
        required_permissions=frozenset({"read:patient_records", "read:guidelines"}),
        policies=frozenset({POLICIES["pol-hipaa-phi-access"]}),
        data_boundary=BOUNDARIES["hc-clinical"],
        version=SkillVersion(1, 3, 0, "HIPAA-v2"),
        semantic_tags=frozenset({"clinical", "guidelines", "patient_privacy"}),
        min_authority_level=AL.DEPARTMENT,
    ),
    AgentSkill(
        id="hc-cd-03", name="Drug Interaction Check",
        description="Checks for adverse drug interactions",
        input_schema=_ts([("medication_list", B.JSON_ARRAY), ("patient_id", B.TEXTUAL)],
                         {SA.PHI}),
        output_schema=_ts([("interactions", B.JSON_ARRAY), ("severity_levels", B.JSON_OBJECT),
                           ("safe", B.BOOLEAN)], {SA.PHI}),
        required_permissions=frozenset({"read:patient_records", "read:drug_database"}),
        policies=frozenset({POLICIES["pol-hipaa-phi-access"]}),
        data_boundary=BOUNDARIES["hc-clinical"],
        version=SkillVersion(3, 0, 1, "HIPAA-v2"),
        semantic_tags=frozenset({"clinical", "pharmacology", "safety", "patient_privacy"}),
        min_authority_level=AL.DEPARTMENT,
    ),
    AgentSkill(
        id="hc-cd-04", name="Clinical Alert Generation",
        description="Generates clinical alerts for care team",
        input_schema=_ts([("risk_score", B.NUMERIC), ("interactions", B.JSON_ARRAY)],
                         {SA.PHI}),
        output_schema=_ts([("alerts", B.JSON_ARRAY), ("priority", B.CATEGORICAL)], {SA.PHI}),
        required_permissions=frozenset({"write:alerts", "read:patient_records"}),
        policies=frozenset({POLICIES["pol-hipaa-phi-access"]}),
        data_boundary=BOUNDARIES["hc-clinical"],
        version=SkillVersion(1, 0, 0, "HIPAA-v2"),
        semantic_tags=frozenset({"clinical", "alerting", "real_time_processing"}),
        min_authority_level=AL.TEAM,
    ),
]

# ── HC-Agent-2: Diagnostic Analysis ──────────────────────────────────────
hc_skills_diagnostics = [
    AgentSkill(
        id="hc-da-01", name="Lab Result Interpretation",
        description="Interprets laboratory test results",
        input_schema=_ts([("patient_id", B.TEXTUAL), ("lab_results", B.JSON_OBJECT)],
                         {SA.PHI, SA.HIPAA_PROTECTED}),
        output_schema=_ts([("interpretations", B.JSON_ARRAY), ("abnormal_flags", B.JSON_ARRAY)],
                          {SA.PHI, SA.HIPAA_PROTECTED}),
        required_permissions=frozenset({"read:lab_results", "compute:diagnostics"}),
        policies=frozenset({POLICIES["pol-hipaa-phi-access"]}),
        data_boundary=BOUNDARIES["hc-diagnostics"],
        version=SkillVersion(2, 1, 0, "HIPAA-v2"),
        semantic_tags=frozenset({"diagnostics", "lab", "interpretation", "patient_privacy"}),
        min_authority_level=AL.DEPARTMENT,
    ),
    AgentSkill(
        id="hc-da-02", name="Imaging Analysis",
        description="Analyzes medical imaging studies",
        input_schema=_ts([("patient_id", B.TEXTUAL), ("imaging_study", B.BINARY)],
                         {SA.PHI, SA.HIPAA_PROTECTED}),
        output_schema=_ts([("findings", B.JSON_ARRAY), ("measurements", B.JSON_OBJECT),
                           ("impression", B.TEXTUAL)], {SA.PHI, SA.HIPAA_PROTECTED}),
        required_permissions=frozenset({"read:imaging", "compute:diagnostics"}),
        policies=frozenset({POLICIES["pol-hipaa-phi-access"]}),
        data_boundary=BOUNDARIES["hc-diagnostics"],
        version=SkillVersion(1, 0, 0, "HIPAA-v2"),
        semantic_tags=frozenset({"diagnostics", "imaging", "ai_analysis", "patient_privacy"}),
        min_authority_level=AL.DEPARTMENT,
    ),
    AgentSkill(
        id="hc-da-03", name="Differential Diagnosis Generator",
        description="Generates ranked differential diagnoses",
        input_schema=_ts([("symptoms", B.JSON_ARRAY), ("lab_results", B.JSON_OBJECT),
                          ("medical_history", B.JSON_OBJECT)], {SA.PHI, SA.HIPAA_PROTECTED}),
        output_schema=_ts([("differential_diagnoses", B.JSON_ARRAY),
                           ("probability_scores", B.JSON_OBJECT)], {SA.PHI, SA.HIPAA_PROTECTED}),
        required_permissions=frozenset({"read:patient_records", "compute:diagnostics"}),
        policies=frozenset({POLICIES["pol-hipaa-phi-access"]}),
        data_boundary=BOUNDARIES["hc-diagnostics"],
        version=SkillVersion(1, 2, 0, "HIPAA-v2"),
        semantic_tags=frozenset({"diagnostics", "differential", "ai_analysis", "patient_privacy"}),
        min_authority_level=AL.DEPARTMENT,
    ),
    AgentSkill(
        id="hc-da-04", name="Pathology Report Analysis",
        description="Analyzes pathology reports for structured findings",
        input_schema=_ts([("pathology_report", B.TEXTUAL), ("patient_id", B.TEXTUAL)],
                         {SA.PHI, SA.HIPAA_PROTECTED}),
        output_schema=_ts([("structured_findings", B.JSON_OBJECT), ("staging", B.CATEGORICAL)],
                          {SA.PHI, SA.HIPAA_PROTECTED}),
        required_permissions=frozenset({"read:pathology", "compute:diagnostics"}),
        policies=frozenset({POLICIES["pol-hipaa-phi-access"]}),
        data_boundary=BOUNDARIES["hc-diagnostics"],
        version=SkillVersion(1, 0, 0, "HIPAA-v2"),
        semantic_tags=frozenset({"diagnostics", "pathology", "patient_privacy"}),
        min_authority_level=AL.DEPARTMENT,
    ),
]

# ── HC-Agent-3: Treatment Planning ───────────────────────────────────────
hc_skills_treatment = [
    AgentSkill(
        id="hc-tp-01", name="Treatment Protocol Selection",
        description="Selects appropriate treatment protocols",
        input_schema=_ts([("differential_diagnoses", B.JSON_ARRAY), ("patient_id", B.TEXTUAL),
                          ("medical_history", B.JSON_OBJECT)], {SA.PHI, SA.HIPAA_PROTECTED}),
        output_schema=_ts([("treatment_options", B.JSON_ARRAY), ("recommended_protocol", B.JSON_OBJECT)],
                          {SA.PHI, SA.HIPAA_PROTECTED}),
        required_permissions=frozenset({"read:patient_records", "read:treatment_protocols"}),
        policies=frozenset({POLICIES["pol-hipaa-phi-access"]}),
        data_boundary=BOUNDARIES["hc-treatment"],
        version=SkillVersion(2, 0, 0, "HIPAA-v2"),
        semantic_tags=frozenset({"treatment", "protocol", "patient_privacy", "thorough_review"}),
        min_authority_level=AL.DEPARTMENT,
    ),
    AgentSkill(
        id="hc-tp-02", name="Medication Dosage Calculator",
        description="Calculates optimal medication dosages",
        input_schema=_ts([("medication_id", B.TEXTUAL), ("patient_id", B.TEXTUAL),
                          ("weight", B.NUMERIC), ("renal_function", B.NUMERIC)], {SA.PHI}),
        output_schema=_ts([("dosage", B.NUMERIC), ("frequency", B.TEXTUAL),
                           ("warnings", B.JSON_ARRAY)], {SA.PHI}),
        required_permissions=frozenset({"read:patient_records", "read:drug_database"}),
        policies=frozenset({POLICIES["pol-hipaa-phi-access"]}),
        data_boundary=BOUNDARIES["hc-treatment"],
        version=SkillVersion(1, 1, 0, "HIPAA-v2"),
        semantic_tags=frozenset({"treatment", "dosage", "pharmacology", "patient_privacy"}),
        min_authority_level=AL.DEPARTMENT,
    ),
    AgentSkill(
        id="hc-tp-03", name="Care Plan Generator",
        description="Generates comprehensive care plans",
        input_schema=_ts([("recommended_protocol", B.JSON_OBJECT), ("patient_id", B.TEXTUAL)],
                         {SA.PHI, SA.HIPAA_PROTECTED}),
        output_schema=_ts([("care_plan", B.JSON_OBJECT), ("milestones", B.JSON_ARRAY)],
                          {SA.PHI, SA.HIPAA_PROTECTED}),
        required_permissions=frozenset({"read:patient_records", "write:care_plans"}),
        policies=frozenset({POLICIES["pol-hipaa-phi-access"]}),
        data_boundary=BOUNDARIES["hc-treatment"],
        version=SkillVersion(1, 0, 0, "HIPAA-v2"),
        semantic_tags=frozenset({"treatment", "care_plan", "patient_privacy"}),
        min_authority_level=AL.DEPARTMENT,
    ),
    AgentSkill(
        id="hc-tp-04", name="Referral Recommendation",
        description="Recommends specialist referrals based on clinical needs",
        input_schema=_ts([("differential_diagnoses", B.JSON_ARRAY), ("care_plan", B.JSON_OBJECT)],
                         {SA.PHI}),
        output_schema=_ts([("referral_recommendations", B.JSON_ARRAY),
                           ("urgency", B.CATEGORICAL)], {SA.PHI}),
        required_permissions=frozenset({"read:patient_records", "read:provider_directory"}),
        policies=frozenset({POLICIES["pol-hipaa-phi-access"]}),
        data_boundary=BOUNDARIES["hc-treatment"],
        version=SkillVersion(1, 0, 0, "HIPAA-v2"),
        semantic_tags=frozenset({"treatment", "referral", "data_sharing", "patient_privacy"}),
        min_authority_level=AL.TEAM,
    ),
]

# ── HC-Agent-4: Insurance Verification ───────────────────────────────────
hc_skills_insurance = [
    AgentSkill(
        id="hc-iv-01", name="Coverage Verification",
        description="Verifies patient insurance coverage",
        input_schema=_ts([("patient_id", B.TEXTUAL), ("insurance_id", B.TEXTUAL)],
                         {SA.PII_CLASSIFIED}),
        output_schema=_ts([("coverage_details", B.JSON_OBJECT), ("copay", B.NUMERIC),
                           ("deductible_remaining", B.NUMERIC)], {SA.PII_CLASSIFIED}),
        required_permissions=frozenset({"read:insurance_records"}),
        policies=frozenset({POLICIES["pol-pii-encrypt"]}),
        data_boundary=BOUNDARIES["hc-insurance"],
        version=SkillVersion(1, 2, 0),
        semantic_tags=frozenset({"insurance", "verification", "billing", "data_enrichment"}),
        min_authority_level=AL.TEAM,
    ),
    AgentSkill(
        id="hc-iv-02", name="Pre-Authorization Request",
        description="Submits pre-authorization requests to insurers",
        input_schema=_ts([("treatment_options", B.JSON_ARRAY), ("coverage_details", B.JSON_OBJECT),
                          ("patient_id", B.TEXTUAL)], {SA.PII_CLASSIFIED}),
        output_schema=_ts([("auth_status", B.CATEGORICAL), ("auth_number", B.TEXTUAL)],
                          {SA.PII_CLASSIFIED}),
        required_permissions=frozenset({"read:insurance_records", "write:auth_requests"}),
        policies=frozenset({POLICIES["pol-pii-encrypt"]}),
        data_boundary=BOUNDARIES["hc-insurance"],
        version=SkillVersion(1, 0, 0),
        semantic_tags=frozenset({"insurance", "authorization", "billing"}),
        min_authority_level=AL.DEPARTMENT,
    ),
    AgentSkill(
        id="hc-iv-03", name="Billing Code Assignment",
        description="Assigns appropriate billing/CPT codes",
        input_schema=_ts([("treatment_options", B.JSON_ARRAY), ("care_plan", B.JSON_OBJECT)]),
        output_schema=_ts([("billing_codes", B.JSON_ARRAY), ("estimated_cost", B.NUMERIC)]),
        required_permissions=frozenset({"read:billing_codes"}),
        policies=frozenset(),
        data_boundary=BOUNDARIES["hc-insurance"],
        version=SkillVersion(2, 0, 0),
        semantic_tags=frozenset({"insurance", "billing", "coding", "revenue_optimization"}),
        min_authority_level=AL.TEAM,
    ),
    AgentSkill(
        id="hc-iv-04", name="Claims Processing",
        description="Processes insurance claims",
        input_schema=_ts([("billing_codes", B.JSON_ARRAY), ("patient_id", B.TEXTUAL),
                          ("auth_number", B.TEXTUAL)], {SA.PII_CLASSIFIED}),
        output_schema=_ts([("claim_id", B.TEXTUAL), ("claim_status", B.CATEGORICAL)],
                          {SA.PII_CLASSIFIED}),
        required_permissions=frozenset({"write:claims", "read:insurance_records"}),
        policies=frozenset({POLICIES["pol-pii-encrypt"]}),
        data_boundary=BOUNDARIES["hc-insurance"],
        version=SkillVersion(1, 1, 0),
        semantic_tags=frozenset({"insurance", "claims", "billing"}),
        min_authority_level=AL.DEPARTMENT,
    ),
]

# ── HC-Agent-5: HIPAA Compliance ─────────────────────────────────────────
hc_skills_compliance = [
    AgentSkill(
        id="hc-hc-01", name="PHI Access Audit",
        description="Audits PHI access patterns for HIPAA compliance",
        input_schema=_ts([("date_range", B.TEMPORAL), ("department", B.TEXTUAL)]),
        output_schema=_ts([("access_log", B.JSON_ARRAY), ("violation_flags", B.JSON_ARRAY)]),
        required_permissions=frozenset({"read:audit_logs"}),
        policies=frozenset({POLICIES["pol-hipaa-phi-access"]}),
        data_boundary=BOUNDARIES["hc-compliance"],
        version=SkillVersion(2, 0, 0, "HIPAA-v2"),
        semantic_tags=frozenset({"compliance", "hipaa", "audit", "patient_privacy", "thorough_review"}),
        min_authority_level=AL.DEPARTMENT,
    ),
    AgentSkill(
        id="hc-hc-02", name="De-identification Engine",
        description="De-identifies PHI for research/analytics use",
        input_schema=_ts([("patient_records", B.JSON_ARRAY)], {SA.PHI, SA.HIPAA_PROTECTED}),
        output_schema=_ts([("deidentified_records", B.JSON_ARRAY), ("method", B.TEXTUAL)]),
        required_permissions=frozenset({"read:patient_records", "write:deidentified_data"}),
        policies=frozenset({POLICIES["pol-hipaa-phi-access"]}),
        data_boundary=BOUNDARIES["hc-compliance"],
        version=SkillVersion(1, 0, 0, "HIPAA-v2"),
        semantic_tags=frozenset({"compliance", "deidentification", "patient_privacy", "data_minimization"}),
        min_authority_level=AL.DEPARTMENT,
    ),
    AgentSkill(
        id="hc-hc-03", name="Breach Detection",
        description="Detects potential HIPAA breaches in data flows",
        input_schema=_ts([("data_flow_log", B.JSON_ARRAY)]),
        output_schema=_ts([("breach_alerts", B.JSON_ARRAY), ("severity", B.CATEGORICAL)]),
        required_permissions=frozenset({"read:data_flow_logs"}),
        policies=frozenset({POLICIES["pol-hipaa-phi-access"]}),
        data_boundary=BOUNDARIES["hc-compliance"],
        version=SkillVersion(1, 1, 0, "HIPAA-v2"),
        semantic_tags=frozenset({"compliance", "breach_detection", "security", "patient_privacy"}),
        min_authority_level=AL.DEPARTMENT,
    ),
    AgentSkill(
        id="hc-hc-04", name="Compliance Report Generator",
        description="Generates HIPAA compliance reports",
        input_schema=_ts([("access_log", B.JSON_ARRAY), ("violation_flags", B.JSON_ARRAY)]),
        output_schema=_ts([("compliance_report", B.BINARY), ("compliance_score", B.NUMERIC)]),
        required_permissions=frozenset({"read:audit_logs", "write:reports"}),
        policies=frozenset({POLICIES["pol-hipaa-phi-access"]}),
        data_boundary=BOUNDARIES["hc-compliance"],
        version=SkillVersion(1, 0, 0, "HIPAA-v2"),
        semantic_tags=frozenset({"compliance", "reporting"}),
        min_authority_level=AL.DEPARTMENT,
    ),
]

# ── HC-Agent-6: Medical Records ──────────────────────────────────────────
hc_skills_records = [
    AgentSkill(
        id="hc-mr-01", name="Record Retrieval",
        description="Retrieves patient medical records from EHR",
        input_schema=_ts([("patient_id", B.TEXTUAL), ("record_types", B.JSON_ARRAY)]),
        output_schema=_ts([("records", B.JSON_OBJECT), ("last_updated", B.TEMPORAL)],
                          {SA.PHI, SA.HIPAA_PROTECTED}),
        required_permissions=frozenset({"read:patient_records"}),
        policies=frozenset({POLICIES["pol-hipaa-phi-access"]}),
        data_boundary=BOUNDARIES["hc-records"],
        version=SkillVersion(3, 0, 0, "HIPAA-v2"),
        semantic_tags=frozenset({"records", "ehr", "retrieval", "patient_privacy"}),
        min_authority_level=AL.TEAM,
    ),
    AgentSkill(
        id="hc-mr-02", name="Record Summarization",
        description="Generates structured summaries of medical records",
        input_schema=_ts([("records", B.JSON_OBJECT)], {SA.PHI, SA.HIPAA_PROTECTED}),
        output_schema=_ts([("summary", B.JSON_OBJECT), ("key_findings", B.JSON_ARRAY)],
                          {SA.PHI, SA.HIPAA_PROTECTED}),
        required_permissions=frozenset({"read:patient_records"}),
        policies=frozenset({POLICIES["pol-hipaa-phi-access"]}),
        data_boundary=BOUNDARIES["hc-records"],
        version=SkillVersion(1, 1, 0, "HIPAA-v2"),
        semantic_tags=frozenset({"records", "summarization", "patient_privacy"}),
        min_authority_level=AL.TEAM,
    ),
    AgentSkill(
        id="hc-mr-03", name="Record Update",
        description="Updates patient records with new clinical data",
        input_schema=_ts([("patient_id", B.TEXTUAL), ("new_data", B.JSON_OBJECT)],
                         {SA.PHI, SA.HIPAA_PROTECTED}),
        output_schema=_ts([("update_status", B.CATEGORICAL), ("record_version", B.TEXTUAL)],
                          {SA.PHI}),
        required_permissions=frozenset({"read:patient_records", "write:patient_records"}),
        policies=frozenset({POLICIES["pol-hipaa-phi-access"]}),
        data_boundary=BOUNDARIES["hc-records"],
        version=SkillVersion(2, 0, 0, "HIPAA-v2"),
        semantic_tags=frozenset({"records", "update", "patient_privacy", "broad_access"}),
        min_authority_level=AL.DEPARTMENT,
    ),
]

# ═══════════════════════════════════════════════════════════════════════════
# BUILD AGENTS
# ═══════════════════════════════════════════════════════════════════════════

ALL_AGENTS = [
    Agent("fs-agent-1", "Portfolio Analysis Agent", "financial_services",
          fs_skills_portfolio, PRINCIPALS["dept-portfolio"]),
    Agent("fs-agent-2", "Risk Assessment Agent", "financial_services",
          fs_skills_risk, PRINCIPALS["dept-risk"]),
    Agent("fs-agent-3", "Regulatory Compliance Agent", "financial_services",
          fs_skills_compliance, PRINCIPALS["dept-compliance-fin"]),
    Agent("fs-agent-4", "Trade Execution Agent", "financial_services",
          fs_skills_trading, PRINCIPALS["dept-trading"]),
    Agent("fs-agent-5", "Audit Reporting Agent", "financial_services",
          fs_skills_audit, PRINCIPALS["dept-audit"]),
    Agent("fs-agent-6", "Client Advisory Agent", "financial_services",
          fs_skills_advisory, PRINCIPALS["dept-advisory"]),
    Agent("hc-agent-1", "Clinical Decision Support Agent", "healthcare",
          hc_skills_clinical, PRINCIPALS["dept-clinical"]),
    Agent("hc-agent-2", "Diagnostic Analysis Agent", "healthcare",
          hc_skills_diagnostics, PRINCIPALS["dept-diagnostics"]),
    Agent("hc-agent-3", "Treatment Planning Agent", "healthcare",
          hc_skills_treatment, PRINCIPALS["dept-treatment"]),
    Agent("hc-agent-4", "Insurance Verification Agent", "healthcare",
          hc_skills_insurance, PRINCIPALS["dept-insurance"]),
    Agent("hc-agent-5", "HIPAA Compliance Agent", "healthcare",
          hc_skills_compliance, PRINCIPALS["dept-compliance-hc"]),
    Agent("hc-agent-6", "Medical Records Agent", "healthcare",
          hc_skills_records, PRINCIPALS["dept-records"]),
]

ALL_SKILLS = []
for agent in ALL_AGENTS:
    ALL_SKILLS.extend(agent.skills)

FS_AGENTS = [a for a in ALL_AGENTS if a.domain == "financial_services"]
HC_AGENTS = [a for a in ALL_AGENTS if a.domain == "healthcare"]

FS_SKILLS = [s for a in FS_AGENTS for s in a.skills]
HC_SKILLS = [s for a in HC_AGENTS for s in a.skills]


def get_agent_by_skill_id(skill_id: str):
    """Find which agent owns a given skill."""
    for agent in ALL_AGENTS:
        if agent.get_skill(skill_id):
            return agent
    return None


def get_skill_count_summary():
    """Return skill count summary for validation."""
    return {
        "total_agents": len(ALL_AGENTS),
        "total_skills": len(ALL_SKILLS),
        "financial_services_agents": len(FS_AGENTS),
        "financial_services_skills": len(FS_SKILLS),
        "healthcare_agents": len(HC_AGENTS),
        "healthcare_skills": len(HC_SKILLS),
    }
