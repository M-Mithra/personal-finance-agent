# 1. Data Design Overview

This document defines the logical data design for the Personal Finance Agent. It builds on the problem and objectives in `docs/01_problem_and_objectives.md`, the requirements in `docs/02_requirements.md`, the system boundaries in `docs/03_system_design.md`, and the agent behavior in `docs/04_agent_design.md`.

Transaction data is the primary data domain because the initial system is intended to help a person understand spending behavior from records of financial activity. The quality, meaning, and traceability of those records directly affect every downstream calculation, pattern, interpretation, and verification step.

The design distinguishes source or raw transaction information from the internal representation used for analysis. Source data preserves what was supplied by an input source, including source-specific names and imperfections. A canonical transaction representation organizes relevant information consistently for filtering, aggregation, comparison, categorization, pattern detection, and verification. Derived analytical information, agent context, analytical results, and verification evidence are separate conceptual outputs rather than replacements for the source record.

The goal at this stage is to establish a stable logical data model before choosing file formats, storage mechanisms, libraries, data vendors, or other implementation details. Exact input formats, data sources, persistence, and categorization mechanisms remain TBD.

# 2. Data Design Goals

## 2.1 Correctness

Transaction values, dates, directions, and scopes must have clear semantics so that calculations reflect the underlying records. Ambiguous data should not silently become a precise-looking result.

## 2.2 Consistency

Equivalent information from different source representations should be comparable where the source supports that comparison. Consistent internal semantics reduce errors in filtering, aggregation, and period comparison.

## 2.3 Traceability

Normalized values, derived results, and important insights should remain connected to source records and the transformations applied to them. This supports grounded responses and independent verification.

## 2.4 Data quality

Missing, malformed, duplicate, conflicting, and ambiguous records must be detectable and their impact must be visible. Data quality is part of the analytical problem, not merely an ingestion concern.

## 2.5 Analytical usefulness

The model should provide the fields needed by the initial spending analyses without requiring every possible financial field. It should support relevant filtering, grouping, aggregation, comparison, and pattern analysis.

## 2.6 Temporal analysis

Dates and optional time information must support daily, weekly, monthly, and other explicitly defined period analyses while making incomplete or ambiguous periods visible.

## 2.7 Categorization support

The model should accept source categories, derived categories, and unresolved categories without forcing false certainty. Category origin and uncertainty should remain understandable.

## 2.8 Pattern detection

The data should support analysis of recurrence, changes, concentration, unusual values, and other collective patterns when sufficient history and fields are available.

## 2.9 Verification support

Analytical outputs should retain enough scope, source references, inclusion rules, and intermediate information for important calculations and interpretations to be checked.

## 2.10 Privacy

The model should minimize unnecessary collection, duplication, exposure, persistence, and logging of sensitive personal financial information.

## 2.11 Simplicity

The initial model should contain only fields and boundaries justified by transaction/spending analysis requirements. It should be implementable without infrastructure intended only for hypothetical future capabilities.

## 2.12 Extensibility

The logical boundaries should allow additional sources, accounts, currencies, analytical capabilities, and persistence later without requiring the initial transaction semantics to be discarded.

# 3. Data Scope

## 3.1 In scope

The initial data model covers:

- Personal transaction data.
- Spending-related transaction information.
- Transaction dates and optional timestamps.
- Transaction amounts and currencies where available.
- Transaction descriptions.
- Transaction direction or type where available.
- Merchant information where available.
- Categories where supplied or derived.
- Account or payment-source information where relevant and available.
- Source references and data-quality information needed for traceability.
- Derived information required for spending, category, contributor, temporal, recurring, and noteworthy-activity analyses.

## 3.2 Out of scope

The initial data model does not include schemas for:

- Investment portfolios or securities-market data.
- Tax records or tax-filing information.
- Loan records or credit-scoring data.
- Payment execution data.
- Banking credentials or authentication secrets.
- Financial-product catalogs or recommendations.
- External banking operations.
- User identity and authentication data beyond what is necessary to define a later system boundary.

These areas are outside the initial project scope and should not be added to the transaction model speculatively.

# 4. Data Lifecycle

The conceptual lifecycle is:

```text
Source Data
  -> Ingestion
  -> Validation
  -> Normalization
  -> Categorization / Enrichment
  -> Analytical Use
  -> Agent Context
  -> Verification Evidence
  -> User Insight
```

## 4.1 Source data

Source data is the transaction information supplied by a user or an approved input source. It may contain source-specific field names, formats, identifiers, descriptions, and missing values. It should be preserved as the original basis of later processing where practical.

## 4.2 Ingestion

Ingestion makes source records available for processing within the supported input scope. The exact ingestion mechanism and file or interaction format are TBD.

## 4.3 Validation

