import asyncio
from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
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


def test_subscription_service_sync_generation_cycle_keeps_counter_without_period_end():
    subscription = SimpleNamespace(
        current_period_end=None,
        questions_generation_cycle_end=None,
        questions_generated_in_cycle=9,
        updated_at=None,
    )

    SubscriptionService._sync_generation_cycle(subscription)

    assert subscription.questions_generated_in_cycle == 9
    assert subscription.updated_at is None


def test_subscription_service_get_generation_context_rejects_missing_profile(sample_ids):
    db = FakeAsyncSession(
        execute_results=[FakeExecuteResult(scalars_items=[SimpleNamespace(profile=None)])]
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            SubscriptionService._get_generation_context(
                sample_ids.user_id,
                sample_ids.institution_id,
                db,
                lock_subscription=False,
            )
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == "User does not have a valid profile for this institution."


def test_subscription_service_get_generation_context_rejects_missing_subscription(sample_ids):
    membership = SimpleNamespace(profile=SimpleNamespace(questions_create_limit=5))
    db = FakeAsyncSession(
        execute_results=[
            FakeExecuteResult(scalars_items=[membership]),
            FakeExecuteResult(scalars_items=[]),
        ]
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            SubscriptionService._get_generation_context(
                sample_ids.user_id,
                sample_ids.institution_id,
                db,
                lock_subscription=True,
            )
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == "Active subscription required."


def test_subscription_service_get_generation_context_returns_membership_and_subscription(sample_ids):
    membership = SimpleNamespace(profile=SimpleNamespace(questions_create_limit=5))
    subscription = SimpleNamespace(status="active")
    db = FakeAsyncSession(
        execute_results=[
            FakeExecuteResult(scalars_items=[membership]),
            FakeExecuteResult(scalars_items=[subscription]),
        ]
    )

    response_membership, response_subscription = asyncio.run(
        SubscriptionService._get_generation_context(
            sample_ids.user_id,
            sample_ids.institution_id,
            db,
            lock_subscription=False,
        )
    )

    assert response_membership is membership
    assert response_subscription is subscription


def test_subscription_service_validate_generation_limit_rejects_when_reaching_limit():
    with pytest.raises(HTTPException) as exc:
        SubscriptionService._validate_generation_limit(
            SimpleNamespace(questions_generated_in_cycle=5),
            5,
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == "Monthly question generation limit reached for this profile."


def test_subscription_service_build_usage_summary_handles_empty_subscription():
    response = SubscriptionService._build_usage_summary(None, 5)

    assert response == {
        "questions_used": 0,
        "questions_limit": 5,
        "questions_remaining": 5,
        "cycle_end": None,
        "subscription_status": None,
    }


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


def test_subscription_service_get_question_generation_usage_without_institution(sample_ids):
    cycle_end = datetime.now() + timedelta(days=30)
    subscription = SimpleNamespace(
        questions_generated_in_cycle=2,
        questions_generation_cycle_end=cycle_end,
        current_period_end=cycle_end,
        status="active",
    )
    db = FakeAsyncSession(execute_results=[FakeExecuteResult(scalars_items=[subscription])])

    response = asyncio.run(
        SubscriptionService.get_question_generation_usage(sample_ids.user_id, None, db)
    )

    assert response["questions_used"] == 2
    assert response["questions_limit"] is None
    assert response["subscription_status"] == "active"


def test_subscription_service_get_question_generation_usage_ignores_invalid_institution(sample_ids):
    cycle_end = datetime.now() + timedelta(days=30)
    subscription = SimpleNamespace(
        questions_generated_in_cycle=2,
        questions_generation_cycle_end=cycle_end,
        current_period_end=cycle_end,
        status="active",
    )
    db = FakeAsyncSession(execute_results=[FakeExecuteResult(scalars_items=[subscription])])

    response = asyncio.run(
        SubscriptionService.get_question_generation_usage(sample_ids.user_id, "invalid", db)
    )

    assert response["questions_limit"] is None
    assert response["questions_remaining"] is None


def test_subscription_service_get_question_generation_usage_with_profile_limit(sample_ids):
    cycle_end = datetime.now() + timedelta(days=30)
    subscription = SimpleNamespace(
        questions_generated_in_cycle=2,
        questions_generation_cycle_end=cycle_end,
        current_period_end=cycle_end,
        status="active",
        created_at=datetime.now(),
    )
    membership = SimpleNamespace(profile=SimpleNamespace(questions_create_limit=5))
    db = FakeAsyncSession(
        execute_results=[
            FakeExecuteResult(scalars_items=[subscription]),
            FakeExecuteResult(scalars_items=[membership]),
        ]
    )

    response = asyncio.run(
        SubscriptionService.get_question_generation_usage(
            sample_ids.user_id,
            sample_ids.institution_id,
            db,
        )
    )

    assert response["questions_limit"] == 5
    assert response["questions_remaining"] == 3


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


def test_stripe_service_extract_user_id_returns_none_for_invalid_payload():
    assert StripeService._extract_user_id_from_metadata("invalid") is None


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


def test_stripe_service_extract_price_id_from_subscription_details_and_invalid_payload():
    assert (
        StripeService._extract_price_id(
            {"subscription_details": {"metadata": {"price_id": "price_subscription"}}}
        )
        == "price_subscription"
    )
    assert StripeService._extract_price_id("invalid") is None


def test_stripe_service_normalize_subscription_status():
    assert StripeService._normalize_subscription_status("active") == "active"
    assert StripeService._normalize_subscription_status("paused") == "failed_payment"
    assert StripeService._normalize_subscription_status("unknown") == "incomplete"


def test_stripe_service_generate_payment_checkout_builds_expected_payload(monkeypatch):
    captured = {}

    def _create(payload):
        captured["payload"] = payload
        return SimpleNamespace(url="https://checkout.stripe.test")

    monkeypatch.setattr(
        "src.services.stripe_service.stripe_client.v1.checkout.sessions.create",
        _create,
    )

    response = StripeService.generate_payment_checkout(uuid4())

    assert response == {"url_session": "https://checkout.stripe.test"}
    assert captured["payload"]["mode"] == "subscription"
    assert captured["payload"]["currency"] == "brl"


def test_stripe_service_get_uba_context_returns_institution_and_profile():
    institution = SimpleNamespace(id=uuid4(), name="UBA")
    profile = SimpleNamespace(id=uuid4(), name="basic_uba_user")
    db = FakeAsyncSession(
        execute_results=[
            FakeExecuteResult(scalars_items=[institution]),
            FakeExecuteResult(scalars_items=[profile]),
        ]
    )

    response = asyncio.run(StripeService._get_uba_context(db))

    assert response == (institution, profile)


def test_stripe_service_get_subscription_by_stripe_id_handles_missing_id():
    response = asyncio.run(
        StripeService._get_subscription_by_stripe_id(FakeAsyncSession(), None)
    )

    assert response is None


def test_stripe_service_get_subscription_by_stripe_id_returns_subscription():
    subscription = SimpleNamespace(stripe_subscription_id="sub_123")
    db = FakeAsyncSession(execute_results=[FakeExecuteResult(scalars_items=[subscription])])

    response = asyncio.run(
        StripeService._get_subscription_by_stripe_id(db, "sub_123")
    )

    assert response is subscription


def test_stripe_service_get_user_institution_returns_membership():
    membership = SimpleNamespace(user_id=uuid4())
    db = FakeAsyncSession(execute_results=[FakeExecuteResult(scalars_items=[membership])])

    response = asyncio.run(
        StripeService._get_user_institution(db, uuid4(), uuid4())
    )

    assert response is membership


def test_stripe_service_upsert_subscription_updates_existing_period_change(monkeypatch):
    current_period_end = datetime.now()
    next_period_end = current_period_end + timedelta(days=30)
    existing = SimpleNamespace(
        user_id=uuid4(),
        status="active",
        price_id="old_price",
        stripe_customer_id="cus_old",
        current_period_end=current_period_end,
        questions_generated_in_cycle=3,
        questions_generation_cycle_end=current_period_end,
        updated_at=None,
    )

    async def _existing(*args, **kwargs):
        return existing

    monkeypatch.setattr(
        StripeService, "_get_subscription_by_stripe_id", staticmethod(_existing)
    )

    subscription, operation = asyncio.run(
        StripeService._upsert_subscription(
            FakeAsyncSession(),
            uuid4(),
            "sub_123",
            "active",
            "new_price",
            stripe_customer_id="cus_new",
            current_period_end=next_period_end,
        )
    )

    assert subscription is existing
    assert operation == "updated"
    assert existing.questions_generated_in_cycle == 0
    assert existing.questions_generation_cycle_end == next_period_end
    assert existing.price_id == "new_price"


def test_stripe_service_upsert_subscription_updates_cycle_end_when_missing(monkeypatch):
    current_period_end = datetime.now() + timedelta(days=30)
    existing = SimpleNamespace(
        user_id=uuid4(),
        status="active",
        price_id="old_price",
        stripe_customer_id="cus_old",
        current_period_end=current_period_end,
        questions_generated_in_cycle=1,
        questions_generation_cycle_end=None,
        updated_at=None,
    )

    async def _existing(*args, **kwargs):
        return existing

    monkeypatch.setattr(
        StripeService, "_get_subscription_by_stripe_id", staticmethod(_existing)
    )

    subscription, operation = asyncio.run(
        StripeService._upsert_subscription(
            FakeAsyncSession(),
            uuid4(),
            "sub_123",
            "active",
            None,
            stripe_customer_id=None,
            current_period_end=None,
        )
    )

    assert subscription is existing
    assert operation == "updated"
    assert existing.questions_generation_cycle_end == current_period_end


def test_stripe_service_upsert_subscription_creates_new(sample_ids):
    db = FakeAsyncSession()

    subscription, operation = asyncio.run(
        StripeService._upsert_subscription(
            db,
            sample_ids.user_id,
            "sub_123",
            "active",
            "price_test",
            stripe_customer_id="cus_123",
            current_period_end=datetime.now() + timedelta(days=30),
        )
    )

    assert operation == "created"
    assert len(db.added) == 1
    assert subscription.stripe_subscription_id == "sub_123"


def test_stripe_service_grant_user_access_updates_existing_membership(monkeypatch):
    membership = SimpleNamespace(profile_id=uuid4(), updated_at=None)
    new_profile_id = uuid4()

    async def _membership(*args, **kwargs):
        return membership

    monkeypatch.setattr(
        StripeService, "_get_user_institution", staticmethod(_membership)
    )

    response = asyncio.run(
        StripeService._grant_user_access(
            FakeAsyncSession(), uuid4(), uuid4(), new_profile_id
        )
    )

    assert response == "updated"
    assert membership.profile_id == new_profile_id


def test_stripe_service_grant_user_access_keeps_existing_membership(monkeypatch):
    profile_id = uuid4()
    membership = SimpleNamespace(profile_id=profile_id, updated_at=None)

    async def _membership(*args, **kwargs):
        return membership

    monkeypatch.setattr(
        StripeService, "_get_user_institution", staticmethod(_membership)
    )

    response = asyncio.run(
        StripeService._grant_user_access(
            FakeAsyncSession(), uuid4(), uuid4(), profile_id
        )
    )

    assert response == "unchanged"


def test_stripe_service_grant_user_access_creates_membership(monkeypatch):
    db = FakeAsyncSession()

    async def _membership(*args, **kwargs):
        return None

    monkeypatch.setattr(
        StripeService, "_get_user_institution", staticmethod(_membership)
    )

    response = asyncio.run(
        StripeService._grant_user_access(db, uuid4(), uuid4(), uuid4())
    )

    assert response == "created"
    assert len(db.added) == 1


def test_stripe_service_revoke_user_access_handles_missing_membership(monkeypatch):
    async def _membership(*args, **kwargs):
        return None

    monkeypatch.setattr(
        StripeService, "_get_user_institution", staticmethod(_membership)
    )

    response = asyncio.run(
        StripeService._revoke_user_access(FakeAsyncSession(), uuid4(), uuid4())
    )

    assert response == "unchanged"


def test_stripe_service_revoke_user_access_deletes_membership(monkeypatch):
    membership = SimpleNamespace(id=uuid4())
    db = FakeAsyncSession()

    async def _membership(*args, **kwargs):
        return membership

    monkeypatch.setattr(
        StripeService, "_get_user_institution", staticmethod(_membership)
    )

    response = asyncio.run(StripeService._revoke_user_access(db, uuid4(), uuid4()))

    assert response == "deleted"
    assert db.deleted == [membership]


def test_stripe_service_sync_user_access_requires_seed_data(monkeypatch):
    async def _context(*args, **kwargs):
        return None, None

    monkeypatch.setattr(StripeService, "_get_uba_context", staticmethod(_context))

    with pytest.raises(ValueError) as exc:
        asyncio.run(StripeService._sync_user_access(FakeAsyncSession(), uuid4(), "active"))

    assert "seed data for UBA institution/profile" in str(exc.value)


def test_stripe_service_sync_user_access_grants_active_access(monkeypatch):
    institution = SimpleNamespace(id=uuid4())
    profile = SimpleNamespace(id=uuid4())

    async def _context(*args, **kwargs):
        return institution, profile

    async def _grant(*args, **kwargs):
        return "created"

    monkeypatch.setattr(StripeService, "_get_uba_context", staticmethod(_context))
    monkeypatch.setattr(StripeService, "_grant_user_access", staticmethod(_grant))

    response = asyncio.run(StripeService._sync_user_access(FakeAsyncSession(), uuid4(), "active"))

    assert response == "created"


def test_stripe_service_sync_user_access_revokes_inactive_access(monkeypatch):
    institution = SimpleNamespace(id=uuid4())
    profile = SimpleNamespace(id=uuid4())

    async def _context(*args, **kwargs):
        return institution, profile

    async def _revoke(*args, **kwargs):
        return "deleted"

    monkeypatch.setattr(StripeService, "_get_uba_context", staticmethod(_context))
    monkeypatch.setattr(StripeService, "_revoke_user_access", staticmethod(_revoke))

    response = asyncio.run(
        StripeService._sync_user_access(FakeAsyncSession(), uuid4(), "failed_payment")
    )

    assert response == "deleted"


def test_stripe_service_sync_subscription_from_event_ignores_missing_user(monkeypatch):
    existing = None

    async def _existing(*args, **kwargs):
        return existing

    monkeypatch.setattr(
        StripeService, "_get_subscription_by_stripe_id", staticmethod(_existing)
    )

    response = asyncio.run(
        StripeService._sync_subscription_from_subscription_event(
            {"type": "customer.subscription.created", "data": {"object": {"id": "sub_123"}}},
            FakeAsyncSession(),
        )
    )

    assert response == {
        "status": "ignored",
        "reason": "user_id_not_found",
        "event": "customer.subscription.created",
    }


def test_stripe_service_sync_subscription_from_event_processes_payload(monkeypatch):
    subscription = SimpleNamespace(stripe_subscription_id="sub_123", status="active")
    db = FakeAsyncSession()

    async def _existing(*args, **kwargs):
        return SimpleNamespace(user_id=uuid4())

    async def _upsert_subscription(**kwargs):
        return subscription, "updated"

    async def _sync_access(*args, **kwargs):
        return "created"

    monkeypatch.setattr(
        StripeService, "_get_subscription_by_stripe_id", staticmethod(_existing)
    )
    monkeypatch.setattr(
        StripeService, "_upsert_subscription", staticmethod(_upsert_subscription)
    )
    monkeypatch.setattr(
        StripeService, "_sync_user_access", staticmethod(_sync_access)
    )

    response = asyncio.run(
        StripeService._sync_subscription_from_subscription_event(
            {
                "type": "customer.subscription.updated",
                "data": {
                    "object": {
                        "id": "sub_123",
                        "status": "active",
                        "metadata": {"user_id": str(uuid4()), "price_id": "price_test"},
                        "customer": "cus_123",
                        "current_period_end": 1_700_000_000,
                    }
                },
            },
            db,
            forced_status=None,
        )
    )

    assert response["status"] == "processed"
    assert response["subscription_action"] == "updated"
    assert response["access_action"] == "created"


def test_stripe_service_checkout_session_completed_ignores_missing_user():
    response = asyncio.run(
        StripeService.checkout_session_completed(
            {"type": "checkout.session.completed", "data": {"object": {}}},
            FakeAsyncSession(),
        )
    )

    assert response == {
        "status": "ignored",
        "reason": "user_id_not_found",
        "event": "checkout.session.completed",
    }


def test_stripe_service_checkout_session_completed_updates_existing_subscription(monkeypatch):
    existing = SimpleNamespace(
        status="active",
        stripe_customer_id=None,
        price_id=None,
        updated_at=None,
    )

    async def _existing(*args, **kwargs):
        return existing

    async def _sync_access(*args, **kwargs):
        return "updated"

    monkeypatch.setattr(
        StripeService, "_get_subscription_by_stripe_id", staticmethod(_existing)
    )
    monkeypatch.setattr(
        StripeService, "_sync_user_access", staticmethod(_sync_access)
    )

    response = asyncio.run(
        StripeService.checkout_session_completed(
            {
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "client_reference_id": str(uuid4()),
                        "subscription": "sub_123",
                        "customer": "cus_123",
                        "metadata": {"price_id": "price_test", "user_id": str(uuid4())},
                    }
                },
            },
            FakeAsyncSession(),
        )
    )

    assert response["status"] == "processed"
    assert response["subscription_action"] == "updated"
    assert response["access_action"] == "updated"


def test_stripe_service_checkout_session_completed_creates_subscription(monkeypatch):
    async def _existing(*args, **kwargs):
        return None

    async def _upsert_subscription(**kwargs):
        return SimpleNamespace(stripe_subscription_id="sub_123"), "created"

    monkeypatch.setattr(
        StripeService, "_get_subscription_by_stripe_id", staticmethod(_existing)
    )
    monkeypatch.setattr(
        StripeService, "_upsert_subscription", staticmethod(_upsert_subscription)
    )

    response = asyncio.run(
        StripeService.checkout_session_completed(
            {
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "client_reference_id": str(uuid4()),
                        "subscription": "sub_123",
                        "customer": "cus_123",
                    }
                },
            },
            FakeAsyncSession(),
        )
    )

    assert response["subscription_action"] == "created"
    assert response["subscription_status"] == "incomplete"


