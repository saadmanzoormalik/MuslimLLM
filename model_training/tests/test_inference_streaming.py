import torch

from serving.engine import InferenceEngine
from training.config import ModelConfig
from training.data.tokenizer import ReversibleByteTokenizer
from training.model import MuslimLLM


def test_inference_streams_and_never_succeeds_empty():
    model = MuslimLLM(ModelConfig(vocabulary_size=256, hidden_size=16, intermediate_size=32, num_layers=1, num_attention_heads=2, num_key_value_heads=1, max_position_embeddings=64))
    output = list(InferenceEngine(model, ReversibleByteTokenizer()).stream("test", 3))
    assert len(output) == 3

