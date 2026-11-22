import pytest
from backend.app.services.footage.mock_provider import MockFootageProvider
from backend.app.services.footage.models import FootageCandidate
from backend.app.services.footage.resilient_fetcher import ResilientFootageFetcher
from backend.app.services.semantic_matching.matcher import SemanticFootageMatcher


@pytest.mark.asyncio
async def test_footage_fetcher_and_license_verification():
    fetcher = ResilientFootageFetcher(use_mock=True)
    cands, _ = await fetcher.get_candidates_for_query("business meeting", limit=3)
    assert len(cands) > 0
    assert cands[0].licence_name is not None
    assert cands[0].licence_url is not None

    # Test rejection of non-commercial license
    nc_cand = FootageCandidate(
        provider="test",
        provider_asset_id="nc_123",
        preview_url="http://test.local/p.jpg",
        download_url="http://test.local/v.mp4",
        source_url="http://test.local/page",
        licence_name="CC BY-NC 4.0 (Non-Commercial)",
        licence_url="https://creativecommons.org/licenses/by-nc/4.0/",
        attribution="Author (NC)",
        creator="Author",
        duration=10.0,
        width=1920,
        height=1080,
    )
    assert fetcher._verify_candidate_license(nc_cand) is False


def test_zero_duplicate_enforcement():
    matcher = SemanticFootageMatcher()
    scene = {"text": "Sales grew rapidly in modern software.", "search_query": "sales analytics team"}

    cand1 = FootageCandidate(
        provider="pexels",
        provider_asset_id="clip_101",
        preview_url="http://p1",
        download_url="http://d1",
        source_url="http://s1",
        licence_name="Pexels License",
        licence_url="http://lic",
        attribution="Pexels",
        creator="Creator 1",
        duration=10.0,
        width=1920,
        height=1080,
    )
    cand2 = FootageCandidate(
        provider="pexels",
        provider_asset_id="clip_102",
        preview_url="http://p2",
        download_url="http://d2",
        source_url="http://s2",
        licence_name="Pexels License",
        licence_url="http://lic",
        attribution="Pexels",
        creator="Creator 2",
        duration=10.0,
        width=1920,
        height=1080,
    )

    used_clips = set()

    # First scene selection: cand1 chosen
    chosen1, score1, _ = matcher.rank_and_select(scene, [cand1, cand2], used_clip_ids=used_clips)
    assert chosen1.provider_asset_id == "clip_101"
    used_clips.add(f"{chosen1.provider}:{chosen1.provider_asset_id}")

    # Second scene selection with same candidate pool: cand1 must be skipped, cand2 chosen
    chosen2, score2, _ = matcher.rank_and_select(scene, [cand1, cand2], used_clip_ids=used_clips)
    assert chosen2.provider_asset_id == "clip_102"
    assert chosen2.provider_asset_id != chosen1.provider_asset_id


def test_avoid_rules_enforcement():
    matcher = SemanticFootageMatcher()
    scene = {"text": "A relaxing celebration dinner.", "search_query": "dinner toast celebration"}

    cand_alcohol = FootageCandidate(
        provider="test",
        provider_asset_id="alcohol_clip",
        preview_url="http://p1",
        download_url="http://d1",
        source_url="http://s1",
        licence_name="Pexels License",
        licence_url="http://lic",
        attribution="Drinking alcohol wine champagne at bar",
        creator="Creator Alcohol",
        duration=10.0,
        width=1920,
        height=1080,
    )
    cand_safe = FootageCandidate(
        provider="test",
        provider_asset_id="safe_clip",
        preview_url="http://p2",
        download_url="http://d2",
        source_url="http://s2",
        licence_name="Pexels License",
        licence_url="http://lic",
        attribution="People dining meal celebration family dinner",
        creator="Safe Creator",
        duration=10.0,
        width=1920,
        height=1080,
    )

    # Avoid alcohol: alcohol_clip must be filtered out
    chosen, _, _ = matcher.rank_and_select(
        scene,
        [cand_alcohol, cand_safe],
        used_clip_ids=set(),
        avoid_terms=["alcohol"],
    )
    assert chosen.provider_asset_id == "safe_clip"