def test_stripe_service_subscription_event_wrappers_delegate(monkeypatch):
    calls = []

    async def _sync(data, db, forced_status=None):
        calls.append(forced_status)
        return {"forced_status": forced_status}

    monkeypatch.setattr(
        StripeService, "_sync_subscription_from_subscription_event", staticmethod(_sync)
    )

    created = asyncio.run(StripeService.customer_subscription_created({}, FakeAsyncSession()))
    updated = asyncio.run(StripeService.customer_subscription_updated({}, FakeAsyncSession()))
    paused = asyncio.run(StripeService.customer_subscription_paused({}, FakeAsyncSession()))
    resumed = asyncio.run(StripeService.customer_subscription_resumed({}, FakeAsyncSession()))
    deleted = asyncio.run(StripeService.customer_subscription_deleted({}, FakeAsyncSession()))

    assert created == {"forced_status": None}
    assert updated == {"forced_status": None}
    assert paused == {"forced_status": "failed_payment"}
    assert resumed == {"forced_status": None}
    assert deleted == {"forced_status": "canceled"}
    assert calls == [None, None, "failed_payment", None, "canceled"]


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


def test_stripe_service_invoice_payment_succeeded_ignores_missing_subscription():
    response = asyncio.run(
        StripeService.invoice_payment_succeeded(
            {"type": "invoice.payment_succeeded", "data": {"object": {}}},
            FakeAsyncSession(),
        )
    )

    assert response == {
        "status": "ignored",
        "reason": "subscription_not_found",
        "event": "invoice.payment_succeeded",
    }


