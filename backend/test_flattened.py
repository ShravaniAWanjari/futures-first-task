from backend.api.services.response_synthesizer import _extract_flattened_table
import json

test_text_1 = """
Device Usage Trends Device Type Share of Watch Activity Device Type Share of Watch Activity Mobile 56% Smart TV 29% Desktop 9% Tablet 6%
"""

test_text_2 = """
Regional Campaign ROI Summary Region Marketing Spend ROI Conversion Rate APAC $12.8M 4.2x 14.8% North America $8.1M 2.7x 9.2% Europe $7.4M 1.6x 5.1%
"""

print("--- TEST 1 (Flattened Metric) ---")
print(_extract_flattened_table(test_text_1))

print("\n--- TEST 2 (Financial Region) ---")
print(_extract_flattened_table(test_text_2))
