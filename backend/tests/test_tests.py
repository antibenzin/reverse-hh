from tests.test_resumes import (
    _auth_as,
    _create_profile,
    _create_verified_company,
    _register,
    _resume_payload,
)


def _published_resume(client, email: str = "tester@candidate.com"):
    _register(client, email)
    _create_profile(client)
    resume_id = client.post("/api/v1/resumes", json={"title": "Dev"}).json()["id"]
    client.patch(f"/api/v1/resumes/{resume_id}", json=_resume_payload())
    client.post(f"/api/v1/resumes/{resume_id}/publish")
    return resume_id


def _sample_questions():
    return [
        {
            "type": "single_choice",
            "text": "Опыт с Python?",
            "sort_order": 0,
            "options": [
                {"text": "Да", "is_expected": True},
                {"text": "Нет", "is_expected": False},
            ],
        },
        {
            "type": "text",
            "text": "Расскажите о проекте",
            "sort_order": 1,
        },
        {
            "type": "scale",
            "text": "Оцените уровень",
            "sort_order": 2,
            "scale_min": 1,
            "scale_max": 5,
            "expected_scale_min": 3,
            "expected_scale_max": 5,
        },
    ]


def test_save_test_draft_hides_resume_from_catalog(client):
    resume_id = _published_resume(client)
    company = _create_verified_company(client, "employer@catalog-test.com")

    _auth_as(client, "tester@candidate.com")
    saved = client.put(
        f"/api/v1/resumes/{resume_id}/test",
        json={"questions": _sample_questions()},
    )
    assert saved.status_code == 200
    assert saved.json()["is_published"] is False

    me = client.get(f"/api/v1/resumes/{resume_id}")
    assert me.json()["test_editing"] is True

    _auth_as(client, "employer@catalog-test.com")
    catalog = client.get(
        "/api/v1/catalog/resumes",
        headers={"X-Company-Id": company["id"]},
    )
    assert catalog.json() == []


def test_publish_test_restores_catalog_visibility(client):
    resume_id = _published_resume(client, "publish@candidate.com")
    company = _create_verified_company(client, "employer@publish-test.com")

    _auth_as(client, "publish@candidate.com")
    client.put(f"/api/v1/resumes/{resume_id}/test", json={"questions": _sample_questions()})
    published = client.post(f"/api/v1/resumes/{resume_id}/test/publish")
    assert published.status_code == 200
    assert published.json()["is_published"] is True
    assert published.json()["version"] == 1

    resume = client.get(f"/api/v1/resumes/{resume_id}")
    assert resume.json()["test_editing"] is False

    _auth_as(client, "employer@publish-test.com")
    catalog = client.get(
        "/api/v1/catalog/resumes",
        headers={"X-Company-Id": company["id"]},
    )
    assert len(catalog.json()) == 1


def test_delete_test_requires_confirmation(client):
    resume_id = _published_resume(client, "delete@candidate.com")
    _auth_as(client, "delete@candidate.com")
    client.put(f"/api/v1/resumes/{resume_id}/test", json={"questions": _sample_questions()})

    denied = client.delete(f"/api/v1/resumes/{resume_id}/test")
    assert denied.status_code == 400

    ok = client.delete(f"/api/v1/resumes/{resume_id}/test", params={"confirm": "true"})
    assert ok.status_code == 204
    assert client.get(f"/api/v1/resumes/{resume_id}/test").status_code == 404


def test_max_ten_questions_enforced(client):
    resume_id = _published_resume(client, "maxq@candidate.com")
    questions = [
        {
            "type": "text",
            "text": f"Question {i}",
            "sort_order": i,
        }
        for i in range(11)
    ]
    response = client.put(
        f"/api/v1/resumes/{resume_id}/test",
        json={"questions": questions},
    )
    assert response.status_code == 400
