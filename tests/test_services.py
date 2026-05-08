import asyncio
from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

from fastapi import HTTPException

import src.services.ai_anatomy_service as ai_anatomy_service_module
from src.models.models import Questions, Subscriptions
from src.schemas.questions_schemas import OnlyQuestionsGetSchema
from src.services.ai_anatomy_service import AIAnatomyService
from src.services.auth_service import AuthService
from src.services.question_answers_service import QuestionAnswersService
from src.services.questions_service import QuestionsService
from src.services.stripe_service import StripeService
from src.services.subscription_service import SubscriptionService
from src.services.user_service import UserService
from src.utils.fernet_utils import FernetUtils
from tests.conftest import FakeAsyncSession, FakeExecuteResult


def _build_user(global_role="User"):
    fernet = FernetUtils()
    return SimpleNamespace(
        id=uuid4(),
        name=fernet.encrypt("Pedro Vieira"),
        email=fernet.encrypt("pedro@example.com"),
        nickname=fernet.encrypt("pedrov"),
        password=fernet.encrypt("secret123"),
        global_role=global_role,
    )


def _build_question(question_id=None, institution_id=None):
    return Questions(
        id=question_id or uuid4(),
        institution_id=institution_id or uuid4(),
        topic="Neuroanatomy",
        subtopic="cerebelo",
        subtopic_description="estrutura do cerebelo",
        diversity_mode="relationship",
        question="Qual estrutura pertence ao cerebelo?",
        answer_a="Lobo anterior",
        answer_b="Mesencéfalo",
        answer_c="Bulbo",
        answer_d="Tálamo",
        explanation_a="A alternativa A é correta.",
        explanation_b="A alternativa B é incorreta.",
        explanation_c="A alternativa C é incorreta.",
        explanation_d="A alternativa D é incorreta.",
        answer_e=None,
        explanation_e=None,
        correct_answer="A",
        created_at=datetime.now(),
        updated_at=None,
    )


def test_auth_service_user_has_active_subscription_true():
    db = FakeAsyncSession(
        execute_results=[FakeExecuteResult(scalars_items=[SimpleNamespace(id=uuid4())])]
    )

    response = asyncio.run(AuthService.user_has_active_subscription(uuid4(), db))

    assert response is True


def test_auth_service_user_has_active_subscription_false():
    db = FakeAsyncSession(execute_results=[FakeExecuteResult(scalars_items=[])])

    response = asyncio.run(AuthService.user_has_active_subscription(uuid4(), db))

    assert response is False


def test_auth_service_login_returns_admin_user():
    admin_user = _build_user(global_role="Admin")
    db = FakeAsyncSession(execute_results=[FakeExecuteResult(scalars_items=[admin_user])])

    response = asyncio.run(AuthService.login("pedrov", "secret123", db))

    assert response is admin_user


def test_auth_service_login_returns_uba_user_institution(monkeypatch):
    base_user = _build_user()
    expected_institution = SimpleNamespace(id=uuid4())
    expected_user_institution = SimpleNamespace(
        user=SimpleNamespace(id=base_user.id),
        institution_id=expected_institution.id,
        profile=SimpleNamespace(name="basic_uba_user"),
    )
    db = FakeAsyncSession(execute_results=[FakeExecuteResult(scalars_items=[base_user])])

    async def _get_uba_institution(_db):
        return expected_institution

    async def _read_user_institutions(user_id, institution_id, _db):
        assert user_id == base_user.id
        assert institution_id == expected_institution.id
        return expected_user_institution

    monkeypatch.setattr(
        "src.services.auth_service.InstitutionsService.get_uba_institution",
        _get_uba_institution,
    )
    monkeypatch.setattr(
        "src.services.auth_service.UserInstitutionService.read_user_institutions",
        _read_user_institutions,
    )

    response = asyncio.run(AuthService.login("pedrov", "secret123", db))

    assert response is expected_user_institution


def test_auth_service_login_returns_base_user_when_no_uba_membership(monkeypatch):
    base_user = _build_user()
    db = FakeAsyncSession(execute_results=[FakeExecuteResult(scalars_items=[base_user])])

    async def _get_uba_institution(_db):
        return SimpleNamespace(id=uuid4())

    async def _read_user_institutions(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "src.services.auth_service.InstitutionsService.get_uba_institution",
        _get_uba_institution,
    )
    monkeypatch.setattr(
        "src.services.auth_service.UserInstitutionService.read_user_institutions",
        _read_user_institutions,
    )

    response = asyncio.run(AuthService.login("pedrov", "secret123", db))

    assert response is base_user


