"""Step 2 of the pipeline: the narrative analyst (LLM, experimental).

Splits a life story into episodes and spots anecdotes that are told again, within the
session or from an earlier one (Cook et al. 2009, docs/discovery/candidates.md). The
result is experimental: it is shown apart and never enters the change index.

The model's answer is untrusted input. Whatever cannot be checked against the
transcript or against earlier sessions is dropped (docs/specs/pipeline.md, step 2).
"""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from enum import StrEnum

from pydantic import BaseModel

from app.agents.passages import SpokenText
from app.agents.segmentation import Utterance, segment_target_speech
from app.language.base import LanguageAdapter
from app.llm import LLMClient, LLMError
from app.schemas import (
    Episode,
    LifePeriod,
    NarrativeAnalysis,
    Repetition,
    RepetitionScope,
    SessionTranscript,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You read transcripts of older adults telling stories from their own lives. Each \
session is one answer, spoken aloud, to an interviewer's question. Your reading feeds \
a tool that follows how a person tells their stories from one session to the next.

You have two jobs.

1. Split the session into episodes. An episode is one remembered event or scene, told \
over one or several utterances. Give each episode a short id (e1, e2, ...), a \
one-sentence summary in your own words, the period of life it belongs to, the people, \
places and time references the person mentions, and the indices of the utterances \
that tell it. Use only the indices shown in the transcript.

2. Find anecdotes that are told again. A repetition is the same specific event told \
once more: the same occasion, with the same people, in the same place. Episodes that \
only share a theme, a person, a place or a habit are not repetitions; neither is a \
routine or a place described again, nor a passing mention of the person once telling \
a story to someone else. Compare each \
episode of this session with the earlier episodes of this session and with the \
episodes of earlier sessions listed under previous_sessions. For each candidate give:
- episode_id: the episode of this session in which the event is told again.
- retold_from: where it was told first, copied exactly from what you were given: \
either a reference from previous_sessions, as written there between square brackets, \
or the id of an earlier episode of this session. Never the episode itself.
- rationale: one sentence comparing the two tellings.
- relation: same_event when both tell the same specific event; related_theme when \
they only share a theme, a person, a place or a habit. Only same_event is kept, so \
choose related_theme whenever you are not sure.
- acknowledgement_quote: the person's exact words when they tell their listener that \
they have told this before (for example "as I told you last time"). Give null when \
they do not say so, which is the usual case: retelling a story is not saying that one \
retells it.
- quoted_passages: one or two short passages of this session, a few words to one \
sentence each, in which the event is told again. Copy the words exactly from the \
transcript, hesitations included and without the number in brackets: a passage that \
is not in the transcript is discarded.

Most sessions contain no repetition at all; an empty list is the usual answer. Report \
only what the transcripts show. Do not comment on the person's memory or health."""


_UTTERANCE_LABEL = re.compile(r"^\s*\[\d+\]\s*")
"""The number shown before each utterance, which models sometimes copy with a quote."""


class Relation(StrEnum):
    """What two episodes have in common, as judged by the model."""

    SAME_EVENT = "same_event"
    RELATED_THEME = "related_theme"
    """A shared theme, person, place or habit: not a repetition. Asking for it gives
    the model somewhere to put its doubts (first real trial, 2026-11-14)."""


class EpisodeDraft(BaseModel):
    episode_id: str
    summary: str
    life_period: LifePeriod
    people: list[str]
    places: list[str]
    time_references: list[str]
    utterance_indices: list[int]


class RepetitionDraft(BaseModel):
    episode_id: str
    retold_from: str
    rationale: str
    relation: Relation
    acknowledgement_quote: str | None
    quoted_passages: list[str]


class NarrativeDraft(BaseModel):
    """What the model is asked to return, before any check."""

    episodes: list[EpisodeDraft]
    repetitions: list[RepetitionDraft]


def analyse_narrative(
    transcript: SessionTranscript,
    previous: Sequence[NarrativeAnalysis],
    llm: LLMClient,
    adapter: LanguageAdapter,
) -> NarrativeAnalysis | None:
    """Analyse one session, given the analyses of the person's earlier sessions.

    Returns None when there is nothing to analyse or the model is unavailable: the
    step is experimental, so the rest of the pipeline goes on without it.
    """
    utterances = [u for turn in segment_target_speech(transcript, adapter) for u in turn.utterances]
    if not utterances:
        return None
    try:
        reply = llm.generate(
            system=SYSTEM_PROMPT,
            user=build_prompt(transcript.session_id, utterances, previous),
            output=NarrativeDraft,
        )
    except LLMError as error:
        logger.warning("narrative analysis skipped for %s: %s", transcript.session_id, error)
        return None
    return check_draft(reply.output, transcript, utterances, previous, reply.model_id)


def build_prompt(
    session_id: str, utterances: Sequence[Utterance], previous: Sequence[NarrativeAnalysis]
) -> str:
    """The earlier episodes, then the numbered utterances of this session."""
    lines = ["<previous_sessions>"]
    for analysis in previous:
        lines.append(f'<session id="{analysis.session_id}">')
        lines.extend(
            f"[{_reference(analysis.session_id, e.episode_id)}] {e.summary}"
            for e in analysis.episodes
        )
        lines.append("</session>")
    lines.append("</previous_sessions>")
    lines.append(f'<transcript session_id="{session_id}">')
    lines.extend(f"[{utterance.index}] {utterance.text}" for utterance in utterances)
    lines.append("</transcript>")
    return "\n".join(lines)


def check_draft(
    draft: NarrativeDraft,
    transcript: SessionTranscript,
    utterances: Sequence[Utterance],
    previous: Sequence[NarrativeAnalysis],
    model_id: str,
) -> NarrativeAnalysis:
    """Keep only what can be verified against the transcript and the earlier sessions."""
    known_indices = {utterance.index for utterance in utterances}
    # Episodes are renamed e1, e2, ... in the model's order: models sometimes invent
    # other id formats, such as the references of earlier sessions.
    renamed: dict[str, str] = {}
    episodes: dict[str, Episode] = {}

    def own(reference: str) -> str:
        """An id of this session as the model gave it, with or without the session in front."""
        return _bare(reference).removeprefix(f"{transcript.session_id}/")

    for item in draft.episodes:
        indices = tuple(sorted({i for i in item.utterance_indices if i in known_indices}))
        given = own(item.episode_id)
        if not indices or not item.summary.strip() or given in renamed:
            continue
        episode_id = f"e{len(episodes) + 1}"
        renamed[given] = episode_id
        episodes[episode_id] = Episode(
            episode_id=episode_id,
            summary=item.summary.strip(),
            life_period=item.life_period,
            people=_clean(item.people),
            places=_clean(item.places),
            time_references=_clean(item.time_references),
            utterance_indices=indices,
        )

    spoken = SpokenText(utterances)
    earlier = {
        _reference(analysis.session_id, episode.episode_id): (
            analysis.session_id,
            episode.episode_id,
        )
        for analysis in previous
        for episode in analysis.episodes
    }
    # One repetition per episode: the first that passes every check.
    repetitions: dict[str, Repetition] = {}
    for rep in draft.repetitions:
        retelling = renamed.get(own(rep.episode_id))
        if retelling is None or retelling in repetitions:
            continue

        def drop(reason: str, retelling: str = retelling) -> None:
            logger.info("repetition %s of %s dropped: %s", retelling, transcript.session_id, reason)

        if rep.relation is not Relation.SAME_EVENT:
            drop("only a related theme")
            continue
        # The origin is looked for in the earlier sessions first, then in this one. The
        # scope follows from where it is found; the model does not state it.
        given = _bare(rep.retold_from)
        previous_session_id, previous_episode_id = earlier.get(
            given, (None, renamed.get(own(given)))
        )
        if previous_episode_id is None or (
            previous_session_id is None and previous_episode_id == retelling
        ):
            drop(f"unknown origin {rep.retold_from!r}")
            continue
        # Each passage as the person said it, whatever the model tidied away.
        quotes = tuple(
            dict.fromkeys(
                found for q in rep.quoted_passages if (found := spoken.locate(_unlabelled(q)))
            )
        )
        if not quotes or not rep.rationale.strip():
            drop(
                f"none of {rep.quoted_passages} is in the transcript"
                if not quotes
                else "no rationale"
            )
            continue

        # Counted as acknowledged only with the words that say so, found in the transcript.
        acknowledgement = spoken.locate(_unlabelled(rep.acknowledgement_quote or ""))
        repetitions[retelling] = Repetition(
            episode_id=retelling,
            scope=(
                RepetitionScope.WITHIN_SESSION
                if previous_session_id is None
                else RepetitionScope.ACROSS_SESSIONS
            ),
            previous_session_id=previous_session_id,
            previous_episode_id=previous_episode_id,
            self_flagged=acknowledgement is not None,
            acknowledgement_quote=acknowledgement,
            rationale=rep.rationale.strip(),
            quoted_passages=quotes,
        )

    return NarrativeAnalysis(
        session_id=transcript.session_id,
        person_id=transcript.person_id,
        synthetic=transcript.synthetic,
        model_id=model_id,
        episodes=tuple(episodes.values()),
        repetitions=tuple(repetitions.values()),
    )


def _reference(session_id: str, episode_id: str) -> str:
    """How an episode of an earlier session is named to the model."""
    return f"{session_id}/{episode_id}"


def _unlabelled(quote: str) -> str:
    return _UTTERANCE_LABEL.sub("", quote)


def _bare(reference: str) -> str:
    """A reference as the model gave it, without the brackets it sometimes copies."""
    return reference.strip().strip("[]").strip()


def _clean(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(value.strip() for value in values if value.strip())
