import re

ALLOW_ODDBALL = ("gong", "tabla")
ALLOW_SYNTH = ("drum machine", "groovebox", "sampler")
EXCLUDED_INSTRUMENTS = (
    "baritone horn",
    "baritone sax",
    "bass trombone",
    "brass",
    "bugle",
    "cornet",
    "euphonium",
    "fiddle",
    "flugelhorn",
    "french horn",
    "mellophone",
    "sax",
    "saxophone",
    "sousaphone",
    "trombone",
    "trumpet",
    "tuba",
    "violin",
)
CONVENTIONAL_DRUMS = (
    "bass drum",
    "cymbal",
    "drum kit",
    "drum pad",
    "drum seat",
    "drum throne",
    "floor tom",
    "hi hat",
    "hihat",
    "snare",
    "tom drum",
)

CATEGORY_TERMS = (
    ("Bass", ("bass guitar", "electric bass")),
    (
        "Synths/Keys",
        ("synth", "keyboard", "midi", "drum machine", "groovebox", "sampler", "sequencer"),
    ),
    ("Effects", ("pedal", "fuzz", "overdrive", "phaser", "chorus", "delay", "reverb")),
    ("Recording", ("portastudio", "audio interface", "multitrack", "preamp", "microphone")),
    ("Amps", ("amplifier", " amp", "speaker cabinet")),
    ("Guitar", ("guitar", "baritone")),
)


def _contains_phrase(text: str, phrase: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", text) is not None


def classify_title(title: str) -> str | None:
    normalized = re.sub(r"[^a-z0-9]+", " ", title.casefold()).strip()
    padded = f" {normalized} "

    if any(_contains_phrase(normalized, term) for term in EXCLUDED_INSTRUMENTS):
        return None
    if any(term in normalized for term in ALLOW_SYNTH):
        return "Synths/Keys"
    if any(term in normalized for term in ALLOW_ODDBALL):
        return "Other/Oddball"
    if any(term in normalized for term in CONVENTIONAL_DRUMS):
        return None

    for category, terms in CATEGORY_TERMS:
        if any(term in padded for term in terms):
            return category

    return "Other/Oddball"
