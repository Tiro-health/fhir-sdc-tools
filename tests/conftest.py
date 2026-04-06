"""Shared test fixtures."""

from __future__ import annotations

import pytest

from sdc.models import Questionnaire, QuestionnaireItem, QuestionnaireItemType


@pytest.fixture
def empty_questionnaire() -> Questionnaire:
    return Questionnaire(url="http://example.org/q1", title="Test")


@pytest.fixture
def questionnaire_with_items() -> Questionnaire:
    return Questionnaire(
        url="http://example.org/q1",
        title="Test",
        item=[
            QuestionnaireItem(
                link_id="1", text="Name", type=QuestionnaireItemType.STRING
            ),
            QuestionnaireItem(
                link_id="2",
                text="Details",
                type=QuestionnaireItemType.GROUP,
                item=[
                    QuestionnaireItem(
                        link_id="2.1",
                        text="Age",
                        type=QuestionnaireItemType.INTEGER,
                    ),
                ],
            ),
        ],
    )
