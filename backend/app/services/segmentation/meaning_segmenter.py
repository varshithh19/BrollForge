import re
import uuid
from typing import Any, Dict, List, Optional
from backend.app.config.settings import settings
from backend.app.core.logging import logger

# Knowledge base of domain disambiguations & abstract metaphors
SEMANTIC_METAPHOR_RULES = [
    {
        "pattern": r"\btrust\s+is\s+earned\s+slowly\b",
        "concept": "trust_building",
        "metaphor": "two professionals shaking hands, artisans carefully assembling a craft together, solid foundation",
        "search_query": "handshake business partnership collaboration trust",
        "reasoning": "Abstract statement 'trust is earned slowly' translated into concrete partnership and careful joint craftsmanship metaphor.",
    },
    {
        "pattern": r"\b(sales|revenue|growth)\s+grew\s+(\d+%?)\b",
        "concept": "business_growth",
        "metaphor": "modern office team reviewing positive financial analytics dashboard",
        "search_query": "business growth analytics financial dashboard team meeting",
        "reasoning": "Statistical statement translated to real-world corporate analytics and strategic team discussion.",
    },
    {
        "pattern": r"\bcloud\s+(computing|storage|infrastructure|server|service)\b",
        "concept": "cloud_infrastructure",
        "metaphor": "modern data center server racks with flashing blue LED lights",
        "search_query": "data center server rack cloud computing technology",
        "reasoning": "Disambiguated 'cloud' in tech context to modern data center server hardware rather than weather sky.",
    },
    {
        "pattern": r"\b(bank|loan|mortgage|banking|interest\s+rate)\b",
        "concept": "financial_institution",
        "metaphor": "modern bank branch interior, financial advisor discussing with client",
        "search_query": "modern bank interior finance consultation office",
        "reasoning": "Disambiguated 'bank' into financial institution rather than riverbank or shoreline.",
    },
    {
        "pattern": r"\bpython\s+(programming|code|script|developer|software|automation)\b",
        "concept": "software_development",
        "metaphor": "software engineer typing clean code on dual monitor setup in modern office",
        "search_query": "software engineer coding programming computer screen",
        "reasoning": "Disambiguated 'python' to programming language and software automation rather than reptile.",
    },
    {
        "pattern": r"\b(mouse|cursor|click)\s+(device|hardware|computer)\b",
        "concept": "computer_hardware",
        "metaphor": "person holding ergonomic computer mouse clicking on modern desktop desk",
        "search_query": "computer mouse clicking desktop workspace",
        "reasoning": "Disambiguated computer mouse hardware rather than animal rodent.",
    },
    {
        "pattern": r"\b(sad|tragic|loss|memorial|sorrow|crisis)\b",
        "concept": "sensitive_somber",
        "metaphor": "respectful contemplative shot, serene nature, quiet city sunrise, dignified atmosphere",
        "search_query": "serene quiet sunrise peaceful landscape dignified calm",
        "reasoning": "Sensitive topic handled respectfully with calm, dignified atmosphere without sensationalism.",
    },
]

# Sensitive classifications
SENSITIVE_KEYWORDS = {
    "tragedy", "tragic", "died", "killed", "mourning", "grief", "victim", "victims",
    "disaster", "funeral", "war", "violence", "somber", "memorial", "sorrow", "crisis"
}


