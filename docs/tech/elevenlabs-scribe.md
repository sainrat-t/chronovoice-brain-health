---
type: tech-reference
title: ElevenLabs Scribe v3 - Référence technique
description: Spécification et réglages ChronoVoice pour la transcription verbatim, horodatage par mot et diarisation à l'étape 0 (ElevenLabs Scribe v3).
status: stable
tags: [tech, stt, elevenlabs, scribe-v3, step-0, verbatim]
resource: https://elevenlabs.io/docs/overview/capabilities/speech-to-text
sources:
  - name: Documentation officielle ElevenLabs Speech-to-Text
    url: https://elevenlabs.io/docs/overview/capabilities/speech-to-text
  - name: API Reference Create Transcript
    url: https://elevenlabs.io/docs/api-reference/speech-to-text/convert
verified:
  by: Documentation ElevenLabs en ligne
  at: "2026-11-12"
---

# ElevenLabs Scribe : référence technique pour ChronoVoice

Outil de transcription de l'étape 0 (capture et qualité), choisi le 2026-11-12.

> **Sources** : documentation officielle d'ElevenLabs, consultée le 2026-11-12 (liste en fin de fichier). Ce document résume ce dont ChronoVoice a besoin, avec nos réglages. Ce n'est pas une copie de la doc : en cas de doute, la doc en ligne fait foi.

## 1. Pourquoi Scribe

On a comparé Mistral Voxtral, ElevenLabs Scribe, AssemblyAI, Deepgram, OpenAI, WhisperX, CrisperWhisper et Gradium. Scribe est le seul à fournir en un seul appel, et documenté, tout ce dont l'étape 0 a besoin :

- **une transcription verbatim par défaut** : les « um », « uh », faux départs et bruits non verbaux sont conservés tant que `no_verbatim` reste à `false`. Ce sont les éléments du facteur fluence (fiche 08) ;
- **un horodatage par mot** (ou par caractère), nécessaire pour mesurer les pauses ≥ 250 ms (fiche 06) ;
- **la séparation des voix** (diarisation), jusqu'à 32 locuteurs ;
- **90+ langues**, avec détection automatique, ce qui va avec la conception multilingue.

Le prix ne départage pas les outils : environ 0,2 $ par heure d'audio pour la plupart. Voxtral 3, choisi au départ, n'horodate que par segment.

## 2. Modèle retenu : `scribe_v3`

| Modèle | `model_id` | Usage | Prix (2026-11-12) | Pour nous |
|---|---|---|---|---|
| **Scribe v3** | `scribe_v3` | audio enregistré, le plus précis | **0,20 $/h** | **retenu** |
| Scribe v2 | `scribe_v2` | génération précédente, toujours disponible | 0,20 $/h | non : v3 fait 27 % d'erreurs de mots en moins |
| Scribe v2 Medical | `scribe_v2_medical` | audio clinique (dictée médicale) | 0,20 $/h | non : nos récits ne sont pas de la dictée médicale. Il est éligible HIPAA, avec BAA et mode zéro rétention |
| Scribe v3 Live | `scribe_v3_live` | temps réel, par WebSocket | 0,22 $/h | plus tard, si un agent vocal mène l'entretien en direct |

Passer de v2 à v3 se fait en changeant seulement `model_id` : l'API est la même.

**Coûts à connaître**

- Le silence est facturé : chaque seconde envoyée compte, pauses comprises.
- Certaines options sont facturées en plus :
  - `keyterms` : +20 % ;
  - `transcript_edit` : +30 % ;
  - `detect_speaker_roles` : +10 %.
- En mode multicanal, chaque canal est facturé sur toute la durée de l'audio.

## 3. Requête

- **Endpoint** : `POST https://api.elevenlabs.io/v1/speech-to-text`, en `multipart/form-data`.
- **Authentification** : en-tête `xi-api-key`, avec la clé dans la variable d'environnement `ELEVENLABS_API_KEY`. Le fichier `.env` est déjà exclu de git.
- **Navigateur** : pour un enregistrement fait dans le navigateur, on peut utiliser à la place un jeton à usage unique. Il se crée par `POST /v1/single-use-token/batch_scribe` et expire au bout de 15 minutes.

### Nos réglages

