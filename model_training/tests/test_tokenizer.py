from training.data.tokenizer import ReversibleByteTokenizer, tokenizer_metrics


def test_quranic_arabic_and_urdu_are_reversible():
    tokenizer = ReversibleByteTokenizer()
    samples = {"arabic": ["بِسْمِ اللَّهِ"], "urdu": ["عدل اور رحمت"], "english": ["Justice and mercy"]}
    metrics = tokenizer_metrics(tokenizer, samples)
    assert all(item["reversible"] and item["diacritics_preserved"] for item in metrics.values())
    assert all(item["fertility"] > 0 for item in metrics.values())