def test_stripe_service_invoice_payment_succeeded_ignores_missing_user(monkeypatch):
    async def _existing(*args, **kwargs):
        return None

    monkeypatch.setattr(
        StripeService, "_get_subscription_by_stripe_id", staticmethod(_existing)
    )

    response = asyncio.run(
        StripeService.invoice_payment_succeeded(
            {
                "type": "invoice.payment_succeeded",
                "data": {"object": {"subscription": "sub_123"}},
            },
            FakeAsyncSession(),
        )
    )

    assert response == {
        "status": "ignored",
        "reason": "user_id_not_found",
        "event": "invoice.payment_succeeded",
    }


def test_stripe_service_invoice_paid_delegates(monkeypatch):
    async def _invoice_payment_succeeded(data, db):
        return {"delegated": True}

    monkeypatch.setattr(
        StripeService, "invoice_payment_succeeded", staticmethod(_invoice_payment_succeeded)
    )

    response = asyncio.run(StripeService.invoice_paid({}, FakeAsyncSession()))

    assert response == {"delegated": True}


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


def test_stripe_service_invoice_payment_failed_ignores_missing_subscription():
    response = asyncio.run(
        StripeService.invoice_payment_failed(
            {"type": "invoice.payment_failed", "data": {"object": {}}},
            FakeAsyncSession(),
        )
    )

    assert response == {
        "status": "ignored",
        "reason": "subscription_not_found",
        "event": "invoice.payment_failed",
    }


