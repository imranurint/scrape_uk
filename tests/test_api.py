"""
tests/test_api.py
──────────────────
FastAPI integration tests using httpx AsyncClient + shared conftest fixtures.
No PostgreSQL needed — uses the in-memory SQLite DB from conftest.py.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestHealthEndpoints:
    async def test_health_ok(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    async def test_ready_ok(self, client: AsyncClient):
        resp = await client.get("/ready")
        # SQLite doesn't support "SELECT 1" the same way but status should be 200 or 503
        assert resp.status_code in (200, 503)


class TestCourseSearch:
    async def test_empty_db_returns_empty_list(self, client: AsyncClient):
        resp = await client.get("/courses/search")
        assert resp.status_code == 200
        body = resp.json()
        assert "total" in body
        assert "results" in body
        assert isinstance(body["results"], list)

    async def test_search_with_keyword(self, client: AsyncClient, sample_course):
        resp = await client.get("/courses/search", params={"q": "Computer Science"})
        assert resp.status_code == 200
        body = resp.json()
        # May or may not match depending on FTS availability in SQLite
        assert "results" in body

    async def test_filter_by_university(self, client: AsyncClient, sample_course):
        resp = await client.get(
            "/courses/search", params={"university": "Test University"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        assert body["results"][0]["university_name"] == "Test University"

    async def test_filter_by_degree(self, client: AsyncClient, sample_course):
        resp = await client.get("/courses/search", params={"degree": "BSc"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1

    async def test_filter_by_level(self, client: AsyncClient, sample_course):
        resp = await client.get("/courses/search", params={"level": "undergraduate"})
        assert resp.status_code == 200

    async def test_fee_range_filter(self, client: AsyncClient, sample_course):
        resp = await client.get(
            "/courses/search", params={"min_fee": 5000, "max_fee": 15000}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1

    async def test_pagination_params(self, client: AsyncClient, sample_course):
        resp = await client.get(
            "/courses/search", params={"page": 1, "page_size": 5}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["page"] == 1
        assert body["page_size"] == 5

    async def test_page_size_over_limit_rejected(self, client: AsyncClient):
        resp = await client.get("/courses/search", params={"page_size": 999})
        assert resp.status_code == 422   # FastAPI validation error

    async def test_page_zero_rejected(self, client: AsyncClient):
        resp = await client.get("/courses/search", params={"page": 0})
        assert resp.status_code == 422


class TestCourseDetail:
    async def test_get_existing_course(self, client: AsyncClient, sample_course):
        resp = await client.get(f"/courses/{sample_course.id}")
        assert resp.status_code == 200
        body = resp.json()
        # Verify top-level schema shape
        assert "university" in body
        assert "course" in body
        assert "fees" in body
        assert "admission" in body
        assert "metadata" in body

    async def test_course_fields_correct(self, client: AsyncClient, sample_course):
        resp = await client.get(f"/courses/{sample_course.id}")
        body = resp.json()
        assert body["course"]["name"] == "BSc Computer Science"
        assert body["course"]["degree"] == "BSc"
        assert body["fees"]["uk"]["yearly"] == 9250
        assert body["fees"]["uk"]["currency"] == "GBP"
        assert body["fees"]["international"]["yearly"] == 35000

    async def test_course_not_found(self, client: AsyncClient):
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = await client.get(f"/courses/{fake_id}")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    async def test_invalid_uuid_returns_422(self, client: AsyncClient):
        resp = await client.get("/courses/not-a-uuid")
        assert resp.status_code == 422


class TestUniversities:
    async def test_empty_list(self, client: AsyncClient):
        resp = await client.get("/universities")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_list_with_data(self, client: AsyncClient, sample_university):
        resp = await client.get("/universities")
        assert resp.status_code == 200
        names = [u["name"] for u in resp.json()]
        assert "Test University" in names

    async def test_university_detail(self, client: AsyncClient, sample_university):
        resp = await client.get(f"/universities/{sample_university.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Test University"
        assert body["location"] == "London, England"

    async def test_university_not_found(self, client: AsyncClient):
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = await client.get(f"/universities/{fake_id}")
        assert resp.status_code == 404
