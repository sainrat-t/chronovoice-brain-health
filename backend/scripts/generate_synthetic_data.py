"""Generate the synthetic sessions of the demo personas (docs/specs/synthetic-data.md).

Inputs, all under backend/data/:
* prompts.json                          interviewer questions and follow-ups;
* synthetic/stories/<persona>.json      authored narratives, sentence by sentence;
* synthetic/generation_params.json      the designed trajectory of each persona.

Output: synthetic/sessions/<persona>/<NN>.json, one Scribe-shaped response per session.

The text comes from the authored stories. This script only (1) mixes plain and vague
sentences, (2) inserts hesitations, repetitions and cut-off words, (3) gives every
word a time and a confidence. Everything is drawn from a seeded generator: the same
inputs always give the same files. Magnitudes are demonstration parameters, not
scientific results.

Run from backend/:  uv run python -m scripts.generate_synthetic_data
"""

from __future__ import annotations

import json
import random
from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from app.demo_data import DATA_ROOT, SYNTHETIC_ROOT

PERSON = "speaker_0"
INTERVIEWER = "speaker_1"
LANGUAGE = "eng"

# Timing model, before the word durations are scaled to reach the target speech rate.
WORD_BASE_S = 0.09
WORD_PER_LETTER_S = 0.055
FILLER_S = (0.25, 0.45)
CUT_OFF_S = 0.12
GAP_IN_SENTENCE_S = (0.02, 0.09)
GAP_AFTER_COMMA_S = (0.08, 0.20)
GAP_BETWEEN_SENTENCES_S = (0.10, 0.22)
PAUSE_IN_SENTENCE_S = (0.25, 0.60)
PAUSE_BETWEEN_SENTENCES_S = (0.35, 1.00)
INTERVIEWER_WORD_S = 0.30
INTERVIEWER_GAP_S = 0.08
TURN_CHANGE_S = (0.50, 0.90)
LOGPROB_SD = 0.04


@dataclass(slots=True)
class _Word:
    text: str
    speaker: str
    kind: str = "lexical"  # lexical, filler or cut_off
    ends_sentence: bool = False
    starts_turn: bool = False
    start: float = 0.0
    end: float = 0.0
    logprob: float = 0.0


def generate_all(only: Collection[str] | None = None) -> dict[Path, str]:
    """Content of every session file, by path. Nothing is written.

    ``only`` restricts the generation to some personas (by id).
    """
    params = json.loads((SYNTHETIC_ROOT / "generation_params.json").read_text())
    bank = json.loads((DATA_ROOT / "prompts.json").read_text())
    questions = {prompt["id"]: prompt["question"] for prompt in bank["prompts"]}
    first_day = datetime.fromisoformat(params["first_session"])

    files: dict[Path, str] = {}
    for persona_id, persona in params["personas"].items():
        if only is not None and persona_id not in only:
            continue
        stories = json.loads((SYNTHETIC_ROOT / "stories" / f"{persona_id}.json").read_text())
        # Session n tells the n-th story of the file, unless "story_order" says otherwise.
        order = persona.get("story_order", range(len(stories["stories"])))
        ordered = [stories["stories"][index] for index in order]
        for number, (story, overrides) in enumerate(
            zip(ordered, persona["sessions"], strict=True), start=1
        ):
            rng = random.Random(f"{params['seed']}:{persona_id}:{number}")
            session = _generate_session(
                rng=rng,
                persona_id=persona_id,
                number=number,
                recorded_at=first_day
                + timedelta(days=params["days_between_sessions"] * (number - 1)),
                story=story,
                retellings=stories.get("anecdote_retellings", []),
                question=questions[story["prompt_id"]],
                follow_ups=bank["follow_ups"],
                base=persona["base"],
                overrides=overrides,
            )
            path = SYNTHETIC_ROOT / "sessions" / persona_id / f"{number:02d}.json"
            files[path] = _dump(session)
    return files


