"""Controller for AI-generated biology questions."""

import uuid
import json
import random
from fastapi import HTTPException

from src.services.ai_biology_service import AIBiologyService
from src.services.questions_service import QuestionsService
from src.services.subscription_service import SubscriptionService

from src.helpers.biologia_questionary_text import BIOLOGY_DIVERSITY_MODES
from src.helpers.check_subtopic import check_biology_sub_topic


class AIBiologyController:
    """Controller for handling AI biology question generation."""

    @staticmethod
    async def generate_question(parameter: str, db, institution_id, user_id):
        """
        Generate a biology question using AI based on the specified parameter.

        Args:
            parameter: The biology topic parameter
            institution_id: The institution ID from the request header
            user_id: Authenticated user ID from the JWT token

        Returns:
            dict: JSON response containing the generated question data
        """

        if institution_id is None:
            raise HTTPException(
                status_code=400,
                detail="institution_id is required and must be a valid UUID.",
            )

        if not isinstance(institution_id, uuid.UUID):
            try:
                institution_id = uuid.UUID(institution_id)
            except ValueError as e:
                raise ValueError(
                    "Invalid institution_id format. Must be a valid UUID."
                ) from e

        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Authenticated user is required to generate questions.",
            )

        await SubscriptionService.validate_question_generation_availability(
            user_id=user_id,
            institution_id=institution_id,
            db=db,
        )

        used_diversity_mode = random.choice(BIOLOGY_DIVERSITY_MODES)
        used_subtopic, used_subtopic_description = check_biology_sub_topic(parameter)
        used_correct_letter = random.choice(["A", "B", "C", "D"])
        last_questions = await QuestionsService.get_last_three_questions(
            parameter, used_subtopic, db
        )

        response = await AIBiologyService.generate_response(
            parameter,
            used_subtopic,
            used_subtopic_description,
            used_diversity_mode,
            used_correct_letter,
            last_questions,
        )

        json_response = json.loads(response.output[0].content[0].text)
        json_response["topic"] = parameter
        json_response["subtopic"] = used_subtopic
        json_response["subtopic_description"] = used_subtopic_description
        json_response["diversity_mode"] = used_diversity_mode
        json_response["institution_id"] = institution_id

        (
            question_response,
            question_generation_usage,
        ) = await SubscriptionService.create_question_and_consume_quota(
            user_id=user_id,
            institution_id=institution_id,
            question_payload=json_response,
            db=db,
        )

        return {
            "data": question_response,
            "question_generation_usage": question_generation_usage,
        }