class MeaningSegmenter:
    """
    Splits narration into meaningful, voice-synchronized scenes based on sentences,
    phrases, conceptual semantics, and timing boundaries.
    Ensures 100% gapless coverage of the narration timeline.
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
        """
        Takes Whisper transcript segments (with start, end, text, words) and optional
        user scene hints to produce a complete list of meaning-based scene definitions.
        """
        raw_segments = transcript_data.get("segments", [])
        total_duration = float(transcript_data.get("duration", 0.0))

        if not raw_segments:
            # Fallback single scene if no segment breakdown
            return [self._create_scene_record(
                index=0,
                text=transcript_data.get("text", "Narration"),
                start=0.0,
                end=max(total_duration, self.min_scene_duration),
                visual_hint=None,
                avoid_rules=avoid_rules,
                style=style,
            )]

        # Step 1: Collect sentence/phrase units with accurate timestamps
        units = []
        for seg in raw_segments:
            seg_text = seg["text"].strip()
            words = seg.get("words", [])

            if not words:
                # Approximate words if not provided
                units.append({
                    "text": seg_text,
                    "start": seg["start"],
                    "end": seg["end"],
                })
                continue

            # Group words by sentence boundaries (. ? ! ;)
            curr_words = []
            curr_start = words[0]["start"]

            for w in words:
                curr_words.append(w["word"])
                w_str = w["word"].strip()
                # Check for punctuation delimiter
                if any(w_str.endswith(p) for p in [".", "!", "?", ";", ":"]):
                    units.append({
                        "text": " ".join(curr_words).strip(),
                        "start": curr_start,
                        "end": w["end"],
                    })
                    curr_words = []
                    curr_start = w["end"]

            if curr_words:
                units.append({
                    "text": " ".join(curr_words).strip(),
                    "start": curr_start,
                    "end": words[-1]["end"],
                })

        # Step 2: Merge units that are too short (< min_scene_duration) and split those too long (> max_scene_duration)
        merged_scenes = []
        buffer = None

        for u in units:
            u_text = u["text"].strip()
            if not u_text:
                continue

            if buffer is None:
                buffer = dict(u)
            else:
                curr_dur = buffer["end"] - buffer["start"]
                # If current buffer is under minimum duration, merge
                if curr_dur < self.min_scene_duration or (curr_dur + (u["end"] - u["start"])) <= self.max_scene_duration:
                    buffer["text"] += " " + u_text
                    buffer["end"] = u["end"]
                else:
                    merged_scenes.append(buffer)
                    buffer = dict(u)

        if buffer:
            merged_scenes.append(buffer)

        # Step 3: Handle user visual hints mapping if supplied (IncuBrix structured scene list)
        final_scenes = []
        for idx, sc in enumerate(merged_scenes):
            user_hint = None
            if user_scenes and idx < len(user_scenes):
                user_hint = user_scenes[idx].get("visual_hint")

            scene_rec = self._create_scene_record(
                index=idx,
                text=sc["text"],
                start=sc["start"],
                end=sc["end"],
                visual_hint=user_hint,
                avoid_rules=avoid_rules,
                style=style,
            )
            final_scenes.append(scene_rec)

        # Step 4: Ensure 100% gapless coverage from 0.0 to total_duration
        final_scenes = self._enforce_gapless_coverage(final_scenes, total_duration)

        return final_scenes

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
        dur = round(max(0.1, end - start), 3)

        # Conceptual and semantic metaphor analysis
        metaphor_match = self._match_metaphor(text)
        sensitivity = self._detect_sensitivity(text)

        if user_hint := visual_hint:
            search_query = f"{user_hint} {style}".strip()
            semantic_desc = f"User directed visual hint: '{user_hint}'. Narration context: '{text}'"
            reasoning = "Query guided directly by user visual hint while honoring narrative timing."
        elif metaphor_match:
            search_query = f"{metaphor_match['search_query']} {style}".strip()
            semantic_desc = f"Concrete metaphor: {metaphor_match['metaphor']}."
            reasoning = metaphor_match["reasoning"]
        else:
            # Extract key concept nouns/verbs
            keywords = self._extract_key_concepts(text)
            search_query = f"{' '.join(keywords)} {style}".strip()
            semantic_desc = f"Real-world scene depicting {', '.join(keywords)}."
            reasoning = f"Generated query from primary semantic keywords: {', '.join(keywords)}."

        return {
            "scene_id": f"scene_{index + 1}_{uuid.uuid4().hex[:6]}",
            "scene_index": index,
            "text": text,
            "start_time": round(start, 3),
            "end_time": round(end, 3),
            "duration": dur,
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
        lower = text.lower()
        words = set(re.findall(r"\b\w+\b", lower))
        if words.intersection(SENSITIVE_KEYWORDS):
            return "sensitive_respectful"
        return "standard"

    def _extract_key_concepts(self, text: str) -> List[str]:
        # Filter stop words and punctuation
        stop_words = {
            "a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "or", "is", "are", "was", "were",
            "it", "this", "that", "these", "those", "i", "we", "you", "they", "he", "she", "with", "as",
            "by", "be", "from", "has", "have", "had", "will", "would", "can", "could", "should", "our",
            "their", "your", "its", "so", "up", "out", "if", "about", "into", "than", "them", "then"
        }
        tokens = re.findall(r"\b[A-Za-z0-9_-]{3,}\b", text.lower())
        concepts = [t for t in tokens if t not in stop_words]
        return concepts[:4] if concepts else ["modern", "business", "technology"]

    def _enforce_gapless_coverage(self, scenes: List[Dict[str, Any]], total_duration: float) -> List[Dict[str, Any]]:
        if not scenes:
            return scenes

        # Fix start time of first scene to 0.0
        scenes[0]["start_time"] = 0.0

        for i in range(len(scenes) - 1):
            curr_scene = scenes[i]
            next_scene = scenes[i + 1]

            # Eliminate gaps or overlaps
            next_scene["start_time"] = curr_scene["end_time"]
            curr_scene["duration"] = round(curr_scene["end_time"] - curr_scene["start_time"], 3)

        # Fix end time of last scene to cover full narration
        last = scenes[-1]
        if total_duration > 0 and last["end_time"] < total_duration:
            last["end_time"] = round(total_duration, 3)
        last["duration"] = round(last["end_time"] - last["start_time"], 3)

        return scenes