def test_auth_service_login_rejects_invalid_credentials():
    user = _build_user()
    db = FakeAsyncSession(execute_results=[FakeExecuteResult(scalars_items=[user])])

    try:
        asyncio.run(AuthService.login("pedrov", "wrong-password", db))
    except ValueError as exc:
        assert str(exc) == "Invalid nickname or password"
    else:
        assert False, "Expected invalid credentials error"


def test_user_service_check_user_existance_rejects_invalid_uuid():
    try:
        asyncio.run(UserService.check_user_existance("not-a-uuid", FakeAsyncSession()))
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "Incorrect Id format"
    else:
        assert False, "Expected invalid UUID error"


def test_user_service_check_user_existance_returns_true():
    db = FakeAsyncSession(
        execute_results=[FakeExecuteResult(scalars_items=[SimpleNamespace(id=uuid4())])]
    )

    response = asyncio.run(UserService.check_user_existance(str(uuid4()), db))

    assert response is True


def test_question_answers_service_maps_latest_answers():
    question = _build_question()
    answered_at = datetime.now() - timedelta(hours=1)
    updated_at = datetime.now()
    user_id = uuid4()
    db = FakeAsyncSession(
        execute_results=[
            FakeExecuteResult(
                rows=[(question, "B", user_id, answered_at, updated_at)]
            )
        ]
    )

    response = asyncio.run(
        QuestionAnswersService.get_questions_with_latest_user_answers(user_id, db)
    )

    assert len(response["data"]) == 1
    payload = response["data"][0]
    assert payload.id == question.id
    assert payload.user_answer == "B"
    assert payload.user_id == user_id
    assert payload.answered_at == answered_at


def test_questions_service_get_last_three_questions_returns_mapped_items():
    question = _build_question()
    db = FakeAsyncSession(
        execute_results=[FakeExecuteResult(scalars_items=[question])]
    )

    response = asyncio.run(
        QuestionsService.get_last_three_questions("Neuroanatomy", "cerebelo", db)
    )

    assert response == [OnlyQuestionsGetSchema(question=question.question)]


def test_questions_service_get_last_three_questions_returns_empty_list():
    db = FakeAsyncSession(execute_results=[FakeExecuteResult(scalars_items=[])])

    response = asyncio.run(
        QuestionsService.get_last_three_questions("Neuroanatomy", "cerebelo", db)
    )

    assert response == []


def test_subscription_service_parse_uuid_accepts_string(sample_ids):
    parsed = SubscriptionService._parse_uuid(str(sample_ids.user_id), "user_id")

    assert parsed == sample_ids.user_id


def test_subscription_service_parse_uuid_rejects_invalid_value():
    try:
        SubscriptionService._parse_uuid("invalid", "institution_id")
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "Invalid institution_id format."
    else:
        assert False, "Expected invalid UUID error"


def test_subscription_service_sync_generation_cycle_resets_counter():
    next_cycle = datetime.now() + timedelta(days=30)
    subscription = SimpleNamespace(
        current_period_end=next_cycle,
        questions_generation_cycle_end=datetime.now(),
        questions_generated_in_cycle=9,
        updated_at=None,
    )

    SubscriptionService._sync_generation_cycle(subscription)

    assert subscription.questions_generated_in_cycle == 0
    assert subscription.questions_generation_cycle_end == next_cycle
    assert subscription.updated_at is not None


def test_subscription_service_validate_question_generation_availability(monkeypatch):
    cycle_end = datetime.now() + timedelta(days=30)
    subscription = SimpleNamespace(
        current_period_end=cycle_end,
        questions_generation_cycle_end=cycle_end,
        questions_generated_in_cycle=2,
        status="active",
    )
    user_institution = SimpleNamespace(
        profile=SimpleNamespace(questions_create_limit=5)
    )

    async def _context(*args, **kwargs):
        return user_institution, subscription

    monkeypatch.setattr(
        SubscriptionService, "_get_generation_context", staticmethod(_context)
    )

    response = asyncio.run(
        SubscriptionService.validate_question_generation_availability(
            uuid4(), uuid4(), FakeAsyncSession()
        )
    )

    assert response["questions_used"] == 2
    assert response["questions_limit"] == 5
    assert response["questions_remaining"] == 3
    assert response["subscription_status"] == "active"


