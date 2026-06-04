import importlib
from uuid import uuid4

import jwt
from fastapi.responses import JSONResponse

stripe_router_module = importlib.import_module("src.routers.stripe_router")


def test_registered_route_matrix(app):
    registered = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
        if method in {"GET", "POST", "PUT"}
    }

    assert ("GET", "/healthy") in registered
    assert ("POST", "/login") in registered
    assert ("POST", "/login/admin") in registered
    assert ("POST", "/forgot-password") in registered
    assert ("POST", "/reset-password") in registered
    assert ("POST", "/users") in registered
    assert ("GET", "/users/me") in registered
    assert ("PUT", "/users/me") in registered
    assert ("GET", "/admin/dashboard/user-payment-summary") in registered
    assert ("POST", "/admin/email-campaigns/inactive-plan-follow-up") in registered
    assert ("GET", "/question-answers/latest-answers") in registered
    assert ("POST", "/question-answers") in registered
    assert ("GET", "/institutions") in registered
    assert ("POST", "/stripe/generate") in registered
    assert ("POST", "/stripe/webhook/payment") in registered
    assert ("POST", "/ai/anatomy") in registered
    assert ("POST", "/ai/biology") in registered
    assert any(
        method == "GET"
        and path.startswith("/institutions/")
        and path != "/institutions"
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


def test_login_admin_route_returns_controller_response(client, override_db, monkeypatch):
    async def _login_admin(nickname, password, db):
        assert nickname == "admin"
        assert password == "Secret123!"
        return {
            "user": {
                "id": str(uuid4()),
                "name": "Pedro Vieira",
                "nickname": "admin",
                "dni": "12345678",
                "stripe_customer_id": None,
                "global_role": "Admin",
            },
            "question_generation_usage": None,
        }, "jwt-admin-token"

    monkeypatch.setattr(
        "src.controllers.auth_controller.AuthController.login_admin",
        _login_admin,
    )

    response = client.post(
        "/login/admin",
        json={"nickname": "admin", "password": "Secret123!"},
    )

    assert response.status_code == 200
    assert response.json()["token"] == "jwt-admin-token"
    assert response.json()["user"]["global_role"] == "Admin"


def test_forgot_password_route_returns_generic_message(
    client, override_db, monkeypatch
):
    async def _forgot_password(email, db):
        assert email == "pedro@example.com"
        return {
            "message": "If the email exists, password reset instructions have been generated."
        }

    monkeypatch.setattr(
        "src.controllers.auth_controller.AuthController.forgot_password",
        _forgot_password,
    )

    response = client.post("/forgot-password", json={"email": "pedro@example.com"})

    assert response.status_code == 200
    assert response.json() == {
        "message": "If the email exists, password reset instructions have been generated.",
        "reset_token": None,
    }


def test_reset_password_route_returns_success(client, override_db, monkeypatch):
    async def _reset_password(token, new_password, db):
        assert token == "reset-token"
        assert new_password == "NovaSenha123!"
        return {"message": "Password updated successfully."}

    monkeypatch.setattr(
        "src.controllers.auth_controller.AuthController.reset_password",
        _reset_password,
    )

    response = client.post(
        "/reset-password",
        json={"token": "reset-token", "new_password": "NovaSenha123!"},
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Password updated successfully."}


def test_reset_password_route_validates_required_fields(client, override_db):
    response = client.post("/reset-password", json={"token": "reset-token"})

    assert response.status_code == 422


def test_users_route_creates_user(client, override_db, monkeypatch):
    async def _create_user(body, db):
        return {
            "data": {
                "id": str(uuid4()),
                "name": "Pedro Vieira",
                "email": "pedro@example.com",
                "nickname": "pedrov",
                "dni": "12345678",
                "global_role": "User",
                "created_at": "2026-05-08T00:00:00",
                "updated_at": None,
            }
        }

    monkeypatch.setattr(
        "src.controllers.users_controller.UsersController.create_user", _create_user
    )

    response = client.post(
        "/users",
        json={
            "name": "Pedro Vieira",
            "email": "pedro@example.com",
            "nickname": "pedrov",
            "dni": "12345678",
            "password": "secret123",
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["nickname"] == "pedrov"


def test_users_route_validates_body(client, override_db):
    response = client.post(
        "/users",
        json={
            "name": "Pedro Vieira",
            "email": "pedro@example.com",
            "dni": "12345678",
        },
    )

    assert response.status_code == 422


def test_users_route_rejects_weak_password(client, override_db):
    response = client.post(
        "/users",
        json={
            "name": "Pedro Vieira",
            "email": "pedro@example.com",
            "nickname": "pedrov",
            "dni": "12345678",
            "password": "secret123",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Password must be at least 8 characters long and contain at least one "
        "uppercase letter, one lowercase letter, one number, and one special character"
    )


def test_users_route_rejects_invalid_dni(client, override_db):
    response = client.post(
        "/users",
        json={
            "name": "Pedro Vieira",
            "email": "pedro@example.com",
            "nickname": "pedrov",
            "dni": "1234",
            "password": "Secret123!",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "DNI is invalid"


def test_users_me_route_returns_authenticated_user(
    client, override_db, authorize_request, monkeypatch
):
    user_id = uuid4()
    headers, _ = authorize_request(user_id=user_id)

    async def _get_current_user(request_user_id, db):
        assert str(request_user_id) == str(user_id)
        return {
            "data": {
                "id": str(user_id),
                "name": "Pedro Vieira",
                "email": "pedro@example.com",
                "nickname": "pedrov",
                "dni": "12345678",
                "global_role": "User",
                "created_at": "2026-05-08T00:00:00",
                "updated_at": None,
            }
        }

    monkeypatch.setattr(
        "src.controllers.users_controller.UsersController.get_current_user",
        _get_current_user,
    )

    response = client.get("/users/me", headers=headers)

    assert response.status_code == 200
    assert response.json()["data"]["email"] == "pedro@example.com"


def test_users_me_route_updates_authenticated_user(
    client, override_db, authorize_request, monkeypatch
):
    user_id = uuid4()
    headers, _ = authorize_request(user_id=user_id)

    async def _update_current_user(request_user_id, body, db):
        assert str(request_user_id) == str(user_id)
        assert body.dni
        return {
            "data": {
                "id": str(user_id),
                "name": "Pedro Vieira",
                "email": "pedro@example.com",
                "nickname": "pedrov",
                "dni": "12345678",
                "global_role": "User",
                "created_at": "2026-05-08T00:00:00",
                "updated_at": "2026-05-24T00:00:00",
            }
        }

    monkeypatch.setattr(
        "src.controllers.users_controller.UsersController.update_current_user",
        _update_current_user,
    )

    response = client.put(
        "/users/me",
        json={
            "name": "Pedro Vieira",
            "email": "pedro@example.com",
            "nickname": "pedrov",
            "dni": "12345678",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["updated_at"] == "2026-05-24T00:00:00"


def test_admin_inactive_plan_campaign_route_returns_controller_response(
    client, override_db, authorize_request, monkeypatch
):
    user_id = uuid4()
    headers, _ = authorize_request(user_id=user_id)

    async def _send_campaign(current_user_id, body, db):
        assert str(current_user_id) == str(user_id)
        assert body.audience == "never_paid"
        assert body.subject == "Sentimos sua falta"
        assert body.dry_run is True
        return {
            "message": "Preview generated successfully.",
            "audience": "never_paid",
            "audience_label": "Usuarios que nunca pagaram",
            "dry_run": True,
            "matched_users": 2,
            "sent_emails": 0,
            "failed_emails": 0,
            "reply_to": "suporte@example.com",
            "recipients_preview": [
                {
                    "user_id": str(uuid4()),
                    "name": "Pedro Vieira",
                    "email": "pedro@example.com",
                }
            ],
        }

    monkeypatch.setattr(
        "src.controllers.admin_controller.AdminController.send_inactive_plan_email_campaign",
        _send_campaign,
    )

    response = client.post(
        "/admin/email-campaigns/inactive-plan-follow-up",
        json={
            "audience": "never_paid",
            "subject": "Sentimos sua falta",
            "message": "Queria entender o que esta faltando.",
            "dry_run": True,
            "confirm_send": False,
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["audience"] == "never_paid"
    assert response.json()["matched_users"] == 2
    assert response.json()["recipients_preview"][0]["email"] == "pedro@example.com"


def test_admin_user_payment_summary_route_returns_controller_response(
    client, override_db, authorize_request, monkeypatch
):
    user_id = uuid4()
    headers, _ = authorize_request(user_id=user_id)

    async def _summary(current_user_id, db):
        assert str(current_user_id) == str(user_id)
        return {
            "total_registered_users": 20,
            "never_paid_users": 9,
            "paid_without_active_subscription_users": 6,
            "active_subscription_users": 5,
            "users_without_active_subscription": 15,
        }

    monkeypatch.setattr(
        "src.controllers.admin_controller.AdminController.get_user_payment_summary",
        _summary,
    )

    response = client.get(
        "/admin/dashboard/user-payment-summary",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["total_registered_users"] == 20
    assert response.json()["paid_without_active_subscription_users"] == 6


def test_question_answers_latest_answers_requires_authorization(client, override_db):
    response = client.get(
        "/question-answers/latest-answers", params={"user_id": str(uuid4())}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Authorization header is required"


def test_question_answers_latest_answers_rejects_invalid_bearer_format(
    client, override_db
):
    response = client.get(
        "/question-answers/latest-answers",
        params={"user_id": str(uuid4())},
        headers={"Authorization": "Token abc"},
    )

    assert response.status_code == 401
    assert (
        response.json()["detail"] == "Invalid authorization format. Use: Bearer <token>"
    )


def test_question_answers_latest_answers_rejects_invalid_token(
    client, override_db, monkeypatch
):
    monkeypatch.setattr(
        "src.middleware.jwt_middleware.JWTUtils.decode_jwt",
        staticmethod(
            lambda token: (_ for _ in ()).throw(jwt.InvalidTokenError("bad token"))
        ),
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
    async def _generate_checkout(user_id, db, coupon_code=None):
        assert coupon_code == "PROMO-UBA"
        return {"url_session": "https://checkout.stripe.test"}

    monkeypatch.setattr(
        "src.controllers.stripe_controller.StripeController.generate_payment_checkout",
        _generate_checkout,
    )

    response = client.post(
        "/stripe/generate",
        json={"user_id": str(uuid4()), "coupon_code": "PROMO-UBA"},
    )

    assert response.status_code == 200
    assert response.json() == {"url_session": "https://checkout.stripe.test"}


def test_stripe_generate_route_returns_dni_validation_error(
    client, override_db, monkeypatch
):
    async def _generate_checkout(user_id, db, coupon_code=None):
        return JSONResponse(
            status_code=400,
            content={"detail": "You must update your DNI before starting the checkout"},
        )

    monkeypatch.setattr(
        "src.controllers.stripe_controller.StripeController.generate_payment_checkout",
        _generate_checkout,
    )

    response = client.post(
        "/stripe/generate",
        json={"user_id": str(uuid4())},
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "You must update your DNI before starting the checkout"
    }


def test_stripe_generate_route_validates_uuid(client, override_db):
    response = client.post("/stripe/generate", json={"user_id": "invalid"})

    assert response.status_code == 422


def test_stripe_webhook_route_parses_body_and_forwards_to_controller(
    client, override_db, monkeypatch
):
    def _construct_event(payload, sig_header, secret):
        assert sig_header == "valid-signature"
        assert secret == "whsec_test"
        return {"type": "checkout.session.completed", "data": {"object": {}}}

    async def _payment_webhook(payload, db):
        assert payload["type"] == "checkout.session.completed"
        return {"status": "processed"}

    monkeypatch.setattr(
        stripe_router_module.stripe.Webhook, "construct_event", _construct_event
    )
    monkeypatch.setattr(
        "src.controllers.stripe_controller.StripeController.payment_response_webhook",
        _payment_webhook,
    )

    response = client.post(
        "/stripe/webhook/payment",
        json={"type": "checkout.session.completed", "data": {"object": {}}},
        headers={"stripe-signature": "valid-signature"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "processed"}


def test_stripe_webhook_route_normalizes_stripe_sdk_event(
    client, override_db, monkeypatch
):
    class _StripeEvent:
        def _to_dict_recursive(self):
            return {
                "type": "checkout.session.completed",
                "data": {"object": {"id": "cs_123"}},
            }

    def _construct_event(payload, sig_header, secret):
        return _StripeEvent()

    async def _payment_webhook(payload, db):
        assert payload == {
            "type": "checkout.session.completed",
            "data": {"object": {"id": "cs_123"}},
        }
        return {"status": "processed"}

    monkeypatch.setattr(
        stripe_router_module.stripe.Webhook, "construct_event", _construct_event
    )
    monkeypatch.setattr(
        "src.controllers.stripe_controller.StripeController.payment_response_webhook",
        _payment_webhook,
    )

    response = client.post(
        "/stripe/webhook/payment",
        json={"type": "checkout.session.completed", "data": {"object": {}}},
        headers={"stripe-signature": "valid-signature"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "processed"}


def test_stripe_webhook_route_rejects_invalid_signature(
    client, override_db, monkeypatch
):
    def _construct_event(payload, sig_header, secret):
        raise ValueError("invalid payload")

    monkeypatch.setattr(
        stripe_router_module.stripe.Webhook, "construct_event", _construct_event
    )

    response = client.post(
        "/stripe/webhook/payment",
        json={"type": "checkout.session.completed", "data": {"object": {}}},
        headers={"stripe-signature": "invalid-signature"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid Stripe webhook signature"


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
    assert (
        response.json()["detail"]
        == "institution_id is required and must be a valid UUID."
    )


def test_ai_biology_route_requires_authorization(client, override_db):
    response = client.post("/ai/biology", json={"parameter": "Genetica"})

    assert response.status_code == 401


def test_ai_biology_route_returns_controller_response(
    client, override_db, authorize_request, monkeypatch
):
    headers, _ = authorize_request()

    async def _generate_question(parameter, db, institution_id, user_id):
        assert parameter == "Genetica"
        assert institution_id == headers["x-institution-id"]
        assert user_id is not None
        return {
            "data": {
                "id": str(uuid4()),
                "institution_id": headers["x-institution-id"],
                "topic": "Genetica",
                "subtopic": "herencia_mitocondrial",
                "subtopic_description": "transmision y heteroplasmia",
                "diversity_mode": "mechanism",
                "question": "Pergunta gerada",
                "answer_a": "Opcao A",
                "answer_b": "Opcao B",
                "answer_c": "Opcao C",
                "answer_d": "Opcao D",
                "correct_answer": "A",
                "explanation_a": "A alternativa A e correta.",
                "explanation_b": "A alternativa B e incorreta.",
                "explanation_c": "A alternativa C e incorreta.",
                "explanation_d": "A alternativa D e incorreta.",
            }
        }

    monkeypatch.setattr(
        "src.controllers.ai_biology_controller.AIBiologyController.generate_question",
        _generate_question,
    )

    response = client.post(
        "/ai/biology",
        json={"parameter": "Genetica"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["question"] == "Pergunta gerada"


def test_ai_biology_route_validates_enum(client, override_db, authorize_request):
    headers, _ = authorize_request()

    response = client.post(
        "/ai/biology",
        json={"parameter": "Botanica"},
        headers=headers,
    )

    assert response.status_code == 422


def test_ai_biology_route_requires_institution_header(
    client, override_db, authorize_request, monkeypatch
):
    headers, _ = authorize_request()
    headers.pop("x-institution-id")

    async def _validate(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "src.controllers.ai_biology_controller.SubscriptionService.validate_question_generation_availability",
        _validate,
    )

    response = client.post(
        "/ai/biology",
        json={"parameter": "Genetica"},
        headers=headers,
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "institution_id is required and must be a valid UUID."
    )
