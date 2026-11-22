import json
import math
import struct
import wave
from pathlib import Path

SAMPLES = [
    {
        "filename": "01_tutorial.json",
        "script": "Welcome to this step-by-step programming tutorial. Today we will explore clean code architecture and automated testing. Modular design ensures your system remains reliable and easy to maintain over time.",
        "voice": "en-IN-female",
        "category": "tutorial",
    },
    {
        "filename": "02_news_summary.json",
        "script": "In economic developments today, national trade markets reported steady quarter-over-quarter expansion. Central financial authorities announced consistent monetary policy to support sustainable enterprise growth.",
        "voice": "en-IN-female",
        "category": "news_summary",
    },
    {
        "filename": "03_product_promotion.json",
        "script": "Introducing BrollForge, the intelligent video engine designed for content teams. Create professional, license-clean B-roll videos synchronized to voiceover in seconds. Supercharge your visual storytelling today.",
        "voice": "en-US-female",
        "category": "product_promotion",
    },
    {
        "filename": "04_story.json",
        "script": "The journey began in a modest workshop with a simple vision. Day after day, artisans crafted each piece with patience and discipline. Decades later, that quiet persistence blossomed into an enduring global legacy.",
        "voice": "en-IN-female",
        "category": "story",
    },
    {
        "filename": "05_business_explainer.json",
        "script": "Modern enterprise scalability requires decoupling services and streamlining workflows. By replacing manual bottlenecks with resilient automation, organizations unlock exponential productivity gains.",
        "voice": "en-IN-male",
        "category": "business_explainer",
    },
    {
        "filename": "06_technology_explainer.json",
        "script": "Cloud computing data centers process billions of secure transactions every second. High-density server racks and optical networks form the silent backbone of the global digital economy.",
        "voice": "en-US-female",
        "category": "technology_explainer",
    },
    {
        "filename": "07_financial_education.json",
        "script": "Compound interest rewards disciplined investors over long investment horizons. Understanding asset diversification and risk management is the foundation of lasting financial independence.",
        "voice": "en-IN-male",
        "category": "financial_education",
    },
    {
        "filename": "08_abstract_narration.json",
        "script": "Trust is earned slowly, built on integrity and transparent collaboration. When partners unite behind a shared purpose, foundations strengthen and meaningful achievements endure.",
        "voice": "en-IN-female",
        "category": "abstract_narration",
    },
    {
        "filename": "09_hindi_narration.json",
        "script": "व्यापार और नवाचार की दुनिया में, विश्वास और निष्ठा सबसे महत्वपूर्ण स्तंभ हैं। सतत विकास और सहयोग से हम एक उज्ज्वल भविष्य का निर्माण करते हैं।",
        "voice": "hi-IN-female",
        "category": "multilingual_hindi",
    },
    {
        "filename": "10_longer_feature.json",
        "script": "Sales grew 40% in 2025 as international commerce embraced digital operations. The bank approved strategic expansion financing for advanced technological infrastructure. Python automation tools eliminated routine operational delays, while engineering teams monitored server performance. Trust is earned slowly through measurable results and continuous customer dedication.",
        "voice": "en-IN-female",
        "category": "longer_feature",
    },
]


def generate_audio_wav(output_path: Path, duration_seconds: float, is_silent: bool = False):
    sample_rate = 16000
    total_samples = int(duration_seconds * sample_rate)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        frames = bytearray()
        for i in range(total_samples):
            if is_silent:
                sample = 0
            else:
                t = i / sample_rate
                # Simulate speech formant frequencies (200Hz fundamental + 400Hz harmonics)
                sample = int(4000 * math.sin(2 * math.pi * 200 * t) + 2000 * math.sin(2 * math.pi * 400 * t))
            frames.extend(struct.pack("<h", sample))
        wav_file.writeframes(frames)


def main():
    root = Path(__file__).resolve().parent.parent / "sample_inputs"
    root.mkdir(parents=True, exist_ok=True)

    for item in SAMPLES:
        target = root / item["filename"]
        with open(target, "w", encoding="utf-8") as f:
            json.dump(item, f, indent=2, ensure_ascii=False)
        print(f"Created sample: {target.name}")

    # Generate audio test inputs
    generate_audio_wav(root / "sample_voiceover.wav", duration_seconds=12.0, is_silent=False)
    print("Created sample_voiceover.wav")

    # Hard case: Silent audio
    generate_audio_wav(root / "hard_case_silent.wav", duration_seconds=5.0, is_silent=True)
    print("Created hard_case_silent.wav")


if __name__ == "__main__":
    main()