def test_subscription_service_create_question_and_consume_quota(sample_ids, monkeypatch):
    cycle_end = datetime.now() + timedelta(days=30)
    subscription = Subscriptions(
        id=sample_ids.subscription_id,
        user_id=sample_ids.user_id,
        stripe_subscription_id="sub_123",
        status="active",
        price_id="price_test",
        current_period_end=cycle_end,
        questions_generated_in_cycle=1,
        questions_generation_cycle_end=cycle_end,
        created_at=datetime.now(),
        updated_at=None,
    )
    user_institution = SimpleNamespace(
        profile=SimpleNamespace(questions_create_limit=5)
    )
    db = FakeAsyncSession()

    async def _context(*args, **kwargs):
        return user_institution, subscription

    monkeypatch.setattr(
        SubscriptionService, "_get_generation_context", staticmethod(_context)
    )

    payload = {
        "id": uuid4(),
        "institution_id": sample_ids.institution_id,
        "topic": "Neuroanatomy",
        "subtopic": "cerebelo",
        "subtopic_description": "estrutura do cerebelo",
        "diversity_mode": "relationship",
        "question": "Qual estrutura pertence ao cerebelo?",
        "answer_a": "Lobo anterior",
        "answer_b": "Mesencéfalo",
        "answer_c": "Bulbo",
        "answer_d": "Tálamo",
        "explanation_a": "A alternativa A é correta.",
        "explanation_b": "A alternativa B é incorreta.",
        "explanation_c": "A alternativa C é incorreta.",
        "explanation_d": "A alternativa D é incorreta.",
        "correct_answer": "A",
        "answer_e": None,
        "explanation_e": None,
    }

    question, usage = asyncio.run(
        SubscriptionService.create_question_and_consume_quota(
            sample_ids.user_id,
            sample_ids.institution_id,
            payload,
            db,
        )
    )

    assert question.question == payload["question"]
    assert subscription.questions_generated_in_cycle == 2
    assert db.committed is True
    assert len(db.added) == 1
    assert usage["questions_used"] == 2
    assert usage["questions_remaining"] == 3


def test_subscription_service_create_question_rolls_back_on_commit_error(sample_ids, monkeypatch):
    cycle_end = datetime.now() + timedelta(days=30)
    subscription = Subscriptions(
        id=sample_ids.subscription_id,
        user_id=sample_ids.user_id,
        stripe_subscription_id="sub_123",
        status="active",
        price_id="price_test",
        current_period_end=cycle_end,
        questions_generated_in_cycle=0,
        questions_generation_cycle_end=cycle_end,
        created_at=datetime.now(),
        updated_at=None,
    )
    user_institution = SimpleNamespace(
        profile=SimpleNamespace(questions_create_limit=5)
    )
    db = FakeAsyncSession(commit_error=RuntimeError("commit failed"))

    async def _context(*args, **kwargs):
        return user_institution, subscription

    monkeypatch.setattr(
        SubscriptionService, "_get_generation_context", staticmethod(_context)
    )

    try:
        asyncio.run(
            SubscriptionService.create_question_and_consume_quota(
                sample_ids.user_id,
                sample_ids.institution_id,
                {
                    "id": uuid4(),
                    "institution_id": sample_ids.institution_id,
                    "topic": "Neuroanatomy",
                    "subtopic": "cerebelo",
                    "subtopic_description": "estrutura do cerebelo",
                    "diversity_mode": "relationship",
                    "question": "Pergunta",
                    "answer_a": "A",
                    "answer_b": "B",
                    "answer_c": "C",
                    "answer_d": "D",
                    "explanation_a": "EA",
                    "explanation_b": "EB",
                    "explanation_c": "EC",
                    "explanation_d": "ED",
                    "correct_answer": "A",
                    "answer_e": None,
                    "explanation_e": None,
                },
                db,
            )
        )
    except RuntimeError as exc:
        assert str(exc) == "commit failed"
    else:
        assert False, "Expected commit error"

    assert db.rolled_back is True


def test_stripe_service_extract_user_id_from_supported_locations():
    direct = StripeService._extract_user_id_from_metadata(
        {"metadata": {"user_id": "direct-user"}}
    )
    nested = StripeService._extract_user_id_from_metadata(
        {"subscription_details": {"metadata": {"user_id": "nested-user"}}}
    )
    parent_nested = StripeService._extract_user_id_from_metadata(
        {
            "parent": {
                "subscription_details": {"metadata": {"user_id": "parent-user"}}
            }
        }
    )

    assert direct == "direct-user"
    assert nested == "nested-user"
    assert parent_nested == "parent-user"


def test_stripe_service_extract_price_id_from_supported_locations():
    assert StripeService._extract_price_id({"metadata": {"price_id": "price_meta"}}) == "price_meta"
    assert (
        StripeService._extract_price_id(
            {"items": {"data": [{"price": {"id": "price_items"}}]}}
        )
        == "price_items"
    )
    assert (
        StripeService._extract_price_id(
            {"lines": {"data": [{"price": {"id": "price_lines"}}]}}
        )
        == "price_lines"
    )


