from types import SimpleNamespace
from uuid import uuid4

import jwt


def test_registered_route_matrix(app):
    registered = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
        if method in {"GET", "POST"}
    }

    assert ("GET", "/healthy") in registered
    assert ("POST", "/login") in registered
    assert ("POST", "/users") in registered
    assert ("GET", "/question-answers/latest-answers") in registered
    assert ("POST", "/question-answers") in registered
    assert ("GET", "/institutions") in registered
    assert ("POST", "/stripe/generate") in registered
    assert ("POST", "/stripe/webhook/payment") in registered
    assert ("POST", "/ai/anatomy") in registered
    assert any(
        method == "GET" and path.startswith("/institutions/") and path != "/institutions"
        for method, path in registered
    )


def test_healthy_route_returns_status_ok(client):
    response = client.get("/healthy")

    assert response.status_code == 200
    assert response.json() == {"status": "Ok"}


def test_login_route_returns_controller_response(client, override_db, monkeypatch):
    async def _login(nickname, password, db):
        assert nickname == "pedrov"
        assert password == "secret123"
        return {
            "user": {
                "id": str(uuid4()),
                "name": "Pedro Vieira",
                "nickname": "pedrov",
                "global_role": "User",
            },
            "question_generation_usage": None,
        }, "jwt-token"

    monkeypatch.setattr("src.controllers.auth_controller.AuthController.login", _login)

    response = client.post(
        "/login",
        json={"nickname": "pedrov", "password": "secret123"},
    )

    assert response.status_code == 200
    assert response.json()["token"] == "jwt-token"


def test_login_route_validates_required_fields(client, override_db):
    response = client.post("/login", json={"nickname": "pedrov"})

    assert response.status_code == 422