def _generate_session(
    *,
    rng: random.Random,
    persona_id: str,
    number: int,
    recorded_at: datetime,
    story: dict[str, Any],
    retellings: list[list[str]],
    question: str,
    follow_ups: list[str],
    base: dict[str, float],
    overrides: dict[str, Any],
) -> dict[str, Any]:
    def target(name: str) -> float:
        """Persona level, plus the session's designed shift, plus session-to-session noise."""
        value = base[name] + overrides.get(f"{name}_shift", 0.0)
        return max(0.0, rng.gauss(value, base[f"{name}_sd"]))

    speech_rate = target("speech_rate_wpm")
    fillers = target("fillers_per_100w")
    repetitions = target("repetitions_per_100w")
    cut_offs = max(0.0, overrides.get("cut_offs_per_100w", 0.0))
    vague_share = overrides.get("vague_share", 0.0)
    retelling = overrides.get("retelling")

    sentences = _pick_sentences(rng, story, vague_share)
    if retelling is not None:
        position = round(len(sentences) * 0.6)
        sentences[position:position] = retellings[retelling]
    if "keep_sentences" in overrides:
        sentences = sentences[: overrides["keep_sentences"]]

    answer = _person_words(rng, sentences, fillers, repetitions, cut_offs)
    words = _with_interviewer(answer, question, follow_ups, len(sentences))
    _set_times(rng, words, speech_rate, base)
    mean_logprob = overrides.get("mean_logprob", base["mean_logprob"])
    for word in words:
        word.logprob = round(min(0.0, rng.gauss(mean_logprob, LOGPROB_SD)), 3)

    return {
        "synthetic": True,
        "session_id": f"{persona_id}-s{number:02d}",
        "metadata": {
            "person_id": persona_id,
            "task_type": "life_story",
            "language": LANGUAGE,
            "consent": True,
            "recorded_at": recorded_at.isoformat(),
            "source": "clinician_ui",
            "context": overrides.get("context", {}),
            "prompt_id": story["prompt_id"],
            "synthetic": True,
        },
        "generation": {
            "speech_rate_wpm": round(speech_rate, 2),
            "fillers_per_100w": round(fillers, 2),
            "repetitions_per_100w": round(repetitions, 2),
            "cut_offs_per_100w": cut_offs,
            "vague_share": vague_share,
            "retelling": retelling,
            "kept_sentences": len(sentences),
            "mean_logprob": mean_logprob,
        },
        "scribe_response": {
            "language_code": LANGUAGE,
            "language_probability": 0.99,
            "audio_duration_secs": round(words[-1].end + 0.5, 3),
            "text": " ".join(word.text for word in words),
            "words": [
                {
                    "text": word.text,
                    "start": word.start,
                    "end": word.end,
                    "type": "word",
                    "speaker_id": word.speaker,
                    "logprob": word.logprob,
                }
                for word in words
            ],
        },
    }


def _pick_sentences(rng: random.Random, story: dict[str, Any], vague_share: float) -> list[str]:
    """Take each sentence in its plain or its vague wording."""
    plain: list[str] = story["sentences"]
    vague: list[str] | None = story.get("vague_sentences")
    if not vague or vague_share <= 0:
        return list(plain)
    return [v if rng.random() < vague_share else p for p, v in zip(plain, vague, strict=True)]


def _person_words(
    rng: random.Random,
    sentences: list[str],
    fillers_per_100w: float,
    repetitions_per_100w: float,
    cut_offs_per_100w: float,
) -> list[_Word]:
    """Words of the answer, with hesitations, repetitions and cut-off words inserted."""
    words: list[_Word] = []
    for sentence in sentences:
        tokens = sentence.split()
        words.extend(_Word(text=token, speaker=PERSON) for token in tokens)
        words[-1].ends_sentence = True

    count = len(words)
    # Never before the first word of a sentence: disfluencies stay inside sentences.
    inside = [i for i in range(1, count) if not words[i - 1].ends_sentence]

    def positions(rate_per_100w: float) -> set[int]:
        return set(rng.sample(inside, min(len(inside), round(rate_per_100w * count / 100))))

    filler_at = positions(fillers_per_100w)
    repeat_at = positions(repetitions_per_100w)
    cut_off_at = positions(cut_offs_per_100w)

    result: list[_Word] = []
    for i, word in enumerate(words):
        if i in filler_at:
            result.append(_Word(text=rng.choice(("um", "um", "uh")), speaker=PERSON, kind="filler"))
        if i in cut_off_at:
            result.append(_Word(text=f"{word.text[0].lower()}-", speaker=PERSON, kind="cut_off"))
        if i in repeat_at:
            # "the, the dog" and, one time in three, "it was, it was": the word is said,
            # then said again, alone or with the word before it.
            result.append(_Word(text=word.text.rstrip(",.?!") + ",", speaker=PERSON))
            if rng.random() < 1 / 3:
                result.append(_Word(text=words[i - 1].text.rstrip(",.?!"), speaker=PERSON))
        result.append(word)
    return result


