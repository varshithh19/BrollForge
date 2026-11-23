
import re
import uuid
from typing import Any, Dict, List, Optional

from backend.app.config.settings import settings
from backend.app.core.logging import logger


SEMANTIC_METAPHOR_RULES = [
    {
        "pattern": r"\btrust\s+is\s+earned\s+slowly\b",
        "concept": "trust_building",
        "metaphor": "two professionals shaking hands, artisans carefully assembling a craft together",
        "search_query": "handshake business partnership collaboration trust",
        "reasoning": "Abstract trust concept translated into a concrete partnership scene.",
    },
    {
        "pattern": r"\b(sales|revenue|growth)\s+grew\s+(\d+%?)\b",
        "concept": "business_growth",
        "metaphor": "modern office team reviewing financial analytics",
        "search_query": "business growth analytics financial dashboard team meeting",
        "reasoning": "Business growth translated into financial analytics footage.",
    },
    {
        "pattern": r"\bcloud\s+(computing|storage|infrastructure|server|service)\b",
        "concept": "cloud_infrastructure",
        "metaphor": "modern data center server racks",
        "search_query": "data center server rack cloud computing technology",
        "reasoning": "Cloud technology disambiguated as computing infrastructure.",
    },
    {
        "pattern": r"\b(bank|loan|mortgage|banking|interest\s+rate)\b",
        "concept": "financial_institution",
        "metaphor": "modern bank branch and financial consultation",
        "search_query": "modern bank interior finance consultation office",
        "reasoning": "Financial terminology translated into banking footage.",
    },
    {
        "pattern": r"\bpython\s+(programming|code|script|developer|software|automation)\b",
        "concept": "software_development",
        "metaphor": "software engineer writing code at a computer",
        "search_query": "software engineer coding programming computer screen",
        "reasoning": "Python identified as a programming language.",
    },
    {
        "pattern": r"\b(mouse|cursor|click)\s+(device|hardware|computer)\b",
        "concept": "computer_hardware",
        "metaphor": "person using a computer mouse at a desk",
        "search_query": "computer mouse clicking desktop workspace",
        "reasoning": "Computer hardware context identified.",
    },
    {
        "pattern": r"\b(sad|tragic|loss|memorial|sorrow|crisis)\b",
        "concept": "sensitive_somber",
        "metaphor": "respectful contemplative scene with serene nature",
        "search_query": "serene quiet sunrise peaceful landscape",
        "reasoning": "Sensitive subject handled respectfully.",
    },
]


SENSITIVE_KEYWORDS = {
    "tragedy", "tragic", "died", "killed", "mourning", "grief",
    "victim", "victims", "disaster", "funeral", "war", "violence",
    "somber", "memorial", "sorrow", "crisis",
}