| Paramètre | Valeur ChronoVoice | Pourquoi |
|---|---|---|
| `model_id` | `"scribe_v3"` | le plus précis |
| `file` | le fichier audio | ou `source_url` pour un fichier hébergé |
| `language_code` | `"eng"` pour le prototype ; omis ailleurs (détection automatique) | le prototype est en anglais ; la langue détectée part dans les métadonnées de la séance |
| `diarize` | `true` | pour isoler la voix de la personne suivie |
| `num_speakers` | `2` quand on sait qu'il y a un seul interlocuteur | aide la diarisation ; sinon, on l'omet |
| `timestamps_granularity` | `"word"` | pour les pauses |
| `no_verbatim` | **`false`** (la valeur par défaut) | **ne jamais l'activer** : il supprime les hésitations et les faux départs, donc le signal de fluence |
| `tag_audio_events` | `true` | rires, toux… exclus du compte de mots, utiles au contrôle qualité |
| `numbers_format` | `"words"` | « forty-two » plutôt que « 42 », pour compter les mots réellement prononcés (v3 seulement) |
| `temperature` | `0.0` | sortie la plus stable possible |
| `seed` | un entier fixe | reproductibilité au mieux : ElevenLabs ne la garantit pas |
| `keyterms` | **non** | biaiserait le vocabulaire transcrit, donc les mesures lexicales ; et coûte 20 % de plus |
| `transcript_edit` | **non** | réécrit le texte |
| `entity_redaction` | **non** sur le texte analysé | modifie le texte ; à réserver à l'affichage si besoin |
| `webhook` | `false` pour le prototype | l'appel synchrone suffit ; un webhook servira pour une intégration comme MyMémoires |

### Options à explorer plus tard