def test_users_route_creates_user(client, override_db, monkeypatch):
    async def _create_user(body, db):
        return {
            "data": {
                "id": str(uuid4()),
                "name": "Pedro Vieira",
                "email": "pedro@example.com",
                "nickname": "pedrov",
                "global_role": "User",
                "created_at": "2026-05-08T00:00:00",
                "updated_at": None,
            }
        }

    monkeypatch.setattr("src.controllers.users_controller.UsersController.create_user", _create_user)

    response = client.post(
        "/users",
        json={
            "name": "Pedro Vieira",
            "email": "pedro@example.com",
            "nickname": "pedrov",
            "password": "secret123",
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["nickname"] == "pedrov"


def test_users_route_validates_body(client, override_db):
    response = client.post(
        "/users",
        json={"name": "Pedro Vieira", "email": "pedro@example.com"},
    )

    assert response.status_code == 422


def test_question_answers_latest_answers_requires_authorization(client, override_db):
    response = client.get("/question-answers/latest-answers", params={"user_id": str(uuid4())})

    assert response.status_code == 401
    assert response.json()["detail"] == "Authorization header is required"


def test_question_answers_latest_answers_rejects_invalid_bearer_format(client, override_db):
    response = client.get(
        "/question-answers/latest-answers",
        params={"user_id": str(uuid4())},
        headers={"Authorization": "Token abc"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authorization format. Use: Bearer <token>"


def test_question_answers_latest_answers_rejects_invalid_token(
    client, override_db, monkeypatch
):
    monkeypatch.setattr(
        "src.middleware.jwt_middleware.JWTUtils.decode_jwt",
        staticmethod(lambda token: (_ for _ in ()).throw(jwt.InvalidTokenError("bad token"))),
    )
    monkeypatch.setattr(
        "src.middleware.jwt_middleware.async_session",
        lambda: override_db,
    )

    response = client.get(
        "/question-answers/latest-answers",
        params={"user_id": str(uuid4())},
        headers={"Authorization": "Bearer invalid", "x-institution-id": str(uuid4())},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"


def test_question_answers_latest_answers_rejects_expired_token(
    client, override_db, monkeypatch
):
    monkeypatch.setattr(
        "src.middleware.jwt_middleware.JWTUtils.decode_jwt",
        staticmethod(
            lambda token: (_ for _ in ()).throw(jwt.ExpiredSignatureError("expired"))
        ),
    )

    response = client.get(
        "/question-answers/latest-answers",
        params={"user_id": str(uuid4())},
        headers={"Authorization": "Bearer expired", "x-institution-id": str(uuid4())},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Token expired"


def test_question_answers_latest_answers_returns_data(
    client, override_db, authorize_request, monkeypatch
):
    headers, _ = authorize_request()

    async def _get_latest_answers(user_id, db):
        return {
            "data": [
                {
                    "id": str(uuid4()),
                    "institution_id": str(uuid4()),
                    "topic": "Neuroanatomy",
                    "subject": "cerebelo",
                    "question": "Qual estrutura pertence ao cerebelo?",
                    "answer_a": "Lobo anterior",
                    "answer_b": "Mesencéfalo",
                    "answer_c": "Bulbo",
                    "answer_d": "Tálamo",
                    "answer_e": None,
                    "explanation_a": "A alternativa A é correta.",
                    "explanation_b": "A alternativa B é incorreta.",
                    "explanation_c": "A alternativa C é incorreta.",
                    "explanation_d": "A alternativa D é incorreta.",
                    "explanation_e": None,
                    "correct_answer": "A",
                    "created_at": "2026-05-08T00:00:00",
                    "updated_at": None,
                    "user_answer": "B",
                    "user_id": str(uuid4()),
                    "answered_at": "2026-05-08T01:00:00",
                    "answer_updated_at": None,
                }
            ]
        }

    monkeypatch.setattr(
        "src.controllers.question_answers_controller.QuestionAnswersController.get_questions_with_latest_user_answers",
        _get_latest_answers,
    )

    response = client.get(
        "/question-answers/latest-answers",
        params={"user_id": str(uuid4())},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["data"][0]["user_answer"] == "B"


def test_question_answers_latest_answers_propagates_permission_errors(
    client, override_db, authorize_request
):
    headers, _ = authorize_request(
        permission_error={
            "status_code": 403,
            "detail": "User does not belong to the institution",
        }
    )

    response = client.get(
        "/question-answers/latest-answers",
        params={"user_id": str(uuid4())},
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "User does not belong to the institution"


def test_question_answers_latest_answers_validates_query_params(
    client, override_db, authorize_request
):
    headers, _ = authorize_request()

    response = client.get(
        "/question-answers/latest-answers",
        params={"user_id": "not-a-uuid"},
        headers=headers,
    )

    assert response.status_code == 422


def test_stripe_generate_route_returns_checkout_url(client, override_db, monkeypatch):
    async def _generate_checkout(user_id, db):
        return {"url_session": "https://checkout.stripe.test"}

    monkeypatch.setattr(
        "src.controllers.stripe_controller.StripeController.generate_payment_checkout",
        _generate_checkout,
    )

    response = client.post("/stripe/generate", json={"user_id": str(uuid4())})

    assert response.status_code == 200
    assert response.json() == {"url_session": "https://checkout.stripe.test"}


def test_stripe_generate_route_validates_uuid(client, override_db):
    response = client.post("/stripe/generate", json={"user_id": "invalid"})

    assert response.status_code == 422


def test_stripe_webhook_route_parses_body_and_forwards_to_controller(
    client, override_db, monkeypatch
):
    async def _payment_webhook(payload, db):
        assert payload["type"] == "checkout.session.completed"
        return {"status": "processed"}

    monkeypatch.setattr(
        "src.controllers.stripe_controller.StripeController.payment_response_webhook",
        _payment_webhook,
    )

    response = client.post(
        "/stripe/webhook/payment",
        json={"type": "checkout.session.completed", "data": {"object": {}}},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "processed"}


def test_ai_anatomy_route_requires_authorization(client, override_db):
    response = client.post("/ai/anatomy", json={"parameter": "Neuroanatomy"})

    assert response.status_code == 401


def test_ai_anatomy_route_returns_controller_response(
    client, override_db, authorize_request, monkeypatch
):
    headers, _ = authorize_request()

    async def _generate_question(parameter, db, institution_id, user_id):
        assert parameter == "Neuroanatomy"
        assert institution_id == headers["x-institution-id"]
        assert user_id is not None
        return {
            "data": {
                "id": str(uuid4()),
                "institution_id": headers["x-institution-id"],
                "topic": "Neuroanatomy",
                "subtopic": "cerebelo",
                "subtopic_description": "estrutura do cerebelo",
                "diversity_mode": "relationship",
                "question": "Pergunta gerada",
                "answer_a": "Lobo anterior",
                "answer_b": "Mesencéfalo",
                "answer_c": "Bulbo",
                "answer_d": "Tálamo",
                "correct_answer": "A",
                "explanation_a": "A alternativa A é correta.",
                "explanation_b": "A alternativa B é incorreta.",
                "explanation_c": "A alternativa C é incorreta.",
                "explanation_d": "A alternativa D é incorreta.",
            }
        }

    monkeypatch.setattr(
        "src.controllers.ai_anatomy_controller.AIAnatomyController.generate_question",
        _generate_question,
    )

    response = client.post(
        "/ai/anatomy",
        json={"parameter": "Neuroanatomy"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["question"] == "Pergunta gerada"


def test_ai_anatomy_route_validates_enum(client, override_db, authorize_request):
    headers, _ = authorize_request()

    response = client.post(
        "/ai/anatomy",
        json={"parameter": "Cardiology"},
        headers=headers,
    )

    assert response.status_code == 422


def test_ai_anatomy_route_requires_institution_header(
    client, override_db, authorize_request, monkeypatch
):
    headers, _ = authorize_request()
    headers.pop("x-institution-id")

    async def _validate(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "src.controllers.ai_anatomy_controller.SubscriptionService.validate_question_generation_availability",
        _validate,
    )

    response = client.post(
        "/ai/anatomy",
        json={"parameter": "Neuroanatomy"},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "institution_id is required and must be a valid UUID."
