from backend.app.services.segmentation.meaning_segmenter import MeaningSegmenter


def test_meaning_segmenter_gapless_coverage():
    segmenter = MeaningSegmenter(min_scene_duration=2.0, max_scene_duration=8.0)

    # Simulated transcript segments
    mock_transcript = {
        "text": "First sentence is here. Second sentence continues immediately. Third sentence concludes the story.",
        "duration": 12.0,
        "segments": [
            {
                "id": 0,
                "start": 0.0,
                "end": 3.5,
                "text": "First sentence is here.",
                "words": [
                    {"word": "First", "start": 0.0, "end": 0.8},
                    {"word": "sentence", "start": 0.8, "end": 1.5},
                    {"word": "is", "start": 1.5, "end": 2.2},
                    {"word": "here.", "start": 2.2, "end": 3.5},
                ],
            },
            {
                "id": 1,
                "start": 3.5,
                "end": 7.5,
                "text": "Second sentence continues immediately.",
                "words": [
                    {"word": "Second", "start": 3.5, "end": 4.5},
                    {"word": "sentence", "start": 4.5, "end": 5.5},
                    {"word": "continues", "start": 5.5, "end": 6.5},
                    {"word": "immediately.", "start": 6.5, "end": 7.5},
                ],
            },
            {
                "id": 2,
                "start": 7.5,
                "end": 12.0,
                "text": "Third sentence concludes the story.",
                "words": [
                    {"word": "Third", "start": 7.5, "end": 8.5},
                    {"word": "sentence", "start": 8.5, "end": 9.5},
                    {"word": "concludes", "start": 9.5, "end": 10.5},
                    {"word": "the", "start": 10.5, "end": 11.0},
                    {"word": "story.", "start": 11.0, "end": 12.0},
                ],
            },
        ],
    }

    scenes = segmenter.segment_transcript(mock_transcript)
    assert len(scenes) >= 2

    # Check 100% gapless coverage
    assert scenes[0]["start_time"] == 0.0
    for i in range(len(scenes) - 1):
        assert scenes[i]["end_time"] == scenes[i + 1]["start_time"]
    assert scenes[-1]["end_time"] == 12.0

    # Ensure every second is covered and reasonable durations
    for sc in scenes:
        assert sc["duration"] >= 1.5
        assert sc["search_query"] is not None
        assert sc["reasoning"] is not None


def test_abstract_metaphors_and_disambiguation():
    segmenter = MeaningSegmenter()

    cases = [
        ("Trust is earned slowly across teams.", "partnership", "handshake"),
        ("Sales grew 40% in 2025 across international regions.", "business", "analytics"),
        ("Cloud computing server infrastructure powers web apps.", "data center", "server"),
        ("The bank approved the loan for our company.", "bank", "finance"),
        ("Python automation scripts streamline workflow execution.", "software", "coding"),
    ]

    for text, expected_kw1, expected_kw2 in cases:
        mock_data = {
            "text": text,
            "duration": 5.0,
            "segments": [{"id": 0, "start": 0.0, "end": 5.0, "text": text, "words": []}],
        }
        scenes = segmenter.segment_transcript(mock_data)
        assert len(scenes) >= 1
        query = scenes[0]["search_query"].lower()
        reasoning = scenes[0]["reasoning"].lower()
        assert (expected_kw1 in query or expected_kw1 in reasoning) or (expected_kw2 in query or expected_kw2 in reasoning)