Validation checks whether records are structurally formed, semantically meaningful, and suitable for the requested analysis. Invalid or questionable records should receive an explicit handling outcome rather than disappearing silently.

## 4.4 Normalization

Normalization maps source-specific representations into consistent internal semantics, such as a common date meaning, amount meaning, direction, and comparable text fields. It should preserve the source value and record uncertainty when a mapping is not reliable.

## 4.5 Categorization and enrichment

Categorization assigns or preserves spending groups when the available information supports them. Other enrichment may include normalized merchant information or analytical flags. The method is TBD, and derived values must remain distinguishable from source values.

## 4.6 Analytical use

Analytical capabilities consume validated canonical transactions and produce totals, groupings, comparisons, patterns, and evidence references. Derived results are not automatically permanent data records.

## 4.7 Agent context

The agent receives only the relevant transaction-derived information, analytical results, metadata, assumptions, limitations, and verification status needed to decide and interpret. It does not need the complete raw dataset for every action.

## 4.8 Verification evidence

Verification evidence connects important results to source transactions, periods, filters, transformations, and calculations. It supports independent checking before an insight is presented.

## 4.9 User insight

The final insight is a grounded response built from verified or explicitly qualified analytical results. It should not replace the source or canonical data representation.

# 5. Source / Raw Transaction Data

Source systems may provide different subsets and meanings. The following table describes conceptual fields that may occur in source records.

| Field | Meaning | Typical Type | Required? | Notes |
|---|---|---|---|---|
| Transaction identifier | Source-provided identifier for a record | Text | Optional/source-dependent | Useful for deduplication and traceability; not all sources provide one. |
| Date/time | Date or timestamp associated with the transaction | Date or timestamp | Conceptually required for time-based analysis | The source may provide a date only, an exact timestamp, or an unclear date meaning. |
| Amount | Monetary value recorded by the source | Numeric or text before parsing | Conceptually required for amount-based analysis | Sign and debit/credit semantics may vary by source. |
| Currency | Currency associated with the amount | Text/code | Optional/source-dependent | Multiple currencies require explicit handling; conversion is not assumed. |
| Description | Source text describing the activity | Text | Expected where available | May contain merchant identifiers, abbreviations, or processing artifacts. |
| Merchant | Merchant or counterparty identified by the source | Text | Optional/source-dependent | May be absent, inconsistent, or less reliable than it appears. |
| Transaction type/direction | Source classification such as debit, credit, transfer, refund, or income | Text or enumerated value | Optional/source-dependent | Source values must be mapped carefully to internal semantics. |
| Account/payment source | Account, card, or payment instrument associated with the record | Text or reference | Optional/source-dependent | Relevant when multiple sources are combined or filtering requires it. |
| Category | Source-provided spending category | Text or hierarchy reference | Optional/source-dependent | May be absent, inconsistent, or based on an unknown taxonomy. |
| Balance after transaction | Account balance following the transaction | Numeric | Optional/source-dependent | Not required for initial spending analyses and should not be assumed to be reliable. |
| Source-specific metadata | Additional fields supplied by the source | Structured metadata | Optional/source-dependent | Retain only when needed for traceability, validation, or approved analysis. |

## 5.1 Required conceptual information

For the initial spending analyses, a usable record generally needs:

- An interpretable date or time value for time-based questions.
- An interpretable amount for amount-based questions.
- Enough description, merchant, category, or other identifying information for the requested grouping or interpretation.

The exact required fields depend on the requested analysis. A record may be valid for one analysis and insufficient for another.

## 5.2 Optional and source-dependent information

Currency, merchant, direction, account, category, balance, and source metadata may be unavailable. The system must not treat an absent optional field as evidence that the corresponding fact is unknown in a particular way, and it must not invent a replacement value.

The exact file format, source strategy, and field names remain TBD.

# 6. Canonical Transaction Model

The canonical transaction model is the internal logical representation used after validation and normalization. It should remain small while preserving source values and enough information for analysis and traceability.