- **`use_multi_channel`** : si l'application source enregistre chaque voix sur un canal séparé (jusqu'à 5 canaux), chaque canal est transcrit à part. On évite alors les erreurs de diarisation, mais chaque canal est facturé.
- **`use_speaker_library`** : reconnaît des voix enregistrées au préalable. Cela pourrait régler la question de savoir quelle voix est celle de la personne suivie. Implications pour la vie privée à évaluer, doc non lue.
- **`enable_logging=false`** (paramètre d'URL) : mode zéro rétention, rien n'est stocké chez ElevenLabs. Réservé aux clients Enterprise.

## 4. Réponse

Objet principal (`SpeechToTextChunkResponseModel`) :

| Champ | Contenu | Usage ChronoVoice |
|---|---|---|
| `language_code` | langue détectée, en ISO 639-3 (`"eng"`) | métadonnée de séance, adaptateur de langue |
| `language_probability` | confiance de la détection de langue (0 à 1) | contrôle qualité |
| `text` | transcription complète | analyse du récit (étape 2) |
| `words` | liste des éléments horodatés, voir ci-dessous | toutes les mesures de l'étape 1 |
| `transcription_id` | identifiant du transcript | récupération (`GET`) et suppression (`DELETE`) |
| `audio_duration_secs` | durée facturée | contrôle qualité, coûts |

Chaque élément de `words` contient :

| Champ | Contenu |
|---|---|
| `text` | le mot, l'espace ou l'événement sonore |
| `type` | `word` (mot), `spacing` (espace entre deux mots) ou `audio_event` (rire, toux…) |
| `start`, `end` | début et fin, en secondes |
| `speaker_id` | `speaker_0`, `speaker_1`… si `diarize=true` |
| `logprob` | log-probabilité du mot, de −∞ à 0 : plus c'est proche de 0, plus le modèle est sûr |
| `characters` | détail par caractère, si `timestamps_granularity="character"` |

## 5. Ce que ChronoVoice en tire (étape 0 vers étape 1)

- **Voix de la personne suivie.** On garde les éléments dont le `speaker_id` est celui de la personne. Pour savoir lequel c'est, il faut une règle : une métadonnée de l'application source, ou le locuteur qui parle le plus longtemps. **À décider.**
- **Pauses.** Une pause est l'écart entre la fin d'un mot (`end`) et le début du mot suivant (`start`), pour deux mots consécutifs de la même personne. On compte celles ≥ 0,25 s (fiche 06).
  - **Ne pas utiliser les éléments `spacing` pour les pauses.** Dans l'exemple de la doc, l'espace qui suit « accent, » dure 0,06 s, alors que l'écart réel entre les deux mots est de 0,77 s.
- **Entre ou dans les énoncés.**
  - Une pause compte comme **entre énoncés** si le mot qui la précède se termine par une ponctuation de fin de phrase (`.`, `?`, `!`) ou s'il y a changement de locuteur. Sinon, c'est une pause **dans l'énoncé**.
  - **Hypothèse à valider** : la ponctuation est déduite par le modèle, pas prononcée.
- **Hésitations et faux départs.** Ils sont conservés par défaut, mais leur forme exacte dans le texte (« um », « uh », « I- I went »…) n'est pas documentée. **À relever sur un échantillon** avant d'écrire le détecteur de l'indice de fluence (fiche 08).
- **Contrôle qualité.**
  - Rejeter ou marquer partielle une séance si :
    - le `logprob` moyen des mots de la personne est faible ;
    - la `language_probability` est basse ;
    - la parole de la personne dure trop peu, ou compte moins de 150 mots (fiche 08) ;
    - les `audio_event` sont trop nombreux.
  - Les seuils restent à fixer.

## 6. Limites

- **Taille et durée** : de 100 ms à 15 h d'audio, et moins de 5 Go par fichier.
- **Formats audio** : AAC, AIFF, OGG, MP3, OPUS, WAV, FLAC, M4A, WebM.
- **Formats vidéo** : MP4, MOV, MKV, WebM, entre autres.
- **Requêtes simultanées** : leur nombre dépend du forfait.

  | Forfait | Free | Starter | Creator | Pro | Scale / Business |
  |---|---|---|---|---|---|
  | Requêtes simultanées | 8 | 12 | 20 | 40 | 60 |

  - Au-delà de 8 minutes, un fichier est découpé en morceaux transcrits en parallèle, jusqu'à 4. Chaque morceau compte dans cette limite.
  - Les en-têtes de réponse `current-concurrent-requests` et `maximum-concurrent-requests` permettent de suivre la charge.

## 7. Données et conformité (slides 8 et 9 du deck)

- **Stockage.** Par défaut, les données sont stockées aux États-Unis, et les transcripts sont conservés chez ElevenLabs. On les relit par `GET /v1/speech-to-text/transcripts/{transcription_id}` et on les supprime par `DELETE` sur la même URL.
  - **Bonne pratique, même sur le prototype** : supprimer le transcript chez ElevenLabs dès qu'il est enregistré chez nous.
- **Zéro rétention** (`enable_logging=false`) : rien n'est stocké. Réservé aux clients Enterprise.
- **Hébergement régional** (Enterprise) : environnements isolés en Europe, en Inde et à Singapour. **Pas de région aux Émirats.**
  - Le traitement peut quand même avoir lieu hors de la région choisie, sauf en Europe avec le mode zéro rétention.
- **Certifications et engagements annoncés par ElevenLabs** :
  - SOC 2 ;
  - conformité au RGPD ;
  - chiffrement des échanges ;
  - BAA HIPAA pour les établissements de santé éligibles.
- **Pour le prototype** : données synthétiques uniquement (règle 3 de CLAUDE.md). La clé API ne doit jamais être commitée.

## 8. SDK Python

```bash
uv add elevenlabs
```

Exemple d'appel avec nos réglages :

```python
import os

from elevenlabs.client import ElevenLabs

client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])

with open("session.wav", "rb") as audio:
    transcript = client.speech_to_text.convert(
        file=audio,
        model_id="scribe_v3",
        language_code="eng",
        diarize=True,
        num_speakers=2,
        timestamps_granularity="word",
        tag_audio_events=True,
        no_verbatim=False,
        numbers_format="words",
        temperature=0.0,
        seed=42,
    )
```

- **Quand ajouter la dépendance.** D'après CLAUDE.md, on ajoute la dépendance au backend seulement quand l'étape 0 est validée.
- **Pour les tests.** Les tests unitaires ne doivent pas appeler l'API : ils travaillent sur des réponses JSON enregistrées.
- **Ce qui reste à vérifier.** Les noms des arguments viennent de la référence de l'API. Leur nom exact dans le SDK n'est pas vérifié, en particulier pour `numbers_format`.

## 9. À tester avant de coder les mesures

Sur 2 ou 3 enregistrements en anglais, de préférence une personne âgée qui raconte un souvenir avec un interlocuteur :

1. **Hésitations et faux départs** : leur forme exacte dans `words`.
2. **Précision des pauses** : comparer les pauses calculées avec un repérage fait à la main dans Audacity, comme la fiche 06.
3. **Ponctuation** : la ponctuation de fin de phrase suit-elle vraiment les énoncés ?
4. **Diarisation à deux voix** : erreurs d'attribution, chevauchements.
5. **Stabilité** : le même fichier transcrit deux fois avec `temperature=0` et un `seed` fixe donne-t-il le même résultat ? C'est important : sinon, la transcription ajoute son propre bruit au bruit d'une séance à l'autre (fiche 09).

## Sources

Documentation ElevenLabs, consultée le 2026-11-12 :

- [Transcription (vue d'ensemble, langues, limites, FAQ)](https://elevenlabs.io/docs/overview/capabilities/speech-to-text)
- [Create transcript (référence API)](https://elevenlabs.io/docs/api-reference/speech-to-text/convert)
- [Get transcript](https://elevenlabs.io/docs/api-reference/speech-to-text/get) · [Delete transcript](https://elevenlabs.io/docs/api-reference/speech-to-text/delete)
- [Models (Scribe v3, requêtes simultanées)](https://elevenlabs.io/docs/overview/models)
- [Speech to Text quickstart (SDK)](https://elevenlabs.io/docs/eleven-api/guides/cookbooks/speech-to-text)
- [Asynchronous Speech to Text (webhooks)](https://elevenlabs.io/docs/eleven-api/guides/how-to/speech-to-text/batch/webhooks)
- [Data residency](https://elevenlabs.io/docs/overview/administration/data-residency)
- [API pricing](https://elevenlabs.io/pricing/api)
- Spécification OpenAPI complète : [openapi.json](https://elevenlabs.io/docs/openapi.json)
