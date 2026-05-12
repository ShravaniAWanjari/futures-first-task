from backend.api.services import response_synthesizer as rs


SQL_CONTEXT = """=== SQL EXECUTION RESULTS ===
Executed Query: SELECT platform, SUM(spend_usd) as total_spend FROM marketing_campaigns GROUP BY platform ORDER BY total_spend DESC LIMIT 5;
Returned 5 rows.

platform | total_spend
----------------------
Google Ads | 4237796
Connected TV | 4107160
Instagram Reels | 3364962
TikTok | 2843075
YouTube Shorts | 2131667
"""


def test_metric_sql_synthesis_returns_grounded_bi_summary(monkeypatch):
    monkeypatch.setattr(rs.llm_service, "enabled", False)

    narrative, structured = rs.synthesize_response(
        answer_context=SQL_CONTEXT,
        sources=[],
        confidence=0.95,
        history=[],
        original_query="Provide full performance audit review for total spend by platform",
    )

    assert "Operational data for" not in narrative
    assert "Google Ads" in narrative
    assert structured is not None
    assert structured["table"]["columns"] == ["platform", "total_spend"]
    assert {chart["type"] for chart in structured["charts"]} == {"bar", "line", "pie"}


def test_summary_follow_up_compresses_previous_answer(monkeypatch):
    monkeypatch.setattr(rs.llm_service, "enabled", False)

    previous_answer = """## Google Ads Leads Spend

### Executive Takeaway
**Google Ads** delivers the highest spend at **4.2M**, ahead of **Connected TV** at **4.1M**.

### Performance Snapshot
- **Instagram Reels** remains the third-largest channel.
- Total observed spend across the result set is **16.7M**.
"""

    narrative, structured = rs.synthesize_response(
        answer_context=previous_answer,
        sources=[],
        confidence=0.95,
        history=[{"role": "assistant", "content": previous_answer}],
        original_query="summarize this for me",
    )

    assert structured is None
    assert narrative.startswith("## Executive Summary")
    assert "chart only response" not in narrative.lower()
    assert len(narrative) < len(previous_answer)


def test_sanitizer_removes_internal_control_text():
    cleaned = rs._sanitize_narrative_output(
        "charts only response\n<thinking>internal notes</thinking>\n## MANAGEMENT RECOMMENDATION\n\nReal content"
    )

    assert "charts only response" not in cleaned.lower()
    assert "internal notes" not in cleaned
    assert "### Strategic Implication" in cleaned


def test_metric_bucket_does_not_force_pie_chart(monkeypatch):
    monkeypatch.setattr(rs.llm_service, "enabled", False)

    narrative, structured = rs.synthesize_response(
        answer_context="""## Mixed Metrics

| Metric | Value |
|---|---|
| Total Subscribers | 45800000 |
| Users | 41200000 |
| Subscriber Churn | 5.8 |
| Contribution | 3.2 |
""",
        sources=[],
        confidence=0.95,
        history=[],
        original_query="Summarize these key metrics",
    )

    assert structured is not None
    assert "pie" not in {chart["type"] for chart in structured["charts"]}


def test_top_titles_block_is_reformatted_into_table():
    output = rs._format_all_flattened_tables(
        "content performance top titles this quarter Galaxy Burn Sci-Fi 84% APAC Shadow Circuit Thriller 73% North America HarborLine Drama 66% Europe"
    )

    assert "| Title | Genre | Avg Completion | Primary Region |" in output


def test_device_share_block_is_reformatted_into_table():
    output = rs._format_all_flattened_tables(
        "device usage Device Share Mobile 73% Smart TV 17% Desktop 7% Tablet 3%"
    )

    assert "| Device | Share |" in output