| Field | Purpose | Required? | Source / Derived |
|---|---|---|---|
| `transaction_id` | Stable identity for the canonical record within the supported data scope | Required for internal traceability | Source identifier when reliable, otherwise a later-defined equivalent reference |
| `date` | Supports period filtering and temporal analysis | Required for analyses that use time | Normalized from source date/time |
| `timestamp` | Preserves finer time information when available | Optional | Normalized from source timestamp; absent when the source provides only a date |
| `amount` | Represents the monetary magnitude used by calculations | Required for amount-based analyses | Normalized from source amount; semantic meaning defined in Section 7 |
| `currency` | Identifies the currency of the amount | Required when the source supplies or analysis requires it | Source value normalized to a consistent representation; exact representation TBD |
| `direction` | Distinguishes expense, income/credit, transfer, refund, or unresolved direction | Required for spending analyses when direction is needed | Mapped from source type, sign, or other evidence; may be unknown |
| `description` | Provides a usable transaction description for analysis and response | Required where a description exists; may be unknown | Normalized source description |
| `merchant` | Supports contributor and recurring analyses | Optional | Source merchant or a derived normalized merchant, with origin recorded |
| `category` | Supports category grouping | Optional | Source or derived category; may be unknown or uncertain |
| `account_source` | Supports account/payment-source filtering and traceability | Optional | Source value where available |
| `original_description` | Preserves the source description exactly or as supplied | Optional but preferred when a description exists | Source |
| `normalized_description` | Supports comparison of similar descriptions | Optional | Derived through normalization; must not replace the original |
| `source_reference` | Connects the canonical record to its source record or source scope | Required for important traceability where available | Source reference or equivalent internal linkage |
| `data_quality_status` | Summarizes whether the record is usable, flagged, incomplete, or unresolved | Required | Derived from validation findings |
| `quality_notes` | Explains material validation or normalization concerns | Optional | Derived from validation and transformation steps |
| `category_origin` | Indicates whether category information was supplied, derived, or unresolved | Optional when category is absent | Derived metadata |
| `normalization_status` | Indicates whether relevant fields were normalized successfully or with uncertainty | Required for traceability of transformations | Derived metadata |

The canonical model should support filtering, aggregation, comparison, categorization, pattern detection, traceability, and verification without requiring every source field to be present. It should not include balances, credentials, tax attributes, investment fields, or other information outside the initial scope merely for future possibilities.

The exact schema, field types, nullability rules, and serialization remain TBD for data design and implementation.

# 7. Transaction Semantics

## 7.1 Amount

The canonical amount should represent the absolute monetary value of the transaction, with transaction direction represented separately. This avoids relying on inconsistent source sign conventions for the meaning of spending.

For example, an expense of 50 and an income/credit of 50 should have the same magnitude but different directions. The source sign, debit/credit notation, and any original amount text should remain available for traceability when relevant. If direction cannot be determined reliably, the amount should not be silently treated as spending.

This is a logical semantic decision, not a requirement for a particular numeric storage type. The exact precision and representation are TBD.

## 7.2 Direction

The canonical direction should conceptually distinguish at least:

- **Expense/debit:** Money leaving the user's spending scope.
- **Income/credit:** Money entering the user's financial scope.
- **Transfer:** Movement between accounts or sources rather than spending or income, when identifiable.
- **Refund/reversal:** A reversal or return associated with previous activity, when identifiable.
- **Unknown/unresolved:** Direction cannot be established reliably.

The exact source-to-direction mapping is TBD. Analyses must state how each direction is included or excluded.

## 7.3 Date and time

The canonical `date` represents the date used for period analysis. An optional `timestamp` preserves finer-grained time when supplied. The system should distinguish a source transaction date from a posting date or other date if the source makes that distinction available.

Timezone interpretation matters when timestamps cross day or period boundaries. The initial design should preserve source timezone information where it is relevant, but no timezone policy is selected yet. Period boundaries must be explicit when a result depends on them.

## 7.4 Currency

Currency identifies the monetary unit of an amount. Amounts in different currencies must not be aggregated as if they were comparable without an explicitly defined conversion or separate-currency treatment. Currency conversion is not part of the current requirements and is therefore TBD rather than assumed.

## 7.5 Merchant and description

The raw or original description is source evidence. A normalized description is a derived comparison aid. Merchant information is a separate conceptual field because a source may identify a merchant directly, provide only free text, or provide a description that cannot safely be treated as a merchant.

A derived merchant grouping must remain distinguishable from a source-provided merchant and should carry uncertainty when different descriptions may refer to different entities or when the same entity appears under several descriptions.

# 8. Data Quality Requirements

