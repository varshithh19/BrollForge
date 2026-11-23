
import html
import re
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.app.config.settings import settings
from backend.app.core.logging import logger
from backend.app.services.footage.models import FootageCandidate


class SemanticFootageMatcher:
    """
    Ranks footage candidates using metadata-based relevance.

    Combines:
    - TF-IDF cosine similarity
    - Keyword overlap
    - Phrase matching
    - Technical concept expansion

    Preserves strict duplicate prevention and avoid-term filtering.
    """

    CONCEPT_EXPANSIONS = {
        "software": (
            "software development programming coding developer "
            "computer application engineering"
        ),
        "software engineer": (
            "software developer programmer coding programming "
            "computer workstation"
        ),
        "programming": (
            "coding developer software engineer source code "
            "computer terminal"
        ),
        "application": (
            "app development software interface user interface "
            "computer screen"
        ),
        "cloud": (
            "cloud computing server infrastructure hosting "
            "datacenter network"
        ),
        "cloud platform": (
            "cloud computing server infrastructure datacenter "
            "network technology"
        ),
        "team collaboration": (
            "teamwork colleagues meeting discussion collaboration "
            "office people working together"
        ),
        "collaboration": (
            "teamwork colleagues meeting discussion communication "
            "office working together"
        ),
        "artificial intelligence": (
            "AI machine learning neural network automation "
            "robotics data science computer technology"
        ),
        "automation": (
            "automated process robotics artificial intelligence "
            "machine learning technology"
        ),
        "data": (
            "data analytics database information charts "
            "visualization statistics"
        ),
        "security": (
            "cybersecurity encryption privacy protection "
            "digital security network"
        ),
        "business": (
            "office workplace company professionals meeting "
            "corporate business"
        ),
        "technology": (
            "digital technology computer electronics software "
            "innovation engineering"
        ),
        "communication": (
            "video conference online meeting discussion "
            "team communication collaboration"
        ),
        "development environment": (
            "developer workstation coding computer monitor "
            "software programming office"
        ),
    }

    def __init__(
        self,
        reuse_penalty_factor: float = settings.REUSE_PENALTY_FACTOR,
        embedding_provider: str = settings.EMBEDDING_PROVIDER,
    ):
        self.reuse_penalty_factor = reuse_penalty_factor
        self.embedding_provider = embedding_provider

    @staticmethod
    def _clean_text(value: Any) -> str:
        """Convert metadata values into clean searchable text."""

        if value is None:
            return ""

        if isinstance(value, str):
            value = html.unescape(value)
            value = re.sub(r"<[^>]+>", " ", value)
            value = re.sub(r"https?://\S+", " ", value)
            return re.sub(r"\s+", " ", value).strip()

        if isinstance(value, (int, float)):
            return ""

        if isinstance(value, dict):
            parts = []
            for key, item in value.items():
                if str(key).lower() in {
                    "url",
                    "source_url",
                    "download_url",
                    "thumbnail",
                    "image",
                    "id",
                    "timestamp",
                }:
                    continue
                cleaned = SemanticFootageMatcher._clean_text(item)
                if cleaned:
                    parts.append(cleaned)
            return " ".join(parts)

        if isinstance(value, (list, tuple, set)):
            return " ".join(
                SemanticFootageMatcher._clean_text(item)
                for item in value
            )

        return ""

    @classmethod
    def _expand_query(cls, text: str) -> str:
        """Add related visual concepts without changing the original query."""

        expanded = text.lower()

        for concept, related_terms in cls.CONCEPT_EXPANSIONS.items():
            if concept in expanded:
                expanded += " " + related_terms

        return expanded

    @staticmethod
    def _tokens(text: str) -> Set[str]:
        """Extract meaningful terms for keyword comparison."""

        stop_words = {
            "the", "and", "for", "with", "that", "this", "from",
            "are", "was", "were", "has", "have", "had", "into",
            "using", "use", "also", "its", "their", "they", "them",
            "our", "you", "your", "about", "through", "while",
            "when", "where", "what", "which", "who", "how",
            "can", "will", "would", "could", "should", "been",
            "being", "not", "but", "all", "more", "than", "very",
            "work", "way",
        }

        words = re.findall(r"[a-z0-9]+", text.lower())

        return {
            word for word in words
            if len(word) > 2 and word not in stop_words
        }

    @classmethod
    def _candidate_document(cls, candidate: FootageCandidate) -> str:
        """Build a descriptive document from all useful candidate metadata."""

        raw = candidate.raw_metadata or {}

        fields = [
            candidate.attribution,
            candidate.creator,
            cls._clean_text(raw),
        ]

        # Include common metadata fields explicitly.
        # This also handles providers with different metadata schemas.
        for key in (
            "title",
            "description",
            "summary",
            "tags",
            "keywords",
            "categories",
            "subject",
            "subjects",
            "caption",
            "name",
            "genre",
            "collection",
            "artist",
        ):
            value = cls._clean_text(raw.get(key))
            if value:
                fields.append(value)

        return " ".join(fields).strip()

    @classmethod
    def _keyword_overlap(
        cls,
        target_text: str,
        candidate_text: str,
    ) -> float:
        """Calculate balanced keyword overlap."""

        target_tokens = cls._tokens(target_text)
        candidate_tokens = cls._tokens(candidate_text)

        if not target_tokens or not candidate_tokens:
            return 0.0

        intersection = target_tokens.intersection(candidate_tokens)

        precision = len(intersection) / len(candidate_tokens)
        recall = len(intersection) / len(target_tokens)

        if precision + recall == 0:
            return 0.0

        return 2 * precision * recall / (precision + recall)

    @staticmethod
    def _phrase_score(
        target_text: str,
        candidate_text: str,
    ) -> float:
        """Reward meaningful multiword phrase matches."""

        target = re.sub(r"\s+", " ", target_text.lower()).strip()
        candidate = re.sub(r"\s+", " ", candidate_text.lower()).strip()

        if not target or not candidate:
            return 0.0

        target_phrases = [
            "artificial intelligence",
            "machine learning",
            "software development",
            "software engineering",
            "cloud computing",
            "data science",
            "team collaboration",
            "computer programming",
            "digital communication",
            "cyber security",
            "source code",
            "data center",
        ]

        matched = sum(
            1 for phrase in target_phrases
            if phrase in target and phrase in candidate
        )

        return min(1.0, matched / 2.0)

    def rank_and_select(
        self,
        scene: Dict[str, Any],
        candidates: List[FootageCandidate],
        used_clip_ids: Set[str],
        avoid_terms: Optional[List[str]] = None,
    ) -> Tuple[Optional[FootageCandidate], float, str]:

        if not candidates:
            return (
                None,
                1.0,
                "No footage candidates found from configured providers.",
            )

        # Build scene description.
        ref_parts = [
            self._clean_text(scene.get("text", "")),
            self._clean_text(scene.get("search_query", "")),
            self._clean_text(scene.get("semantic_description", "")),
            self._clean_text(scene.get("visual_hint", "")),
        ]

        original_target = " ".join(part for part in ref_parts if part)
        target_text = self._expand_query(original_target)

        if not target_text.strip():
            return None, 1.0, "Scene contains no searchable description."

        # Prepare candidate descriptions.
        candidate_docs = [
            self._candidate_document(candidate)
            for candidate in candidates
        ]

        # Expand metadata vocabulary for comparison.
        expanded_candidate_docs = [
            self._expand_query(document)
            for document in candidate_docs
        ]

        all_docs = [target_text] + expanded_candidate_docs

        try:
            vectorizer = TfidfVectorizer(
                ngram_range=(1, 2),
                stop_words="english",
                max_features=10000,
                sublinear_tf=True,
            )

            tfidf_matrix = vectorizer.fit_transform(all_docs)

            similarities = cosine_similarity(
                tfidf_matrix[0:1],
                tfidf_matrix[1:],
            )[0]

        except ValueError as exc:
            logger.warning(
                f"TF-IDF could not process footage metadata: {exc}"
            )
            similarities = np.zeros(len(candidates))

        except Exception as exc:
            logger.warning(
                f"Semantic matching fallback: {exc}"
            )
            similarities = np.zeros(len(candidates))

        avoid_set = {
            term.lower().strip()
            for term in (avoid_terms or [])
            if term and term.strip()
        }

        scored_candidates = []

        for idx, candidate in enumerate(candidates):

            cid = f"{candidate.provider}:{candidate.provider_asset_id}"

            # Strict duplicate prevention.
            is_used = (
                cid in used_clip_ids
                or candidate.provider_asset_id in used_clip_ids
            )

            if is_used:
                continue

            candidate_text = candidate_docs[idx].lower()

            # Avoid prohibited content.
            violated_rule = next(
                (
                    term for term in avoid_set
                    if term in candidate_text
                ),
                None,
            )

            if violated_rule:
                logger.info(
                    f"Candidate {cid} rejected by avoid rule: "
                    f"{violated_rule}"
                )
                continue

            tfidf_score = float(similarities[idx])

            keyword_score = self._keyword_overlap(
                target_text,
                expanded_candidate_docs[idx],
            )

            phrase_score = self._phrase_score(
                target_text,
                expanded_candidate_docs[idx],
            )

            # Weighted relevance score.
            # No artificial minimum relevance boost.
            relevance = (
                0.65 * tfidf_score
                + 0.25 * keyword_score
                + 0.10 * phrase_score
            )

            relevance = max(0.0, min(1.0, relevance))

            # Map genuine relevance to a 1-5 display scale.
            normalized_score = round(
                1.0 + 4.0 * relevance,
                2,
            )

            scored_candidates.append({
                "candidate": candidate,
                "score": normalized_score,
                "relevance": relevance,
                "tfidf": tfidf_score,
                "keywords": keyword_score,
                "phrases": phrase_score,
                "cid": cid,
            })

        if not scored_candidates:
            return (
                None,
                1.0,
                "All candidates were duplicates or violated avoid filters.",
            )

        scored_candidates.sort(
            key=lambda item: item["relevance"],
            reverse=True,
        )

        best = scored_candidates[0]

        selected = best["candidate"]
        score = best["score"]

        reason = (
            f"Selected {selected.provider} asset "
            f"{selected.provider_asset_id}. "
            f"Relevance: {score}/5.0. "
            f"TF-IDF: {best['tfidf']:.3f}, "
            f"keyword overlap: {best['keywords']:.3f}, "
            f"phrase match: {best['phrases']:.3f}. "
            f"Licence metadata: {selected.licence_name}. "
            f"Passed duplicate and avoid-term checks."
        )

        logger.info(
            f"Footage match: {best['cid']} | "
            f"score={score}/5 | "
            f"raw relevance={best['relevance']:.3f}"
        )

        return selected, score, reason
