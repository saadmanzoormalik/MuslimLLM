from dataclasses import dataclass
import random


@dataclass(frozen=True)
class CurriculumPhase:
    start_step: int
    domains: tuple[str, ...]
    minimum_quality: float
    maximum_complexity: float = 1.0


class Curriculum:
    def __init__(self, phases: list[CurriculumPhase], seed: int = 17):
        self.phases, self.seed = sorted(phases, key=lambda phase: phase.start_step), seed

    def phase_at(self, step: int):
        return max((phase for phase in self.phases if phase.start_step <= step), key=lambda phase: phase.start_step)

    def sample(self, records, step: int, count: int):
        phase = self.phase_at(step)
        eligible = [record for record in records if record.domain in phase.domains and record.quality_score >= phase.minimum_quality]
        rng = random.Random(self.seed + step)
        return [eligible[rng.randrange(len(eligible))] for _ in range(count)] if eligible else []

