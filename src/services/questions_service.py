from sqlalchemy import select
from api_crud_generate_libary.services.service import Service

from src.models import Questions
from src.schemas.questions_schemas import OnlyQuestionsGetSchema

questions_service = Service(Questions)


class QuestionsService:
    @staticmethod
    async def get_last_three_questions(topic, subtopic, db) -> list:
        """Fetch the last three questions from the database."""
        async with db as session:
            query = (
                select(Questions)
                .where(
                    Questions.topic == topic,
                    Questions.subtopic == subtopic,
                )
                .order_by(Questions.created_at.desc())
                .limit(3)
            )

            result = await session.execute(query)
            response = result.scalars().all()

            if len(response) > 0:
                return [
                    OnlyQuestionsGetSchema.model_validate(item) for item in response
                ]

            return []
