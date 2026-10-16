"""SkillProof Engine module — Evidence-backed skill proof and legitimate code similarity checking."""

from app.services.skillproof.detector import SkillDetectorAndMapper, detect_file_language, is_irrelevant_file
from app.services.skillproof.engine import SkillProofEngine, skillproof_engine
from app.services.skillproof.reference_corpus import (
    ReferenceSource,
    reference_registry,
)
from app.services.skillproof.similarity import CodeSimilarityEngine, similarity_engine

__all__ = [
    "SkillProofEngine",
    "skillproof_engine",
    "SkillDetectorAndMapper",
    "detect_file_language",
    "is_irrelevant_file",
    "CodeSimilarityEngine",
    "similarity_engine",
    "ReferenceSource",
    "reference_registry",
]
