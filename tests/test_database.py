"""Unit tests for database.db."""
import os

import pytest


def test_build_database_url_from_env(monkeypatch):
    from database import db
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/mydb")
    url = db._build_database_url()
    assert url == "postgresql://user:pass@host:5432/mydb"


def test_build_database_url_fallback_from_postgres_vars(monkeypatch):
    from database import db
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("POSTGRES_USER", "u")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p")
    monkeypatch.setenv("POSTGRES_HOST", "h")
    monkeypatch.setenv("POSTGRES_PORT", "5433")
    monkeypatch.setenv("POSTGRES_DB", "d")
    url = db._build_database_url()
    assert "postgresql" in url
    assert "u" in url and "p" in url and "h" in url and "5433" in url and "d" in url