def test_stripe_service_invoice_payment_failed_ignores_missing_user(monkeypatch):
    async def _existing(*args, **kwargs):
        return None

    monkeypatch.setattr(
        StripeService, "_get_subscription_by_stripe_id", staticmethod(_existing)
    )

    response = asyncio.run(
        StripeService.invoice_payment_failed(
            {
                "type": "invoice.payment_failed",
                "data": {"object": {"subscription": "sub_123"}},
            },
            FakeAsyncSession(),
        )
    )

    assert response == {
        "status": "ignored",
        "reason": "user_id_not_found",
        "event": "invoice.payment_failed",
    }


def test_stripe_service_invoice_payment_failed_processes_failed_payment(monkeypatch):
    existing_subscription = SimpleNamespace(
        current_period_end=datetime.now() + timedelta(days=30),
        user_id=uuid4(),
    )
    created_subscription = SimpleNamespace(
        stripe_subscription_id="sub_123",
        status="failed_payment",
    )

    async def _get_subscription(*args, **kwargs):
        return existing_subscription

    async def _upsert_subscription(**kwargs):
        assert kwargs["status"] == "failed_payment"
        return created_subscription, "updated"

    async def _sync_user_access(*args, **kwargs):
        return "deleted"

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
                        "billing_reason": "manual",
                        "metadata": {
                            "user_id": str(existing_subscription.user_id),
                            "price_id": "price_test",
                        },
                    }
                },
            },
            FakeAsyncSession(),
        )
    )

    assert response["status"] == "processed"
    assert response["subscription_status"] == "failed_payment"


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


def test_ai_anatomy_service_generate_response_handles_empty_recent_questions(monkeypatch):
    captured = {}

    def _create(*, model, input):
        captured["input"] = input
        return SimpleNamespace(id="response-123")

    monkeypatch.setattr(ai_anatomy_service_module.client.responses, "create", _create)

    asyncio.run(
        AIAnatomyService.generate_response(
            parameter="Neuroanatomy",
            subtopic="cerebelo",
            subtopic_description="estrutura do cerebelo",
            diversity_mode="relationship",
            correct_letter="B",
            recent_questions=[],
        )
    )

    assert "There are no recent questions to avoid repetition." in captured["input"]


def test_stripe_service_parse_uuid_returns_uuid(sample_ids):
    assert StripeService._parse_uuid(str(sample_ids.user_id)) == sample_ids.user_id
    assert isinstance(StripeService._parse_uuid(str(sample_ids.user_id)), UUID)


def test_stripe_service_parse_uuid_returns_none_for_invalid_value():
    assert StripeService._parse_uuid("invalid") is None


def test_stripe_service_unix_to_datetime_handles_none():
    assert StripeService._unix_to_datetime(None) is None
