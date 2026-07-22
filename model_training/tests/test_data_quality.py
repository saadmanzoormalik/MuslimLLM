from training.data.quality import quality_components


def test_quality_components_remain_auditable():
    result = quality_components("A varied educational text with reference 2024.", source_authority=0.9)
    assert 0 <= result["weighted_quality_score"] <= 1
    assert len(result) > 5 and "source_authority" in result

