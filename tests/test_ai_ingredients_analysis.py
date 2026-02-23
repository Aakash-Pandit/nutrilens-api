"""Unit tests for ai.ingredients_analysis (analyze_ingredients)."""
import os
from unittest.mock import MagicMock, patch

import pytest

from ai.ingredients_analysis import analyze_ingredients


def test_analyze_ingredients_no_api_key_returns_unavailable_message():
    with patch.dict(os.environ, {"COHERE_API_KEY": ""}, clear=False):
        result = analyze_ingredients("Sugar, salt")
    assert "COHERE_API_KEY" in result or "unavailable" in result.lower()


def test_analyze_ingredients_empty_input_uses_placeholder():
    with patch.dict(os.environ, {"COHERE_API_KEY": "test-key"}, clear=False):
        with patch("ai.ingredients_analysis.cohere") as mock_cohere_module:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Analysis result"
            mock_client.chat.return_value = mock_response
            mock_cohere_module.Client.return_value = mock_client
            result = analyze_ingredients("")
    assert "No ingredients text" in result or mock_client.chat.called


def test_analyze_ingredients_calls_cohere_with_prompt():
    with patch.dict(os.environ, {"COHERE_API_KEY": "test-key"}, clear=False):
        with patch("ai.ingredients_analysis.cohere") as mock_cohere_module:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "  Parsed analysis  "
            mock_client.chat.return_value = mock_response
            mock_cohere_module.Client.return_value = mock_client
            result = analyze_ingredients("Sugar, Salt")
    assert result == "Parsed analysis"
    assert mock_client.chat.called
    call_kw = mock_client.chat.call_args[1]
    assert "preamble" in call_kw
    assert "Sugar, Salt" in call_kw["preamble"]
