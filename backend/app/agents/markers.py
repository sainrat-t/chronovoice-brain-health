"""Step 1 of the pipeline: language markers of one session.

Pure computation, no LLM. Every marker is defined in docs/specs/pipeline.md (step 1)
and described, with its sources, in MARKER_SPECS. All markers are computed on the
lexical words of the tracked speaker; fillers and cut-off words only count in the
maze index, so that hesitating more does not also lower the semantic markers
(design choice, not backed by a study).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise
from statistics import fmean

from app.agents.segmentation import Turn, WordKind, segment_target_speech, speaking_time_s
from app.language.base import CONTENT_POS, NOUN_POS, LanguageAdapter, Pos
from app.schemas import (
    DeclineDirection,
    MarkerFamily,
    MarkerId,
    MarkerSpec,
    MarkerValue,
    SessionMetrics,
    SessionTranscript,
    StudyRef,
)

# ---------------------------------------------------------------------------
# Thresholds and their sources
# ---------------------------------------------------------------------------

PAUSE_THRESHOLD_S = 0.25
"""Shortest silence counted as a pause: Pistono et al. 2016 (study note 06), who take
the 250 ms threshold from Goldman-Eisler."""

MATTR_WINDOW = 50
"""Window of the moving-average type-token ratio. Method: Covington MA, McFall JD
(2010), J Quant Linguist 17(2):94-100, DOI 10.1080/09296171003643098 (checked on
Crossref). The value 50 comes from the initial project brief, not from a study."""

MATTR_MIN_WORDS = 150
"""Shortest sample on which lexical diversity is reported: minimum cited by
Mueller et al. 2018 (study note 08)."""

MAX_REPEATED_PHRASE_WORDS = 3
"""Longest phrase checked for an immediate repetition ("it was, it was").
Design choice, not backed by a study."""

_TIMESTAMP_DECIMALS = 3  # Scribe timestamps are given to the millisecond.

# ---------------------------------------------------------------------------
# Marker catalogue
# ---------------------------------------------------------------------------


def _spec(
    marker: MarkerId,
    family: MarkerFamily,
    direction: DeclineDirection,
    in_change_index: bool,
    definition: str,
    *sources: StudyRef,
) -> MarkerSpec:
    return MarkerSpec(
        marker=marker,
        family=family,
        decline_direction=direction,
        in_change_index=in_change_index,
        definition=definition,
        sources=sources,
    )


MARKER_SPECS: dict[MarkerId, MarkerSpec] = {
    spec.marker: spec
    for spec in (
        _spec(
            MarkerId.PRONOUN_INDEX,
            MarkerFamily.SEMANTIC,
            DeclineDirection.INCREASE,
            True,
            "Pronouns divided by pronouns plus nouns.",
            StudyRef.MUELLER_2018,
            StudyRef.ROBIN_2023,
        ),
        _spec(
            MarkerId.NOUN_RATIO,
            MarkerFamily.SEMANTIC,
            DeclineDirection.DECREASE,
            True,
            "Share of nouns among the words spoken.",
            StudyRef.ROBIN_2023,
            StudyRef.MUELLER_2018,
        ),
        _spec(
            MarkerId.MEAN_WORD_FREQUENCY,
            MarkerFamily.SEMANTIC,
            DeclineDirection.INCREASE,
            True,
            "Average frequency of content words on the Zipf scale: "
            "higher means a more common vocabulary.",
            StudyRef.ROBIN_2023,
        ),
        _spec(
            MarkerId.MEAN_WORD_LENGTH,
            MarkerFamily.SEMANTIC,
            DeclineDirection.DECREASE,
            True,
            "Average number of letters per word.",
            StudyRef.ROBIN_2023,
        ),
        _spec(
            MarkerId.MAZE_INDEX,
            MarkerFamily.FLUENCY,
            DeclineDirection.INCREASE,
            True,
            "Hesitations, immediate repetitions and cut-off words per utterance.",
            StudyRef.MUELLER_2018,
        ),
        _spec(
            MarkerId.SPEECH_RATE_WPM,
            MarkerFamily.FLUENCY,
            DeclineDirection.DECREASE,
            True,
            "Words per minute of speaking time.",
            StudyRef.MUELLER_2018,
        ),
        _spec(
            MarkerId.PAUSES_BETWEEN_PER100W,
            MarkerFamily.FLUENCY,
            DeclineDirection.UNCERTAIN,
            False,
            "Silences of 250 ms or more between two utterances, per 100 words.",
            StudyRef.PISTONO_2016,
        ),
        _spec(
            MarkerId.PAUSES_WITHIN_PER100W,
            MarkerFamily.FLUENCY,
            DeclineDirection.UNCERTAIN,
            False,
            "Silences of 250 ms or more inside an utterance, per 100 words.",
            StudyRef.PISTONO_2016,
        ),
        _spec(
            MarkerId.MATTR_50,
            MarkerFamily.LEXICAL,
            DeclineDirection.DECREASE,
            False,
            "Lexical diversity: share of distinct words, averaged over windows of 50 words.",
            StudyRef.GARRARD_2005,
            StudyRef.MUELLER_2018,
        ),
    )
}

# ---------------------------------------------------------------------------
# Inputs of the marker functions
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LexicalWord:
    """A lexical word of the tracked speaker, with its language analysis."""

    form: str
    pos: frozenset[Pos]
    zipf_frequency: float | None


@dataclass(frozen=True, slots=True)
class Pause:
    start_s: float
    duration_s: float
    between_utterances: bool
    """True when the word before the pause ends an utterance."""


def analyse_lexical_words(
    turns: Sequence[Turn], adapter: LanguageAdapter
) -> tuple[LexicalWord, ...]:
    """Tag the lexical words of every utterance with the language adapter."""
    words: list[LexicalWord] = []
    for turn in turns:
        for utterance in turn.utterances:
            lexical = utterance.lexical_words
            if not lexical:
                continue
            analyses = adapter.analyse_utterance([word.raw for word in lexical])
            words.extend(
                LexicalWord(
                    form=word.form, pos=analysis.pos, zipf_frequency=analysis.zipf_frequency
                )
                for word, analysis in zip(lexical, analyses, strict=True)
            )
    return tuple(words)


# ---------------------------------------------------------------------------
# Semantic markers
# ---------------------------------------------------------------------------


def pronoun_index(words: Sequence[LexicalWord]) -> MarkerValue:
    """Pronouns / (nouns + pronouns), definition of Mueller et al. 2018 (study note 08)."""
    pronouns = sum(Pos.PRON in word.pos for word in words)
    nouns = sum(not NOUN_POS.isdisjoint(word.pos) for word in words)
    return _ratio(MarkerId.PRONOUN_INDEX, pronouns, pronouns + nouns)


def noun_ratio(words: Sequence[LexicalWord]) -> MarkerValue:
    """Nouns / lexical words (Robin et al. 2023, study note 09)."""
    nouns = sum(not NOUN_POS.isdisjoint(word.pos) for word in words)
    return _ratio(MarkerId.NOUN_RATIO, nouns, len(words))


def mean_word_frequency(words: Sequence[LexicalWord]) -> MarkerValue:
    """Mean Zipf frequency of the content words found in the frequency list.

    Marker of Robin et al. 2023 (study note 09). Restricting it to content words is a
    design choice to confirm when reading that study.
    """
    frequencies = [
        word.zipf_frequency
        for word in words
        if word.zipf_frequency is not None and not CONTENT_POS.isdisjoint(word.pos)
    ]
    return MarkerValue(
        marker=MarkerId.MEAN_WORD_FREQUENCY,
        value=fmean(frequencies) if frequencies else None,
        n_units=len(frequencies),
    )


def mean_word_length(words: Sequence[LexicalWord]) -> MarkerValue:
    """Mean number of letters (or digits) per lexical word (Robin et al. 2023, note 09)."""
    letters = sum(char.isalnum() for word in words for char in word.form)
    return _ratio(MarkerId.MEAN_WORD_LENGTH, letters, len(words))


# ---------------------------------------------------------------------------
# Lexical diversity
# ---------------------------------------------------------------------------


def mattr(forms: Sequence[str], *, window: int = MATTR_WINDOW) -> float | None:
    """Moving-average type-token ratio (Covington & McFall 2010).

    Mean, over every window of ``window`` consecutive words, of distinct words / window.
    None when the text is shorter than one window.
    """
    if window < 1:
        raise ValueError("window must be at least 1")
    if len(forms) < window:
        return None
    return fmean(
        len(set(forms[start : start + window])) / window for start in range(len(forms) - window + 1)
    )


def mattr_marker(words: Sequence[LexicalWord]) -> MarkerValue:
    """MATTR over windows of 50 words, reported only from MATTR_MIN_WORDS words."""
    forms = [word.form for word in words]
    value = mattr(forms) if len(forms) >= MATTR_MIN_WORDS else None
    return MarkerValue(marker=MarkerId.MATTR_50, value=value, n_units=len(forms))


# ---------------------------------------------------------------------------
# Fluency markers
# ---------------------------------------------------------------------------


def count_immediate_repetitions(forms: Sequence[str]) -> int:
    """Count words or short phrases said twice in a row ("the the", "it was it was").

    Each repeated unit counts once: "no no no" holds two repetitions.
    """
    forms = tuple(forms)
    count = 0
    position = 1
    while position < len(forms):
        for size in range(1, MAX_REPEATED_PHRASE_WORDS + 1):
            repeated = forms[position : position + size]
            if position >= size and repeated == forms[position - size : position]:
                count += 1
                position += size
                break
        else:
            position += 1
    return count


def maze_index(turns: Sequence[Turn]) -> MarkerValue:
    """(Fillers + immediate repetitions + cut-off words) / utterances.

    After the maze index of Mueller et al. 2018 (study note 08). Revisions
    ("I went, we went") belong to their index but are not detected here.
    An utterance counts only if it holds at least one lexical word.
    """
    mazes = 0
    utterances = 0
    for turn in turns:
        for utterance in turn.utterances:
            lexical_forms = [word.form for word in utterance.lexical_words]
            utterances += bool(lexical_forms)
            mazes += count_immediate_repetitions(lexical_forms)
            mazes += sum(word.kind is not WordKind.LEXICAL for word in utterance.words)
    return _ratio(MarkerId.MAZE_INDEX, mazes, utterances)


def speech_rate_wpm(turns: Sequence[Turn], lexical_word_count: int) -> MarkerValue:
    """Lexical words per minute of speaking time (Mueller et al. 2018, study note 08)."""
    minutes = speaking_time_s(turns) / 60
    return MarkerValue(
        marker=MarkerId.SPEECH_RATE_WPM,
        value=lexical_word_count / minutes if minutes > 0 else None,
        n_units=lexical_word_count,
    )


def find_pauses(
    turns: Sequence[Turn], *, threshold_s: float = PAUSE_THRESHOLD_S
) -> tuple[Pause, ...]:
    """Silences of at least ``threshold_s`` between two consecutive words of a turn.

    Definition of Pistono et al. 2016 (study note 06). A gap holding a non-speech
    sound (laugh, cough) is not a silence and is skipped.
    """
    pauses: list[Pause] = []
    for turn in turns:
        for previous, word in pairwise(turn.words):
            if word.after_audio_event:
                continue
            gap = round(word.start_s - previous.end_s, _TIMESTAMP_DECIMALS)
            if gap >= threshold_s:
                pauses.append(
                    Pause(
                        start_s=previous.end_s,
                        duration_s=gap,
                        between_utterances=previous.ends_utterance,
                    )
                )
    return tuple(pauses)


def pause_rates(turns: Sequence[Turn], lexical_word_count: int) -> tuple[MarkerValue, MarkerValue]:
    """Pauses between and within utterances, per 100 lexical words."""
    pauses = find_pauses(turns)
    between = sum(pause.between_utterances for pause in pauses)
    return (
        _per_100_words(MarkerId.PAUSES_BETWEEN_PER100W, between, lexical_word_count),
        _per_100_words(MarkerId.PAUSES_WITHIN_PER100W, len(pauses) - between, lexical_word_count),
    )


# ---------------------------------------------------------------------------
# Step 1 entry point
# ---------------------------------------------------------------------------


def compute_session_metrics(
    transcript: SessionTranscript, adapter: LanguageAdapter
) -> SessionMetrics:
    """Compute every marker of one session from its transcript."""
    if transcript.language != adapter.language:
        raise ValueError(
            f"transcript language {transcript.language!r} does not match "
            f"adapter language {adapter.language!r}"
        )

    turns = segment_target_speech(transcript, adapter)
    words = analyse_lexical_words(turns, adapter)
    pauses_between, pauses_within = pause_rates(turns, len(words))

    return SessionMetrics(
        session_id=transcript.session_id,
        person_id=transcript.person_id,
        synthetic=transcript.synthetic,
        markers=(
            pronoun_index(words),
            noun_ratio(words),
            mean_word_frequency(words),
            mean_word_length(words),
            maze_index(turns),
            speech_rate_wpm(turns, len(words)),
            pauses_between,
            pauses_within,
            mattr_marker(words),
        ),
    )


def _ratio(marker: MarkerId, numerator: int, denominator: int) -> MarkerValue:
    return MarkerValue(
        marker=marker,
        value=numerator / denominator if denominator else None,
        n_units=denominator,
    )


def _per_100_words(marker: MarkerId, count: int, word_count: int) -> MarkerValue:
    return MarkerValue(
        marker=marker,
        value=100 * count / word_count if word_count else None,
        n_units=word_count,
    )
