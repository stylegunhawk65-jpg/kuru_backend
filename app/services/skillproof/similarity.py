"""Multi-modal code similarity calculation engine.

Supports exact, normalized, token-based, and AST-based comparisons against legitimate reference sources.
Never executes code; uses static inspection, AST parsing, and lexical tokens exclusively.
"""

import ast
import difflib
import logging
import re
import tokenize
from typing import Any
from io import BytesIO

from app.services.skillproof.reference_corpus import ReferenceSource, reference_registry

logger = logging.getLogger("kuru.skillproof.similarity")


class CodeSimilarityEngine:
    """Calculates code similarity across exact, normalized, token, and AST modalities."""

    # -------------------------------------------------------------------------
    # 1. Exact Matching
    # -------------------------------------------------------------------------
    @staticmethod
    def calculate_exact_similarity(source_code: str, reference_code: str) -> tuple[float, list[str]]:
        """Calculate exact block matching between source and reference code.
        
        Returns similarity score (0.0 to 1.0) and list of matched line snippets.
        """
        source_lines = [line.rstrip() for line in source_code.splitlines() if line.strip()]
        ref_lines = [line.rstrip() for line in reference_code.splitlines() if line.strip()]

        if not source_lines or not ref_lines:
            return 0.0, []

        ref_set = set(ref_lines)
        matched = [line for line in source_lines if line in ref_set]

        score = round(len(matched) / max(len(source_lines), len(ref_lines)), 4)
        return min(1.0, max(0.0, score)), matched[:5]

    # -------------------------------------------------------------------------
    # 2. Normalized Matching
    # -------------------------------------------------------------------------
    @staticmethod
    def _strip_comments_and_normalize(code: str, language: str = "Python") -> list[str]:
        """Strip comments, collapse whitespace, and omit empty lines."""
        normalized: list[str] = []
        is_block_comment = False

        for raw_line in code.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            # JavaScript / C-style block comments
            if "/*" in line:
                is_block_comment = True
            if is_block_comment:
                if "*/" in line:
                    is_block_comment = False
                continue

            # Single line comments
            if line.startswith("#") or line.startswith("//"):
                continue

            # Remove inline comments
            line = re.sub(r"#.*$", "", line)
            line = re.sub(r"//.*$", "", line)
            line = " ".join(line.split())

            if line:
                normalized.append(line)

        return normalized

    @classmethod
    def calculate_normalized_similarity(
        cls,
        source_code: str,
        reference_code: str,
        language: str = "Python",
    ) -> tuple[float, float]:
        """Calculate normalized similarity using whitespace/comment-stripped SequenceMatcher.
        
        Returns (similarity_score, coverage_ratio).
        """
        norm_source = cls._strip_comments_and_normalize(source_code, language)
        norm_ref = cls._strip_comments_and_normalize(reference_code, language)

        if not norm_source or not norm_ref:
            return 0.0, 0.0

        sm = difflib.SequenceMatcher(None, norm_source, norm_ref)
        ratio = round(sm.ratio(), 4)

        # Coverage is the fraction of source lines appearing in matched blocks
        matched_blocks = sm.get_matching_blocks()
        total_matched_lines = sum(b.size for b in matched_blocks)
        coverage = round(total_matched_lines / max(1, len(norm_source)), 4)

        return min(1.0, max(0.0, ratio)), min(1.0, max(0.0, coverage))

    # -------------------------------------------------------------------------
    # 3. Token-Based Matching
    # -------------------------------------------------------------------------
    @staticmethod
    def _tokenize_code(code: str, language: str = "Python") -> list[str]:
        """Extract lexical token streams, ignoring whitespace and comments."""
        tokens: list[str] = []

        if language.lower() == "python":
            try:
                raw_bytes = code.encode("utf-8")
                token_gen = tokenize.tokenize(BytesIO(raw_bytes).readline)
                for tok in token_gen:
                    if tok.type not in (
                        tokenize.COMMENT,
                        tokenize.NL,
                        tokenize.NEWLINE,
                        tokenize.INDENT,
                        tokenize.DEDENT,
                        tokenize.ENCODING,
                    ):
                        tokens.append(tok.string)
                return tokens
            except Exception:
                pass  # Fall back to regex tokenizer

        # Generic lexical tokenizer for JS, YAML, etc.
        pattern = re.compile(r"[a-zA-Z_]\w*|[0-9]+|[^\s\w]")
        return pattern.findall(code)

    @classmethod
    def calculate_token_similarity(
        cls,
        source_code: str,
        reference_code: str,
        language: str = "Python",
        n_gram_size: int = 3,
    ) -> float:
        """Calculate token n-gram Jaccard similarity."""
        source_tokens = cls._tokenize_code(source_code, language)
        ref_tokens = cls._tokenize_code(reference_code, language)

        if len(source_tokens) < n_gram_size or len(ref_tokens) < n_gram_size:
            # Fall back to token SequenceMatcher if short
            if not source_tokens or not ref_tokens:
                return 0.0
            return round(difflib.SequenceMatcher(None, source_tokens, ref_tokens).ratio(), 4)

        source_ngrams = set(
            tuple(source_tokens[i : i + n_gram_size])
            for i in range(len(source_tokens) - n_gram_size + 1)
        )
        ref_ngrams = set(
            tuple(ref_tokens[i : i + n_gram_size])
            for i in range(len(ref_tokens) - n_gram_size + 1)
        )

        intersection = len(source_ngrams & ref_ngrams)
        union = len(source_ngrams | ref_ngrams)

        if union == 0:
            return 0.0

        return round(intersection / union, 4)

    # -------------------------------------------------------------------------
    # 4. AST-Based Matching (Python)
    # -------------------------------------------------------------------------
    @staticmethod
    def _normalize_ast_to_structure(code: str) -> str | None:
        """Parse Python AST and produce a structural tree signature with identifiers anonymized."""
        try:
            tree = ast.parse(code)
        except Exception:
            return None

        class ASTNormalizer(ast.NodeTransformer):
            def visit_Name(self, node: ast.Name) -> ast.Name:
                return ast.Name(id="ID", ctx=node.ctx)

            def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
                node.name = "FUNC"
                self.generic_visit(node)
                return node

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
                node.name = "ASYNC_FUNC"
                self.generic_visit(node)
                return node

            def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
                node.name = "CLASS"
                self.generic_visit(node)
                return node

            def visit_arg(self, node: ast.arg) -> ast.arg:
                node.arg = "ARG"
                return node

        normalizer = ASTNormalizer()
        normalized_tree = normalizer.visit(tree)
        # Dump node types only, ignoring line/col attributes
        return ast.dump(normalized_tree, annotate_fields=False)

    @classmethod
    def calculate_ast_similarity(
        cls,
        source_code: str,
        reference_code: str,
    ) -> float:
        """Calculate structural AST similarity between two Python snippets with anonymized identifiers."""
        struct_source = cls._normalize_ast_to_structure(source_code)
        struct_ref = cls._normalize_ast_to_structure(reference_code)

        if not struct_source or not struct_ref:
            return 0.0

        ratio = difflib.SequenceMatcher(None, struct_source, struct_ref).ratio()
        return round(ratio, 4)

    # -------------------------------------------------------------------------
    # Comprehensive Multi-Modal Evaluation
    # -------------------------------------------------------------------------
    @classmethod
    def evaluate_similarity(
        cls,
        source_code: str,
        reference: ReferenceSource,
        language: str = "Python",
    ) -> dict[str, Any]:
        """Perform comprehensive multi-modal comparison against a specific reference source."""
        exact_score, matched_snippets = cls.calculate_exact_similarity(source_code, reference.code)
        norm_score, coverage = cls.calculate_normalized_similarity(source_code, reference.code, language)
        token_score = cls.calculate_token_similarity(source_code, reference.code, language)

        ast_score = 0.0
        if language.lower() == "python":
            ast_score = cls.calculate_ast_similarity(source_code, reference.code)

        # Composite score weighted towards structural and normalized overlap
        if language.lower() == "python" and ast_score > 0:
            composite_score = round(
                (0.20 * exact_score) + (0.35 * norm_score) + (0.20 * token_score) + (0.25 * ast_score),
                4,
            )
        else:
            composite_score = round(
                (0.25 * exact_score) + (0.45 * norm_score) + (0.30 * token_score),
                4,
            )

        # Primary matched modality
        best_modality = "normalized"
        if exact_score >= 0.8:
            best_modality = "exact"
        elif ast_score >= 0.75:
            best_modality = "ast"
        elif token_score > norm_score:
            best_modality = "token"

        return {
            "reference_id": reference.reference_id,
            "reference_name": reference.name,
            "provenance": reference.provenance,
            "license": reference.license,
            "canonical_url": reference.canonical_url,
            "skill": reference.skill,
            "similarity_score": min(1.0, max(0.0, composite_score)),
            "exact_score": exact_score,
            "normalized_score": norm_score,
            "token_score": token_score,
            "ast_score": ast_score,
            "coverage_ratio": coverage,
            "primary_modality": best_modality,
            "matched_snippets": matched_snippets,
        }

    @classmethod
    def compare_against_skill_references(
        cls,
        source_code: str,
        skill_name: str,
        language: str = "Python",
    ) -> list[dict[str, Any]]:
        """Compare code against all registered references for a specific skill."""
        references = reference_registry.get_references_for_skill(skill_name)
        if not references:
            # Check language references
            references = reference_registry.get_references_for_language(language)

        results = []
        for ref in references:
            eval_result = cls.evaluate_similarity(source_code, ref, language)
            # Only include findings if there is non-trivial similarity (> 0.15)
            if eval_result["similarity_score"] >= 0.15:
                results.append(eval_result)

        # Sort by similarity score descending
        results.sort(key=lambda r: r["similarity_score"], reverse=True)
        return results


similarity_engine = CodeSimilarityEngine()