| Quality issue | Detection | Conceptual handling | Impact on analysis |
|---|---|---|---|
| Missing required field | Check required information for the requested analysis | Reject, flag, exclude, or request correction depending on impact | The affected record or analysis may be unusable or incomplete. |
| Missing optional field | Check field availability before an operation | Retain the record with an unknown value and communicate the limitation | Merchant, category, account, or pattern analyses may be less complete. |
| Invalid date | Parse and semantically check date values | Flag or exclude from time-dependent analyses; preserve source value | Period totals and comparisons may be incomplete. |
| Invalid amount | Parse and check amount semantics | Flag or exclude from amount-dependent analyses; never silently coerce | Totals, rankings, and patterns may be unreliable. |
| Duplicate transaction | Compare source identifiers and relevant record attributes where possible | Flag, isolate, or apply a later-defined deduplication policy | Totals and counts may be inflated. |
| Inconsistent description | Compare text representations and merchant evidence | Normalize for comparison while preserving original text and uncertainty | Contributor and recurring analysis may be ambiguous. |
| Inconsistent transaction type | Compare source type, sign, direction, and related fields | Flag conflicts and avoid unsupported direction mapping | Spending versus income or transfer totals may be wrong. |
| Malformed record | Check structural parseability and required shape | Reject or isolate the record with a reason | The record should not silently enter analysis. |
| Unexpected currency | Validate currency presence and compatibility | Keep separate, flag, or require later handling | Cross-currency aggregation may be unavailable. |
| Incomplete merchant information | Check merchant and description availability | Use available evidence with qualification or omit contributor analysis | Merchant and recurring conclusions may be weaker. |
| Conflicting information | Compare fields that imply different meanings | Preserve the conflict and prevent unsupported resolution | The record may require clarification or exclusion. |

Quality handling should be proportional to the requested analysis. A missing merchant may not prevent a total, while a missing amount prevents an amount-based total. No universal data-quality threshold is defined at this stage.

# 9. Data Validation

Validation should occur at three conceptual levels.

## 9.1 Structural validation

Structural validation asks whether the record is correctly formed for the supported input scope. It includes:

- Expected fields or source equivalents are identifiable.
- Values can be parsed into the expected conceptual types.
- Required record boundaries are present.
- The record is not truncated or malformed in a way that prevents interpretation.

A structurally invalid record may be rejected or isolated before normalization.

## 9.2 Semantic validation

Semantic validation asks whether the values make sense together. It includes:

- Date values are valid and interpretable.
- Amount values are valid and their source meaning is understood.
- Direction and amount semantics are not contradictory without explanation.
- Currency information is valid enough for the intended analysis.
- Merchant, description, category, and account relationships are not silently misrepresented.
- Duplicate or conflicting records are identified where possible.

A semantically questionable record may be retained with a warning, excluded from affected analyses, or sent for correction depending on impact.

## 9.3 Analytical validation

Analytical validation asks whether the dataset behaves consistently when used for analysis. It includes:

- Period filters select the intended records.
- Complete and incomplete periods are distinguished.
- Spending totals use consistent direction and inclusion rules.
- Grouped results reconcile with the selected transaction scope where expected.
- Duplicate or invalid records do not silently distort results.
- Comparison periods are comparable for the requested conclusion.

Analytical validation can identify a dataset that is structurally valid but unsuitable for a particular question.

## 9.4 Validation outcomes

Possible outcomes include:

- Reject the record or dataset.
- Flag the record for review.
- Exclude the record from a specific analysis.
- Retain the record with a warning.
- Request correction or clarification.
- Continue with a qualified result when the remaining evidence is sufficient.

The appropriate outcome depends on how material the issue is to the requested analysis. The exact rules are TBD.

# 10. Data Normalization

Normalization maps equivalent source representations into consistent internal meanings without claiming to recover information that does not exist.

Potential normalization areas include:

- Date and timestamp formats.
- Amount representation and source sign conventions.
- Transaction direction and type values.
- Whitespace, casing, and obvious formatting differences in descriptions.
- Merchant names and source-specific merchant labels.
- Category labels and category origins.
- Duplicate representations of source fields.
- Source-specific field names mapped to canonical concepts.

Normalization should preserve original values, source references, transformation status, and material uncertainty. It should make comparable values easier to analyze without erasing evidence.

## 10.1 Normalization versus data correction

**Normalization** changes representation while preserving the intended information, such as converting several date formats into one date meaning or standardizing harmless text variation.

**Data correction** changes a value because the source is believed to be wrong, incomplete, or contradictory. Correction requires evidence or an explicit external decision and should not be implied merely because a value looks unusual.

The system may normalize a description for grouping, but it should not silently rename an unknown merchant, infer a missing category as certain, or change an amount because it appears implausible. The exact normalization rules are TBD.

# 11. Transaction Categorization

## 11.1 Purpose

Categorization groups transactions into meaningful spending areas for category totals, comparisons, contributor analysis, and pattern interpretation. It is useful but uncertain: descriptions may be incomplete, a transaction may fit multiple categories, and source categories may use different taxonomies.

## 11.2 Category requirements

The data model should support:

- A category value when one is supplied or derived.
- An unknown or unclassified category.
- Category origin, such as source-provided, derived, or unresolved.
- Category uncertainty or qualification where meaningful.
- A category hierarchy or multiple levels if later requirements justify it.
- Traceability from a category back to the transaction and the basis for the assignment.

The MVP should not require a complex category hierarchy unless the selected use cases need one. A simple category representation is preferred initially.

## 11.3 Uncertainty

