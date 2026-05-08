"""Service functions for question answers queries."""

from uuid import UUID

from sqlalchemy import func, select

from src.models import QuestionAnswers, Questions
from src.schemas.questions_answers_schema import UserQuestionWithLatestAnswerSchema


class QuestionAnswersService:
    """Service for handling question answer operations."""

    @staticmethod
    async def get_questions_with_latest_user_answers(
        user_id: UUID,
        db,
    ):
        """
        Return only questions that have a latest answer sent by the given user.

        The underlying SQL shape is equivalent to:

        SELECT
            q.*,
            qa_latest.answer AS user_answer,
            qa_latest.user_id,
            qa_latest.created_at AS answered_at,
            qa_latest.updated_at AS answer_updated_at
        FROM questions q
        JOIN (
            SELECT *
            FROM (
                SELECT
                    qa.question_id,
                    qa.user_id,
                    qa.answer,
                    qa.created_at,
                    qa.updated_at,
                    ROW_NUMBER() OVER (
                        PARTITION BY qa.question_id
                        ORDER BY qa.created_at DESC, qa.id DESC
                    ) AS row_num
                FROM question_answers qa
                WHERE qa.user_id = :user_id
            ) ranked_answers
            WHERE ranked_answers.row_num = 1
        ) qa_latest ON qa_latest.question_id = q.id
        ORDER BY q.created_at;
        """
        latest_answers_subquery = (
            select(
                QuestionAnswers.question_id.label("question_id"),
                QuestionAnswers.user_id.label("user_id"),
                QuestionAnswers.answer.label("user_answer"),
                QuestionAnswers.created_at.label("answered_at"),
                QuestionAnswers.updated_at.label("answer_updated_at"),
                func.row_number()
                .over(
                    partition_by=QuestionAnswers.question_id,
                    order_by=(
                        QuestionAnswers.created_at.desc(),
                        QuestionAnswers.id.desc(),
                    ),
                )
                .label("row_num"),
            )
            .where(QuestionAnswers.user_id == user_id)
            .subquery()
        )

        latest_ranked_answers_subquery = (
            select(
                latest_answers_subquery.c.question_id,
                latest_answers_subquery.c.user_id,
                latest_answers_subquery.c.user_answer,
                latest_answers_subquery.c.answered_at,
                latest_answers_subquery.c.answer_updated_at,
            )
            .where(latest_answers_subquery.c.row_num == 1)
            .subquery()
        )

        query = (
            select(
                Questions,
                latest_ranked_answers_subquery.c.user_answer,
                latest_ranked_answers_subquery.c.user_id,
                latest_ranked_answers_subquery.c.answered_at,
                latest_ranked_answers_subquery.c.answer_updated_at,
            )
            .join(
                latest_ranked_answers_subquery,
                latest_ranked_answers_subquery.c.question_id == Questions.id,
            )
            .where(latest_ranked_answers_subquery.c.user_id == user_id)
            .order_by(Questions.created_at)
        )

        result = await db.execute(query)

        return {
            "data": [
                UserQuestionWithLatestAnswerSchema(
                    id=question.id,
                    institution_id=question.institution_id,
                    topic=question.topic,
                    subject=question.subtopic,
                    question=question.question,
                    answer_a=question.answer_a,
                    answer_b=question.answer_b,
                    answer_c=question.answer_c,
                    answer_d=question.answer_d,
                    answer_e=question.answer_e,
                    explanation_a=question.explanation_a,
                    explanation_b=question.explanation_b,
                    explanation_c=question.explanation_c,
                    explanation_d=question.explanation_d,
                    explanation_e=question.explanation_e,
                    correct_answer=question.correct_answer,
                    created_at=question.created_at,
                    updated_at=question.updated_at,
                    user_answer=user_answer,
                    user_id=answered_user_id,
                    answered_at=answered_at,
                    answer_updated_at=answer_updated_at,
                )
                for (
                    question,
                    user_answer,
                    answered_user_id,
                    answered_at,
                    answer_updated_at,
                ) in result.all()
            ]
        }
