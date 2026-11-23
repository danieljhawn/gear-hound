import pytest

from app.services.classifier import classify_title


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Yamaha BB414 Electric Bass", "Bass"),
        ("GK MB500 bass amp", "Amps"),
        ("Korg Minilogue analog synthesizer", "Synths/Keys"),
        ("Elektron drum machine", "Synths/Keys"),
        ("Tascam Portastudio 4-track", "Recording"),
        ("Vintage MXR Phase 100 pedal", "Effects"),
        ("1960s Framus electric guitar", "Guitar"),
        ("Large ceremonial gong", "Other/Oddball"),
        ("Handmade tabla pair", "Other/Oddball"),
        ("Unknown circuit-bent sound device", "Other/Oddball"),
        ("14 inch hi-hat cymbal pair", None),
        ("Vintage Ludwig snare stand", None),
        ("Bass drum spur legs", None),
        ("Yamaha electronic drum pad", None),
        ("Bach Stradivarius trumpet", None),
        ("Conn 88H trombone with case", None),
        ("Jupiter student French horn", None),
        ("Yamaha YAS-23 saxophone", None),
        ("Full size student violin with bow", None),
        ("Old fiddle in case", None),
        ("Sousaphone for sale", None),
        ("Baritone guitar, 27 inch scale", "Guitar"),
        ("Fender Bassman amp", "Amps"),
        ("Saxony-style analog synth", "Synths/Keys"),
    ],
)
def test_classify_title_keeps_interesting_gear_and_excludes_routine_drums(
    title: str, expected: str | None
) -> None:
    assert classify_title(title) == expected