class MeaningSegmenter:
    """
    Creates meaningful narration scenes using Whisper word timestamps.

    Preserves sentence boundaries where possible, splits long sentences,
    and ensures gapless coverage of the narration duration.
    """

    def __init__(
        self,
        min_scene_duration: float = settings.MIN_SCENE_DURATION_SECONDS,
        max_scene_duration: float = settings.MAX_SCENE_DURATION_SECONDS,
    ):
        self.min_scene_duration = min_scene_duration
        self.max_scene_duration = max_scene_duration

    def segment_transcript(
        self,
        transcript_data: Dict[str, Any],
        user_scenes: Optional[List[Dict[str, Any]]] = None,
        avoid_rules: Optional[List[str]] = None,
        style: str = "bright, modern, real-world footage",
    ) -> List[Dict[str, Any]]:

        raw_segments = transcript_data.get("segments", [])
        total_duration = float(transcript_data.get("duration", 0.0))

        if not raw_segments:
            text = transcript_data.get("text", "Narration")
            end = max(total_duration, self.min_scene_duration)

            return [
                self._create_scene_record(
                    index=0,
                    text=text,
                    start=0.0,
                    end=end,
                    visual_hint=None,
                    avoid_rules=avoid_rules,
                    style=style,
                )
            ]

        units = self._collect_sentence_units(raw_segments)

        if not units:
            return []

        # Split sentences that exceed the configured maximum duration.
        split_units = []
        for unit in units:
            split_units.extend(self._split_long_unit(unit))

        # Merge only very short units when doing so stays within the limit.
        merged_units = []
        buffer = None

        for unit in split_units:
            if not unit["text"].strip():
                continue

            if buffer is None:
                buffer = dict(unit)
                continue

            buffer_duration = buffer["end"] - buffer["start"]
            unit_duration = unit["end"] - unit["start"]
            combined_duration = unit["end"] - buffer["start"]

            if (
                buffer_duration < self.min_scene_duration
                and combined_duration <= self.max_scene_duration
            ):
                buffer["text"] = (
                    buffer["text"].rstrip() + " " + unit["text"].lstrip()
                )
                buffer["end"] = unit["end"]
            else:
                merged_units.append(buffer)
                buffer = dict(unit)

        if buffer:
            merged_units.append(buffer)

        final_scenes = []

        for idx, unit in enumerate(merged_units):
            user_hint = None

            if user_scenes and idx < len(user_scenes):
                user_hint = user_scenes[idx].get("visual_hint")

            final_scenes.append(
                self._create_scene_record(
                    index=idx,
                    text=unit["text"],
                    start=unit["start"],
                    end=unit["end"],
                    visual_hint=user_hint,
                    avoid_rules=avoid_rules,
                    style=style,
                )
            )

        final_scenes = self._enforce_gapless_coverage(
            final_scenes,
            total_duration,
        )

        logger.info(
            "Scene segmentation completed: %s scenes, %.2fs total duration",
            len(final_scenes),
            total_duration,
        )

        return final_scenes

    def _collect_sentence_units(
        self,
        raw_segments: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        units = []
        pending_words = []

        for segment in raw_segments:
            words = segment.get("words") or []

            if not words:
                # Use sentence boundaries and estimate timing proportionally
                # when Whisper word timestamps are unavailable.
                text = segment.get("text", "").strip()
                if text:
                    units.extend(
                        self._estimate_sentence_units(
                            text,
                            float(segment["start"]),
                            float(segment["end"]),
                        )
                    )
                continue

            for word in words:
                pending_words.append(word)

                word_text = str(word.get("word", "")).strip()

                if re.search(r"[.!?;:]$", word_text):
                    units.append(self._make_word_unit(pending_words))
                    pending_words = []

        if pending_words:
            units.append(self._make_word_unit(pending_words))

        return units

    def _make_word_unit(self, words: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "text": " ".join(
                str(word.get("word", "")).strip()
                for word in words
            ).strip(),
            "start": float(words[0]["start"]),
            "end": float(words[-1]["end"]),
            "words": list(words),
        }

    def _estimate_sentence_units(
        self,
        text: str,
        start: float,
        end: float,
    ) -> List[Dict[str, Any]]:

        sentences = re.split(r"(?<=[.!?;:])\s+", text.strip())
        sentences = [sentence.strip() for sentence in sentences if sentence.strip()]

        if not sentences:
            return []

        total_words = sum(len(sentence.split()) for sentence in sentences)
        duration = max(0.0, end - start)

        units = []
        current_time = start

        for sentence in sentences:
            word_count = len(sentence.split())
            sentence_duration = duration * word_count / max(total_words, 1)
            sentence_end = current_time + sentence_duration

            units.append({
                "text": sentence,
                "start": current_time,
                "end": sentence_end,
                "words": [],
            })

            current_time = sentence_end

        return units

    def _split_long_unit(
        self,
        unit: Dict[str, Any],
    ) -> List[Dict[str, Any]]:

        duration = unit["end"] - unit["start"]

        if duration <= self.max_scene_duration:
            return [unit]

        words = unit.get("words") or []

        # Prefer real Whisper word timestamps for accurate splitting.
        if words:
            chunks = []
            current_words = []

            for word in words:
                if not current_words:
                    current_words.append(word)
                    continue

                chunk_duration = (
                    float(word["end"]) - float(current_words[0]["start"])
                )

                if chunk_duration > self.max_scene_duration:
                    chunks.append(self._make_word_unit(current_words))
                    current_words = [word]
                else:
                    current_words.append(word)

            if current_words:
                chunks.append(self._make_word_unit(current_words))

            return chunks

        # Fallback: divide text proportionally when word timestamps
        # are unavailable.
        tokens = unit["text"].split()
        if not tokens:
            return [unit]

        total_duration = unit["end"] - unit["start"]
        chunk_count = max(
            2,
            int(total_duration / self.max_scene_duration) + 1,
        )

        words_per_chunk = max(1, (len(tokens) + chunk_count - 1) // chunk_count)

        chunks = []
        current_time = unit["start"]

        for index in range(0, len(tokens), words_per_chunk):
            chunk_words = tokens[index:index + words_per_chunk]
            fraction = len(chunk_words) / len(tokens)
            chunk_duration = total_duration * fraction

            chunk_end = min(
                unit["end"],
                current_time + chunk_duration,
            )

            chunks.append({
                "text": " ".join(chunk_words),
                "start": current_time,
                "end": chunk_end,
                "words": [],
            })

            current_time = chunk_end

        return chunks

    def _create_scene_record(
        self,
        index: int,
        text: str,
        start: float,
        end: float,
        visual_hint: Optional[str],
        avoid_rules: Optional[List[str]],
        style: str,
    ) -> Dict[str, Any]:

        duration = round(max(0.1, end - start), 3)

        metaphor_match = self._match_metaphor(text)
        sensitivity = self._detect_sensitivity(text)

        if visual_hint:
            search_query = f"{visual_hint} {style}".strip()
            semantic_desc = (
                f"User directed visual hint: '{visual_hint}'. "
                f"Narration context: '{text}'"
            )
            reasoning = "Visual query guided by the user's scene hint."

        elif metaphor_match:
            search_query = f"{metaphor_match['search_query']} {style}".strip()
            semantic_desc = f"Concrete metaphor: {metaphor_match['metaphor']}."
            reasoning = metaphor_match["reasoning"]

        else:
            keywords = self._extract_key_concepts(text)
            search_query = f"{' '.join(keywords)} {style}".strip()
            semantic_desc = (
                f"Real-world scene depicting {', '.join(keywords)}."
            )
            reasoning = (
                f"Generated query from primary semantic keywords: "
                f"{', '.join(keywords)}."
            )

        return {
            "scene_id": f"scene_{index + 1}_{uuid.uuid4().hex[:6]}",
            "scene_index": index,
            "text": text,
            "start_time": round(start, 3),
            "end_time": round(end, 3),
            "duration": duration,
            "visual_hint": visual_hint,
            "semantic_description": semantic_desc,
            "search_query": search_query,
            "scene_type": "b-roll",
            "sensitivity": sensitivity,
            "avoid_rules": avoid_rules or [],
            "reasoning": reasoning,
            "selected_clip": None,
            "relevance_score": 0.0,
            "selection_reason": None,
            "warnings": [],
        }

    def _match_metaphor(self, text: str) -> Optional[Dict[str, str]]:
        lower = text.lower()

        for rule in SEMANTIC_METAPHOR_RULES:
            if re.search(rule["pattern"], lower):
                return rule

        return None

    def _detect_sensitivity(self, text: str) -> str:
        words = set(re.findall(r"\b\w+\b", text.lower()))

        if words.intersection(SENSITIVE_KEYWORDS):
            return "sensitive_respectful"

        return "standard"

    def _extract_key_concepts(self, text: str) -> List[str]:
        stop_words = {
            "a", "an", "the", "in", "on", "at", "to", "for", "of",
            "and", "or", "is", "are", "was", "were", "it", "this",
            "that", "these", "those", "i", "we", "you", "they",
            "he", "she", "with", "as", "by", "be", "from", "has",
            "have", "had", "will", "would", "can", "could", "should",
            "our", "their", "your", "its", "so", "up", "out", "if",
            "about", "into", "than", "them", "then",
        }

        tokens = re.findall(r"\b[A-Za-z0-9_-]{3,}\b", text.lower())
        concepts = [token for token in tokens if token not in stop_words]

        return concepts[:5] if concepts else [
            "modern", "business", "technology"
        ]

    def _enforce_gapless_coverage(
        self,
        scenes: List[Dict[str, Any]],
        total_duration: float,
    ) -> List[Dict[str, Any]]:

        if not scenes:
            return scenes

        scenes[0]["start_time"] = 0.0

        for index in range(1, len(scenes)):
            scenes[index]["start_time"] = scenes[index - 1]["end_time"]

        if total_duration > 0:
            scenes[-1]["end_time"] = round(total_duration, 3)

        for scene in scenes:
            scene["duration"] = round(
                scene["end_time"] - scene["start_time"],
                3,
            )

        return scenes