An uncertain category must not be presented as an established fact. Records may remain unclassified, carry multiple candidates, or be grouped at a broader level when the evidence supports that approach. The selected handling should be visible in relevant analytical results.

## 11.4 Possible approaches

Categorization could conceptually use:

- Rules.
- Deterministic mappings.
- Machine-learning methods.
- Language-model reasoning.
- Hybrid approaches.

No final approach is selected here. The categorization strategy should be determined later using data quality, evaluation results, implementation constraints, and traceability requirements.

# 12. Derived Data

Derived data is calculated or inferred from canonical transactions rather than directly supplied by the source.

Examples include:

- Spending totals.
- Income totals.
- Category totals.
- Merchant or contributor totals.
- Transaction counts.
- Period-level aggregates.
- Period-over-period absolute or relative changes.
- Recurring-transaction indicators.
- Unusual-activity indicators.
- Trend-related information.
- Normalized merchant or description values.
- Category origin and uncertainty.
- Data-quality and completeness summaries.

Raw fields must remain distinguishable from these derived results. A derived value should retain its scope, calculation basis, source references, and limitations where it may support an important insight.

Derived information may be computed dynamically for a request rather than stored permanently. The system should avoid persisting every aggregate, flag, or intermediate result by default. Persistence decisions depend on later requirements.

# 13. Analytical Data Requirements

| Analytical Capability | Required Data | Important Constraints |
|---|---|---|
| Total spending | Date, amount, direction, currency where relevant, and source scope | Must distinguish expense from income, transfer, and refund where possible; invalid amounts cannot silently enter the total. |
| Category analysis | Date, amount, direction, category, category origin, and uncertainty | Missing or uncertain categories must be visible; category totals may not cover all spending. |
| Merchant analysis | Date, amount, direction, merchant or description, normalized comparison information | Similar descriptions must not be merged without adequate support; missing merchant data limits the result. |
| Period comparison | Date, amount, direction, currency, and consistent inclusion rules | Period boundaries and complete versus incomplete periods must be explicit. |
| Contributor analysis | Amount, direction, merchant/category/grouping dimension, and relevant period | Contributors should be traceable to transactions and should support reconciliation where practical. |
| Recurring spending | Date or timestamp, amount, direction, merchant/description, and sufficient history | Repetition is evidence of a pattern, not proof of a subscription, authorization, or cause. |
| Unusual/noteworthy activity | Amount, date, direction, relevant baseline history, and comparison scope | A reason for flagging must be explainable; unusual does not mean fraudulent or erroneous. |
| Trend analysis | Date, amount, direction, grouping dimension, and multiple comparable periods | Irregular frequency, incomplete periods, and missing data can weaken conclusions. |

A capability should report when required fields are unavailable or when the available data only supports a qualified result. The exact set of MVP capabilities remains TBD.

# 14. Temporal Data Design

The canonical date should support at least the following conceptual periods:

- Day.
- Week.
- Month.
- Custom user-specified periods.
- Other periods selected by a later requirement.

Period analysis requires explicit start and end boundaries, inclusion rules, and treatment of timestamps. A transaction should belong to a period based on a defined date or timestamp interpretation, not an implicit assumption hidden in the result.

## 14.1 Period comparison

Comparisons should identify both periods, their boundaries, their completeness, the included transaction directions, and any relevant data-quality limitations. A complete month should not be compared to an incomplete current month without making that difference visible.

## 14.2 Dates and boundaries

Missing dates prevent reliable time filtering for the affected record. Invalid dates should be flagged or excluded from time-dependent analysis. Timezone interpretation may change the day or period for a timestamp near a boundary and therefore remains an explicit design consideration.

## 14.3 Irregular frequency

Transactions do not necessarily occur at regular intervals. Recurrence and trend analysis must account for irregular transaction frequency rather than treating missing days or variable counts as evidence of behavior change without qualification.

No time-series database or specialized temporal storage is required or selected.

# 15. Traceability and Evidence

The conceptual relationship is:

```text
Transaction
  -> Analysis
  -> Result
  -> Evidence
  -> Insight
```

An important result should remain connected to:

- Relevant canonical transactions.
- Source references where available.
- Applied filters and grouping dimensions.
- Comparison periods and boundaries.
- Direction and inclusion rules.
- Normalization or categorization transformations.
- Aggregation or pattern-analysis outputs.
- Warnings and limitations.

Traceability does not require exposing every underlying transaction in every response. It requires that the system can identify and inspect the basis of an important conclusion where practical. The exact provenance representation is TBD.

# 16. Agent Data Interface

The data and analysis layers should provide the agent with:

- The user's current request.
- Relevant transaction-derived information.
- Analytical results.
- Period, filter, and grouping metadata.
- Assumptions and limitations.
- Data-quality findings.
- Evidence references or supporting transaction subsets where needed.
- Validation and verification results.