def test_stripe_service_normalize_subscription_status():
    assert StripeService._normalize_subscription_status("active") == "active"
    assert StripeService._normalize_subscription_status("paused") == "failed_payment"
    assert StripeService._normalize_subscription_status("unknown") == "incomplete"


def test_stripe_service_invoice_payment_succeeded_processes_event(monkeypatch):
    subscription = SimpleNamespace(
        stripe_subscription_id="sub_123",
        status="active",
    )
    db = FakeAsyncSession()
    user_id = uuid4()

    async def _get_subscription(*args, **kwargs):
        return subscription

    async def _upsert_subscription(**kwargs):
        return subscription, "updated"

    async def _sync_user_access(*args, **kwargs):
        return "created"

    monkeypatch.setattr(
        StripeService, "_get_subscription_by_stripe_id", staticmethod(_get_subscription)
    )
    monkeypatch.setattr(
        StripeService, "_upsert_subscription", staticmethod(_upsert_subscription)
    )
    monkeypatch.setattr(
        StripeService, "_sync_user_access", staticmethod(_sync_user_access)
    )

    response = asyncio.run(
        StripeService.invoice_payment_succeeded(
            {
                "type": "invoice.payment_succeeded",
                "data": {
                    "object": {
                        "subscription": "sub_123",
                        "customer": "cus_123",
                        "metadata": {"user_id": str(user_id), "price_id": "price_test"},
                        "lines": {"data": [{"period": {"end": 1_700_000_000}}]},
                    }
                },
            },
            db,
        )
    )

    assert response["status"] == "processed"
    assert response["subscription_action"] == "updated"
    assert response["access_action"] == "created"
    assert response["subscription_status"] == "active"


def test_stripe_service_invoice_payment_failed_marks_subscription_create_as_incomplete(monkeypatch):
    existing_subscription = SimpleNamespace(
        current_period_end=datetime.now() + timedelta(days=30),
        user_id=uuid4(),
    )
    created_subscription = SimpleNamespace(
        stripe_subscription_id="sub_123",
        status="incomplete",
    )
    db = FakeAsyncSession()

    async def _get_subscription(*args, **kwargs):
        return existing_subscription

    async def _upsert_subscription(**kwargs):
        assert kwargs["status"] == "incomplete"
        return created_subscription, "updated"

    async def _sync_user_access(*args, **kwargs):
        return "unchanged"

    monkeypatch.setattr(
        StripeService, "_get_subscription_by_stripe_id", staticmethod(_get_subscription)
    )
    monkeypatch.setattr(
        StripeService, "_upsert_subscription", staticmethod(_upsert_subscription)
    )
    monkeypatch.setattr(
        StripeService, "_sync_user_access", staticmethod(_sync_user_access)
    )

    response = asyncio.run(
        StripeService.invoice_payment_failed(
            {
                "type": "invoice.payment_failed",
                "data": {
                    "object": {
                        "subscription": "sub_123",
                        "customer": "cus_123",
                        "billing_reason": "subscription_create",
                        "metadata": {
                            "user_id": str(existing_subscription.user_id),
                            "price_id": "price_test",
                        },
                    }
                },
            },
            db,
        )
    )

    assert response["status"] == "processed"
    assert response["subscription_status"] == "incomplete"


def test_ai_anatomy_service_generate_response_formats_prompt(monkeypatch):
    expected_response = SimpleNamespace(id="response-123")
    captured = {}

    def _create(*, model, input):
        captured["model"] = model
        captured["input"] = input
        return expected_response

    monkeypatch.setattr(ai_anatomy_service_module.client.responses, "create", _create)

    response = asyncio.run(
        AIAnatomyService.generate_response(
            parameter="Neuroanatomy",
            subtopic="cerebelo",
            subtopic_description="estrutura do cerebelo",
            diversity_mode="relationship",
            correct_letter="B",
            recent_questions=[SimpleNamespace(question="Pergunta antiga")],
        )
    )

    assert response is expected_response
    assert captured["model"] == "gpt-5.4-mini"
    assert "Neuroanatomy" in captured["input"]
    assert "cerebelo" in captured["input"]
    assert "Pergunta antiga" in captured["input"]
    assert "relationship" in captured["input"]


def test_stripe_service_parse_uuid_returns_uuid(sample_ids):
    assert StripeService._parse_uuid(str(sample_ids.user_id)) == sample_ids.user_id
    assert isinstance(StripeService._parse_uuid(str(sample_ids.user_id)), UUID)


def test_stripe_service_parse_uuid_returns_none_for_invalid_value():
    assert StripeService._parse_uuid("invalid") is None


def test_stripe_service_unix_to_datetime_handles_none():
    assert StripeService._unix_to_datetime(None) is None
