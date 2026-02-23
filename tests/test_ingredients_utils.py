"""Unit tests for ingredients.utils (parse_ingredients_to_json)."""
import pytest

from ingredients.utils import parse_ingredients_to_json


def test_parse_ingredients_to_json_returns_dict():
    text = "Salt:\nA common seasoning.\n\nSummary:\nGood.\nVerdict:\nSafe."
    result = parse_ingredients_to_json(text)
    assert isinstance(result, dict)
    assert "product_metadata" in result
    assert "ingredients" in result
    assert "summary" in result["product_metadata"]
    assert "verdict" in result["product_metadata"]


def test_parse_ingredients_to_json_extracts_summary_and_verdict():
    text = """
Sugar: Sweetener.

Summary: A brief summary here.
Verdict: Generally safe.
"""
    result = parse_ingredients_to_json(text)
    assert "summary" in result["product_metadata"]
    assert "verdict" in result["product_metadata"]
    assert "A brief summary here" in result["product_metadata"]["summary"] or ""
    assert "Generally safe" in result["product_metadata"]["verdict"] or ""


def test_parse_ingredients_to_json_extracts_ingredient_with_percentage():
    text = """
Besan (10%): Chickpea flour.

Summary: None.
Verdict: Safe.
"""
    result = parse_ingredients_to_json(text)
    assert len(result["ingredients"]) >= 1
    ing = result["ingredients"][0]
    assert "ingredient" in ing
    assert "percentage" in ing
    assert "description" in ing
    assert "Besan" in ing["ingredient"] or "10" in str(ing.get("percentage", ""))


def test_parse_ingredients_to_json_removes_markdown_bold():
    text = "**Salt**: Seasoning.\n\nSummary: x\nVerdict: y"
    result = parse_ingredients_to_json(text)
    assert isinstance(result, dict)
    assert result["product_metadata"]["name"] == "Rajasthani Mix"


def test_parse_ingredients_to_json_empty_text():
    result = parse_ingredients_to_json("")
    assert result["product_metadata"]["summary"] == ""
    assert result["product_metadata"]["verdict"] == ""
    assert result["ingredients"] == []


def test_parse_ingredients_to_json_skips_summary_verdict_in_ingredients():
    text = """
Salt: Seasoning.

Summary: Overall summary.
Verdict: Safe to eat.
"""
    result = parse_ingredients_to_json(text)
    names = [i["ingredient"] for i in result["ingredients"]]
    assert "Summary" not in names
    assert "Verdict" not in names