The agent should not necessarily receive the entire raw transaction dataset for every request. Passing only relevant derived information and evidence reduces unnecessary exposure, makes context manageable, and reinforces the boundary between data processing and interpretation.

The conceptual boundary is:

**The data layer provides evidence. The agent interprets evidence.**

The data layer and analytical capabilities remain responsible for retrieving and calculating transaction information. The agent decides what analysis is needed and explains verified results, but it should not recreate numerical truth from incomplete context. No actual API, class, or schema is defined here.

# 17. Analytical Result Model

An analytical capability should conceptually return a result containing some or all of the following:

| Element | Purpose |
|---|---|
| Operation performed | Identifies the analysis that produced the result. |
| Parameters and scope | Identifies periods, filters, grouping, direction, currency, and other material choices. |
| Result value or structure | Contains totals, groups, comparisons, candidates, or other output. |
| Relevant period | Makes temporal boundaries explicit. |
| Supporting transactions or references | Connects the result to underlying evidence. |
| Assumptions | Records interpretations used when the request or data was incomplete. |
| Warnings | Identifies material concerns such as duplicate or incomplete records. |
| Data-quality limitations | Explains missing, malformed, ambiguous, or excluded data. |
| Uncertainty | Expresses uncertainty where a pattern, category, or grouping is not definitive. |
| Status | Distinguishes success, partial result, empty result, invalid result, and failure. |
| Verification state | Indicates whether and how the result has been checked. |

The result model should be structured enough for the agent to reason over and for verification to inspect independently. It should not force a single response format or imply that every operation produces the same fields. Exact schemas are TBD.

# 18. Verification Data

Verification requires enough information to independently assess an important result.

## 18.1 Spending total

Evidence should include:

- Source or canonical transactions included.
- Period definition.
- Direction and inclusion/exclusion rules.
- Currency scope.
- Calculated total.
- Excluded or questionable records that may affect the result.

## 18.2 Period comparison

Evidence should include:

- Both period definitions and completeness status.
- Both period totals.
- Absolute difference and percentage change where applicable.
- Consistent filters and direction rules.
- Contributing categories, merchants, or transactions where the explanation requires them.

## 18.3 Unusual activity

Evidence should include:

- Baseline or reference period.
- Identified transaction or pattern.
- Comparison measure or reason for flagging.
- Relevant amount, date, merchant, category, and source reference.
- Limitations on what the flag means.

Verification should be able to distinguish calculation correctness from interpretation groundedness. The exact verification implementation is TBD.

# 19. Data Privacy Considerations

Transaction data is sensitive personal financial information. The data design should therefore follow these principles:

- Collect and retain only information necessary for approved analysis, validation, traceability, or verification.
- Minimize unnecessary duplication of raw records and derived information.
- Limit each component's access to the fields required for its responsibility where practical.
- Avoid including raw transaction details unnecessarily in logs, execution context, or agent input.
- Distinguish sensitive raw records from less sensitive aggregate insights, while recognizing that aggregates can also reveal personal information.
- Define deletion and lifecycle behavior before persistent storage is introduced.
- Protect data during any future external or model-based interaction through later design decisions.
- Avoid exposing account identifiers, descriptions, or other sensitive fields when they are not needed for the answer.
- Preserve enough evidence for verification without making all source data visible by default.

No encryption technology, cloud provider, authentication system, compliance framework, or hosting model is selected here. Privacy implementation remains TBD.

# 20. Data Storage Considerations

## 20.1 Initial prototype

A simple local data-handling approach may be sufficient for the initial prototype, provided it can support the selected input, analysis, verification, and testing requirements. The prototype does not require a persistent database merely because future growth is possible.

The initial choice should be based on the actual data scope and workflow, including whether data must survive a session or only support one execution. The exact handling method is TBD.

## 20.2 Future evolution

Persistent storage may become useful if later requirements introduce:

- Multiple users.
- Persistent transaction history.
- Larger datasets.
- Conversation persistence.
- Repeated analysis across sessions.
- External integrations.
- Operational retention or deletion requirements.

No database or storage technology is selected. The storage decision will be made during implementation based on actual requirements, data volume, privacy constraints, and operational needs.

# 21. Synthetic vs Real Data Strategy

## 21.1 Synthetic data

Synthetic data is useful because it is safe for development, reproducible, controllable, and suitable for deliberately constructing edge cases such as duplicate transactions, missing fields, refunds, transfers, and incomplete periods. Its limitation is that it may not represent the messy descriptions, source inconsistencies, and unusual patterns found in real records.

## 21.2 Real or anonymized data

