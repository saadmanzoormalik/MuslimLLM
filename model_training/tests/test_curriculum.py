from training.data.curriculum import Curriculum, CurriculumPhase
from training.data.registry import DataRecord


def test_curriculum_is_reproducible():
    records = [DataRecord(str(i), "public-domain", "en", "general", f"text {i}", "public-domain", "primary", quality_score=0.9) for i in range(5)]
    curriculum = Curriculum([CurriculumPhase(0, ("general",), 0.8)], seed=9)
    assert [r.source for r in curriculum.sample(records, 4, 5)] == [r.source for r in curriculum.sample(records, 4, 5)]

