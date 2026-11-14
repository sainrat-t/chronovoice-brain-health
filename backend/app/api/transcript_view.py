"""Annotated transcript of a session, for the session detail screen.

Everything highlighted is computed here, with the same code as the markers of step 1
(docs/specs/clinician-ui.md, screen 3): hesitations, cut-off words, immediate
repetitions, pauses of at least PAUSE_THRESHOLD_S, and audio events.
"""

from __future__ import annotations

from itertools import groupby

from app.agents.markers import PAUSE_THRESHOLD_S, find_immediate_repetitions, find_pauses
from app.agents.segmentation import SpokenWord, WordKind, segment_target_speech
from app.api.models import AnnotatedTranscript, TranscriptItem, TranscriptItemKind, TranscriptTurn
from app.language.base import LanguageAdapter
from app.schemas import SessionTranscript, TokenKind, TranscriptToken

_KINDS = {
    WordKind.LEXICAL: TranscriptItemKind.WORD,
    WordKind.FILLER: TranscriptItemKind.FILLER,
    WordKind.CUT_OFF: TranscriptItemKind.CUT_OFF,
}

_Key = tuple[float, float, str]


def annotate_transcript(
    transcript: SessionTranscript, adapter: LanguageAdapter
) -> AnnotatedTranscript:
    turns = segment_target_speech(transcript, adapter)

    # The words of the tracked speaker, as step 1 sees them.
    spoken: dict[_Key, SpokenWord] = {}
    repeated: set[_Key] = set()
    for turn in turns:
        for word in turn.words:
            spoken[_key_of(word)] = word
        for utterance in turn.utterances:
            lexical = utterance.lexical_words
            for position, size in find_immediate_repetitions([w.form for w in lexical]):
                repeated.update(_key_of(w) for w in lexical[position : position + size])
    # A pause is found after the word that ends where it starts.
    pauses = {pause.start_s: pause for pause in find_pauses(turns)}

    view: list[TranscriptTurn] = []
    for speaker_id, group in groupby(transcript.tokens, key=lambda t: t.speaker_id):
        tracked = speaker_id == transcript.target_speaker_id
        items: list[TranscriptItem] = []
        for token in group:
            items.append(_item(token, spoken, repeated, tracked=tracked))
            pause = pauses.get(token.end_s) if tracked else None
            if pause is not None and (token.start_s, token.end_s, token.text) in spoken:
                items.append(
                    TranscriptItem(
                        kind=TranscriptItemKind.PAUSE,
                        text="",
                        start_s=pause.start_s,
                        end_s=round(pause.start_s + pause.duration_s, 3),
                        between_utterances=pause.between_utterances,
                    )
                )
        view.append(
            TranscriptTurn(speaker_id=speaker_id, is_tracked_speaker=tracked, items=tuple(items))
        )
    return AnnotatedTranscript(
        target_speaker_id=transcript.target_speaker_id,
        pause_threshold_s=PAUSE_THRESHOLD_S,
        turns=tuple(view),
    )


def _item(
    token: TranscriptToken,
    spoken: dict[_Key, SpokenWord],
    repeated: set[_Key],
    *,
    tracked: bool,
) -> TranscriptItem:
    if token.kind is TokenKind.AUDIO_EVENT:
        kind = TranscriptItemKind.AUDIO_EVENT
    else:
        word = spoken.get((token.start_s, token.end_s, token.text)) if tracked else None
        kind = TranscriptItemKind.WORD if word is None else _KINDS[word.kind]
    key = (token.start_s, token.end_s, token.text)
    return TranscriptItem(
        kind=kind,
        text=token.text,
        start_s=token.start_s,
        end_s=token.end_s,
        repeated=tracked and key in repeated,
    )


def _key_of(word: SpokenWord) -> _Key:
    return (word.start_s, word.end_s, word.raw)
