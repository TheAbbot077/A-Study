import pytest


@pytest.mark.django_db
def test_classroom_app_is_importable():
    from apps.classroom_learning.domain.models import LessonPreparation

    assert LessonPreparation.__name__ == "LessonPreparation"