Real or appropriately anonymized data can expose realistic descriptions, field omissions, source quirks, merchant variation, and data-quality problems. Its limitations include privacy risk, handling complexity, uncertain permission to use it, and reduced reproducibility.

## 21.3 Initial direction

The initial development and testing strategy should begin with controlled synthetic data so that correctness cases and edge cases are reproducible. Real or anonymized data may be introduced later if it can be used appropriately and if evaluation requirements justify it. No real dataset is assumed or invented here.

The final real-versus-synthetic strategy remains TBD.

# 22. Data Quality and Edge Cases

| Edge case | Expected conceptual treatment |
|---|---|
| Empty dataset | Report that no transaction evidence is available; do not fabricate a zero-spending conclusion unless the scope explicitly establishes that zero is meaningful. |
| Single transaction | Analyze it when fields are sufficient, while recognizing that no broader pattern can be established from one record. |
| Very large dataset | Process within the supported scope and preserve correctness and traceability; quantitative capacity targets are TBD. |
| Duplicate transactions | Detect or flag where possible; prevent duplicate-sensitive results from being presented as certain. |
| Missing description | Retain if other required fields support the analysis; qualify merchant, categorization, or explanation limitations. |
| Missing merchant | Use other evidence only when appropriate; do not invent a merchant identity. |
| Missing category | Use unknown/unclassified or another qualified treatment; do not force a category. |
| Missing date | Exclude from time-dependent analysis or report its impact; do not assign an arbitrary date. |
| Malformed amount | Flag or exclude from amount-based analysis; do not silently coerce it. |
| Zero-value transaction | Retain or flag according to source meaning; assess whether it affects the requested analysis. |
| Unusually large transaction | Preserve and potentially flag as noteworthy only with an explicit comparison basis; do not imply error or fraud. |
| Refund | Represent distinctly when identifiable and apply an explicit inclusion rule. |
| Transfer | Represent distinctly when identifiable so it is not silently counted as spending. |
| Income mixed with expenses | Separate by direction where possible; report limitations when direction is unresolved. |
| Recurring transactions | Preserve timing, amount, and identity evidence; treat recurrence as a candidate pattern rather than proof of a subscription. |
| Same merchant with different descriptions | Normalize or group only where evidence supports it; preserve source descriptions and uncertainty. |
| Same description for different merchants | Avoid assuming a single merchant when the source does not establish one. |
| Multiple currencies | Keep currencies separate or require a later-defined treatment; do not aggregate incomparable amounts. |
| Incomplete month | Mark period completeness and qualify comparisons or trends that depend on it. |
| Negative/positive sign inconsistencies | Use explicit direction semantics and flag conflicting source conventions. |

The exact rules for each edge case remain subject to data design, implementation, and evaluation. The key principle is that uncertainty or invalidity must not disappear silently.

# 23. Data Design for Future Extensibility

The logical model should be able to evolve toward:

- Multiple accounts and payment sources.
- Multiple transaction sources.
- Multiple currencies.
- Additional financial data only if later scope approves it.
- Persistent storage.
- External integrations.
- Richer categorization.
- Additional analytical capabilities.

The following boundaries should remain stable enough to support that evolution:

- Source records remain distinguishable from canonical records.
- Canonical transaction semantics for amount, direction, date, and traceability remain explicit.
- Analytical capabilities consume a defined transaction/data boundary rather than source-specific formats directly.
- Derived results retain scope and evidence references.
- Agent context remains separate from raw data and analytical storage.
- Verification can inspect results and evidence without depending on response wording.

These boundaries do not require schemas for every future domain. Future fields should be added only when requirements justify them.

# 24. Data Design Alternatives

## Option A - Use raw source data directly

This is simple initially and avoids a transformation step, but it would make analysis dependent on source-specific formats and sign conventions. It would weaken consistency, data-quality handling, and support for multiple sources, while making traceability and verification more difficult to standardize.

## Option B - Normalize everything into a canonical model

This provides a consistent analytical surface and may simplify calculations, but it risks losing source-specific evidence or flattening uncertainty if original values are discarded. It may also force unsupported assumptions when sources do not provide equivalent information.

## Option C - Preserve raw and canonical representations

This approach retains source/raw information for traceability while maintaining a normalized canonical representation for analysis. It requires a deliberate transformation boundary, but it supports data quality, reproducibility, verification, and future source variation without making the analytical layer source-specific.

| Option | Simplicity | Traceability | Data quality | Analytical reliability | Extensibility |
|---|---|---|---|---|---|
| Raw source directly | High initially | Source-dependent | Limited | Variable | Low to medium |
| Canonical only | Medium | Weaker if source values are discarded | Strong if normalization is reliable | Strong for comparable data | Medium |
| Raw plus canonical | Medium | Strong | Strong with explicit status | Strong | Strong |

