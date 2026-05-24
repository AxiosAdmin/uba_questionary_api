from typing import Optional
import datetime
import uuid

from sqlalchemy import (
    Boolean,
    CHAR,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    PrimaryKeyConstraint,
    String,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Institutions(Base):
    __tablename__ = "institutions"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="institutions_pkey"),
        UniqueConstraint("name", name="institutions_name_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

    questions: Mapped[list["Questions"]] = relationship(
        "Questions", back_populates="institution"
    )
    users_institutions: Mapped[list["UsersInstitutions"]] = relationship(
        "UsersInstitutions", back_populates="institution"
    )


class Profiles(Base):
    __tablename__ = "profiles"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="profiles_pkey"),
        UniqueConstraint("name", name="profiles_name_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("now()")
    )
    questions_create_limit: Mapped[Optional[int]] = mapped_column(Integer)
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

    users_institutions: Mapped[list["UsersInstitutions"]] = relationship(
        "UsersInstitutions", back_populates="profile"
    )


class Users(Base):
    __tablename__ = "users"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="users_pkey"),
        UniqueConstraint("email_hash", name="users_email_hash_key"),
        UniqueConstraint("nickname_hash", name="users_nickname_hash_key"),
        UniqueConstraint("cbu_hash", name="users_cbu_hash_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    email_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    nickname: Mapped[str] = mapped_column(Text, nullable=False)
    nickname_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    cbu: Mapped[str] = mapped_column(Text, nullable=False)
    cbu_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    password: Mapped[str] = mapped_column(Text, nullable=False)
    global_role: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default=text("'User'::character varying")
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

    question: Mapped[list["Questions"]] = relationship(
        "Questions", secondary="favorite_questions", back_populates="user"
    )
    subscriptions: Mapped[list["Subscriptions"]] = relationship(
        "Subscriptions", back_populates="user"
    )
    user_feedback: Mapped[list["UserFeedback"]] = relationship(
        "UserFeedback", back_populates="user"
    )
    users_institutions: Mapped[list["UsersInstitutions"]] = relationship(
        "UsersInstitutions", back_populates="user"
    )
    question_answers: Mapped[list["QuestionAnswers"]] = relationship(
        "QuestionAnswers", back_populates="user"
    )


class Questions(Base):
    __tablename__ = "questions"
    __table_args__ = (
        CheckConstraint(
            "correct_answer = ANY (ARRAY['A'::bpchar, 'B'::bpchar, 'C'::bpchar, 'D'::bpchar, 'E'::bpchar])",
            name="questions_correct_answer_check",
        ),
        ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name="questions_institution_id_fkey",
        ),
        PrimaryKeyConstraint("id", name="questions_pkey"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    topic: Mapped[str] = mapped_column(String(100), nullable=False)
    subtopic: Mapped[str] = mapped_column(Text, nullable=False)
    subtopic_description: Mapped[str] = mapped_column(Text, nullable=False)
    diversity_mode: Mapped[str] = mapped_column(Text, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer_a: Mapped[str] = mapped_column(Text, nullable=False)
    answer_b: Mapped[str] = mapped_column(Text, nullable=False)
    answer_c: Mapped[str] = mapped_column(Text, nullable=False)
    answer_d: Mapped[str] = mapped_column(Text, nullable=False)
    explanation_a: Mapped[str] = mapped_column(Text, nullable=False)
    explanation_b: Mapped[str] = mapped_column(Text, nullable=False)
    explanation_c: Mapped[str] = mapped_column(Text, nullable=False)
    explanation_d: Mapped[str] = mapped_column(Text, nullable=False)
    correct_answer: Mapped[str] = mapped_column(CHAR(1), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("now()")
    )
    answer_e: Mapped[Optional[str]] = mapped_column(Text)
    explanation_e: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

    institution: Mapped["Institutions"] = relationship(
        "Institutions", back_populates="questions"
    )
    user: Mapped[list["Users"]] = relationship(
        "Users", secondary="favorite_questions", back_populates="question"
    )
    question_answers: Mapped[list["QuestionAnswers"]] = relationship(
        "QuestionAnswers", back_populates="question"
    )
    question_feedbacks: Mapped[list["QuestionFeedbacks"]] = relationship(
        "QuestionFeedbacks", back_populates="question"
    )


class Subscriptions(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint(
            "status::text = ANY (ARRAY['active'::character varying, 'failed_payment'::character varying, 'canceled'::character varying, 'incomplete'::character varying, 'trialing'::character varying]::text[])",
            name="subscriptions_status_check",
        ),
        ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="subscriptions_user_id_fkey"
        ),
        PrimaryKeyConstraint("id", name="subscriptions_pkey"),
        UniqueConstraint(
            "stripe_subscription_id", name="subscriptions_stripe_subscription_id_key"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    stripe_subscription_id: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    price_id: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("now()")
    )
    questions_generated_in_cycle: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(Text)
    current_period_end: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    questions_generation_cycle_end: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime
    )

    user: Mapped["Users"] = relationship("Users", back_populates="subscriptions")


class UserFeedback(Base):
    __tablename__ = "user_feedback"
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="user_feedback_user_id_fkey"
        ),
        PrimaryKeyConstraint("id", name="user_feedback_pkey"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    text_feedback: Mapped[str] = mapped_column(Text, nullable=False)

    user: Mapped["Users"] = relationship("Users", back_populates="user_feedback")


class UsersInstitutions(Base):
    __tablename__ = "users_institutions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name="users_institutions_institution_id_fkey",
        ),
        ForeignKeyConstraint(
            ["profile_id"], ["profiles.id"], name="users_institutions_profile_id_fkey"
        ),
        ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="users_institutions_user_id_fkey"
        ),
        PrimaryKeyConstraint(
            "user_id", "institution_id", name="users_institutions_pkey"
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    institution_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    profile_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

    institution: Mapped["Institutions"] = relationship(
        "Institutions", back_populates="users_institutions"
    )
    profile: Mapped["Profiles"] = relationship(
        "Profiles", back_populates="users_institutions"
    )
    user: Mapped["Users"] = relationship("Users", back_populates="users_institutions")


t_favorite_questions = Table(
    "favorite_questions",
    Base.metadata,
    Column("user_id", Uuid, primary_key=True),
    Column("question_id", Uuid, primary_key=True),
    ForeignKeyConstraint(
        ["question_id"], ["questions.id"], name="favorite_questions_question_id_fkey"
    ),
    ForeignKeyConstraint(
        ["user_id"], ["users.id"], name="favorite_questions_user_id_fkey"
    ),
    PrimaryKeyConstraint("user_id", "question_id", name="favorite_questions_pkey"),
)


class QuestionAnswers(Base):
    __tablename__ = "question_answers"
    __table_args__ = (
        CheckConstraint(
            "answer = ANY (ARRAY['A'::bpchar, 'B'::bpchar, 'C'::bpchar, 'D'::bpchar, 'E'::bpchar])",
            name="question_answers_answer_check",
        ),
        ForeignKeyConstraint(
            ["question_id"], ["questions.id"], name="question_answers_question_id_fkey"
        ),
        ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="question_answers_user_id_fkey"
        ),
        PrimaryKeyConstraint("id", name="question_answers_pkey"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    question_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    answer: Mapped[str] = mapped_column(CHAR(1), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

    question: Mapped["Questions"] = relationship(
        "Questions", back_populates="question_answers"
    )
    user: Mapped["Users"] = relationship("Users", back_populates="question_answers")


class QuestionFeedbacks(Base):
    __tablename__ = "question_feedbacks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["question_id"],
            ["questions.id"],
            name="question_feedbacks_question_id_fkey",
        ),
        PrimaryKeyConstraint("id", name="question_feedbacks_pkey"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    question_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    is_liked: Mapped[bool] = mapped_column(Boolean, nullable=False)
    feedback: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

    question: Mapped["Questions"] = relationship(
        "Questions", back_populates="question_feedbacks"
    )