def _with_interviewer(
    answer: list[_Word], question: str, follow_ups: list[str], sentence_count: int
) -> list[_Word]:
    """Put the question first and, in a long answer, a follow-up at each third."""

    def turn(text: str) -> list[_Word]:
        words = [_Word(text=token, speaker=INTERVIEWER) for token in text.split()]
        words[0].starts_turn = True
        return words

    follow_up_after = (
        {sentence_count // 3: follow_ups[0], 2 * sentence_count // 3: follow_ups[1]}
        if sentence_count >= 20
        else {}
    )
    words = turn(question)
    sentences_done = 0
    new_turn = True
    for word in answer:
        word.starts_turn = new_turn
        new_turn = False
        words.append(word)
        if word.ends_sentence:
            sentences_done += 1
            if sentences_done in follow_up_after and sentences_done < sentence_count:
                words.extend(turn(follow_up_after[sentences_done]))
                new_turn = True
    return words


def _set_times(
    rng: random.Random, words: list[_Word], speech_rate_wpm: float, base: dict[str, float]
) -> None:
    """Give every word a start and an end, so that the person speaks at the target rate."""
    durations: list[float] = []
    gaps: list[float] = []  # silence before each word
    for previous, word in zip([None, *words], words, strict=False):
        if word.speaker == INTERVIEWER:
            durations.append(INTERVIEWER_WORD_S)
        elif word.kind == "filler":
            durations.append(rng.uniform(*FILLER_S))
        elif word.kind == "cut_off":
            durations.append(CUT_OFF_S)
        else:
            letters = sum(char.isalnum() for char in word.text)
            durations.append(WORD_BASE_S + WORD_PER_LETTER_S * letters)

        if previous is None:
            gaps.append(0.0)
        elif word.starts_turn:
            gaps.append(rng.uniform(*TURN_CHANGE_S))
        elif word.speaker == INTERVIEWER:
            gaps.append(INTERVIEWER_GAP_S)
        elif previous.ends_sentence:
            pause = rng.random() < base["pause_between_probability"]
            gaps.append(
                rng.uniform(*(PAUSE_BETWEEN_SENTENCES_S if pause else GAP_BETWEEN_SENTENCES_S))
            )
        elif rng.random() < base["pause_within_probability"]:
            gaps.append(rng.uniform(*PAUSE_IN_SENTENCE_S))
        elif previous.text.endswith(","):
            gaps.append(rng.uniform(*GAP_AFTER_COMMA_S))
        else:
            gaps.append(rng.uniform(*GAP_IN_SENTENCE_S))

    # Speaking time = word durations + silences inside the person's turns. Scale the
    # durations so that lexical words / speaking time reaches the target rate.
    person = [i for i, word in enumerate(words) if word.speaker == PERSON]
    lexical = sum(words[i].kind == "lexical" for i in person)
    spoken = sum(durations[i] for i in person)
    silence = sum(gaps[i] for i in person if not words[i].starts_turn)
    scale = max(0.4, (lexical / speech_rate_wpm * 60 - silence) / spoken)

    clock = 0.0
    for i, word in enumerate(words):
        clock += gaps[i]
        word.start = round(clock, 3)
        clock += durations[i] * (scale if word.speaker == PERSON else 1.0)
        word.end = round(clock, 3)


def _dump(session: dict[str, Any]) -> str:
    """JSON with one word per line, so that files stay readable and diffs small."""
    scribe = dict(session["scribe_response"])
    words = scribe.pop("words")
    head = {key: value for key, value in session.items() if key != "scribe_response"}
    lines = [f" {json.dumps(key)}: {json.dumps(value)}," for key, value in head.items()]
    lines.append(' "scribe_response": {')
    lines.extend(f"  {json.dumps(key)}: {json.dumps(value)}," for key, value in scribe.items())
    lines.append('  "words": [')
    lines.extend(
        f"   {json.dumps(word)}{',' if i < len(words) - 1 else ''}" for i, word in enumerate(words)
    )
    lines.append("  ]")
    lines.append(" }")
    return "{\n" + "\n".join(lines) + "\n}\n"


def main() -> None:
    files = generate_all()
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    print(f"{len(files)} session files written under {SYNTHETIC_ROOT / 'sessions'}")


if __name__ == "__main__":
    main()