The preferred direction is **preserve source/raw information while maintaining a normalized canonical representation for analysis**. This is a logical data-design decision, not a selection of storage technology.

# 25. Initial Data Design Decision

The initial system should conceptually use:

```text
Source Transaction Data
  -> Validation
  -> Canonical Transaction Representation
  -> Derived / Analytical Information
  -> Agent Context
  -> Verification Evidence
  -> Grounded Insight
```

The canonical model should preserve traceability to source information and should use explicit semantics for amount, direction, date, currency, description, merchant, category, and quality status where those concepts are available.

The initial data model should remain small and focused on transaction and spending analysis. It should support the selected MVP analyses without designing schemas for investments, taxes, banking operations, payment execution, or other out-of-scope domains.

No database, external financial source, data vendor, cloud storage, or specialized data platform is required or selected. Persistent storage should be introduced only if later requirements justify it.

# 26. Data Design Decisions and Rationale

| Decision | Rationale | Status |
|---|---|---|
| Use a canonical transaction representation | Consistent internal semantics are needed for filtering, aggregation, comparison, categorization, and pattern analysis. | Decided |
| Preserve source information | Original values and source references are necessary for traceability, quality review, and verification. | Decided |
| Treat data quality as a first-class concern | Missing, malformed, duplicate, and ambiguous records can materially affect spending insights. | Decided |
| Represent transaction direction explicitly | Separate direction avoids relying on inconsistent source sign conventions to define spending. | Decided |
| Separate raw data from derived analytical results | Source evidence should not be confused with calculated totals, flags, or interpretations. | Decided |
| Support temporal analysis | Dates and explicit period boundaries are central to spending comparisons and trends. | Decided |
| Support category uncertainty | Categories may be absent, inferred, or ambiguous and must not be represented as certain without support. | Decided |
| Keep verification evidence available | Important results must be independently checkable against data and calculation scope. | Decided |
| Avoid storing unnecessary derived information | Many aggregates and flags can be computed for a request; permanent storage requires justification. | Decided |
| Start with a simple data model | The MVP should support transaction/spending analysis without hypothetical financial domains. | Decided |
| Preserve future extensibility through boundaries | Raw/canonical separation and explicit result evidence allow future sources and capabilities to be added. | Decided |
| Select exact source formats and schema | Source strategy and detailed field rules depend on later data and implementation work. | TBD |
| Select categorization method | Rules, mappings, model-based, or hybrid categorization requires evaluation and implementation evidence. | TBD |
| Select persistence and retention approach | Storage and lifecycle depend on actual scope, privacy, volume, and session requirements. | TBD |

# 27. Open Questions / TBD

The following data-design questions remain unresolved:

- What exact input format or formats will the MVP accept?
- What exact canonical schema, field types, and nullability rules will be implemented?
- Which fields are required for each supported analysis, and which are optional?
- What category taxonomy, if any, will be used?
- Will categorization use rules, mappings, machine learning, language-model reasoning, or a hybrid approach?
- Will development and evaluation use synthetic data, real data, anonymized data, or a combination?
- How will currency be handled when multiple currencies are present?
- How will refunds and reversals be represented and included?
- How will transfers be distinguished from expenses and income?
- What duplicate detection rules are appropriate for the selected data source?
- What evidence and baseline define unusual spending?
- What evidence and minimum history define a recurring transaction pattern?
- What storage mechanism, if any, is needed?
- What persistence requirements exist for the MVP?
- What data retention and deletion behavior is required?
- Will additional external data sources be introduced later?
- What privacy controls are required for raw data, derived results, agent context, and observability?
- What data-volume expectations should inform implementation and testing?
- Which derived values should be computed dynamically versus retained for a session?
- How should source date semantics and timezone information be handled?

These questions remain TBD and should be resolved by later data, implementation, testing, privacy, and evaluation work rather than by assuming a particular technology or source.

# 28. Handoff to Implementation and Testing

This document establishes the logical transaction model, source-to-canonical data lifecycle, validation and normalization requirements, categorization considerations, analytical data requirements, temporal semantics, traceability, verification evidence, privacy principles, storage considerations, synthetic-versus-real data strategy, and important edge cases.

These definitions will be used by `docs/06_implementation.md` to translate the logical design into actual software components. Implementation should preserve the source/canonical distinction, explicit transaction semantics, data-quality status, analytical scope, and evidence relationships established here.

The data model will later support `docs/07_testing_and_evaluation.md`, particularly for:

- Deterministic analytical tests.
- Data-quality and validation tests.
- Normalization tests.
- Categorization and uncertainty tests.
- Temporal and edge-case tests.
- Agent evaluation.
- Verification tests.
- Groundedness evaluation.

The next phases should refine unresolved details through evidence and requirements rather than expanding the data model speculatively.
