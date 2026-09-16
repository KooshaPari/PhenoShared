"""Non-LLM semantic analysis engine for benchmark trace decomposition."""

import math
import re
import string
from collections import Counter
from typing import Any


def tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return [t for t in text.split() if t]


def syllable_count(word: str) -> int:
    """Estimate syllable count by vowel groups."""
    word = word.lower().strip(string.punctuation)
    if not word:
        return 0
    vowels = "aeiouy"
    count = 0
    prev_vowel = False
    for ch in word:
        is_vowel = ch in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    if word.endswith("e") and count > 1:
        count -= 1
    return max(count, 1)


# --- Core Analysis ---


def relevance_score(reply: str, prompt: str) -> float:
    """BM25-style keyword overlap via TF-cosine similarity."""
    prompt_tokens = tokenize(prompt)
    reply_tokens = tokenize(reply)
    if not prompt_tokens or not reply_tokens:
        return 0.0

    prompt_tf = Counter(prompt_tokens)
    reply_tf = Counter(reply_tokens)

    shared = set(prompt_tf) & set(reply_tf)
    if not shared:
        return 0.0

    dot = sum(prompt_tf[k] * reply_tf[k] for k in shared)
    mag_p = math.sqrt(sum(v * v for v in prompt_tf.values()))
    mag_r = math.sqrt(sum(v * v for v in reply_tf.values()))
    if mag_p == 0 or mag_r == 0:
        return 0.0
    return min(dot / (mag_p * mag_r), 1.0)


def coherence_score(reply: str) -> float:
    """Sentence-level transition consistency via shared-word overlap."""
    sentences = [s.strip() for s in re.split(r"[.!?\n]+", reply) if s.strip()]
    if len(sentences) < 2:
        return 0.5

    overlaps = []
    for i in range(len(sentences) - 1):
        words_a = {w for w in tokenize(sentences[i]) if len(w) > 3}
        words_b = {w for w in tokenize(sentences[i + 1]) if len(w) > 3}
        if words_a and words_b:
            overlap = len(words_a & words_b) / max(len(words_a | words_b), 1)
        else:
            overlap = 0.0
        overlaps.append(overlap)

    raw = sum(overlaps) / len(overlaps)
    return min(raw * 3, 1.0)


def completeness_score(reply: str, difficulty: str) -> float:
    """Reply length vs expected complexity ratio."""
    expected_tokens = {
        "trivial": 50,
        "easy": 150,
        "medium": 400,
        "hard": 800,
        "extreme": 1500,
    }
    expected = expected_tokens.get(difficulty.lower(), 400)
    actual = len(tokenize(reply))
    return min(actual / max(expected, 1), 1.0)


def accuracy_hints(reply: str) -> float:
    """Ratio of confident phrases vs hedging phrases."""
    hedging = [
        "maybe",
        "perhaps",
        "i think",
        "i believe",
        "might be",
        "could be",
        "possibly",
        "not sure",
        "seems like",
        "i guess",
        "probably",
        "apparently",
    ]
    confident = [
        "definitely",
        "certainly",
        "the answer is",
        "clearly",
        "obviously",
        "yes",
        "no",
        "exactly",
        "always",
        "never",
        "is exactly",
        "the correct",
    ]

    lower = reply.lower()
    hedge_count = sum(lower.count(h) for h in hedging)
    conf_count = sum(lower.count(c) for c in confident)
    total = hedge_count + conf_count
    if total == 0:
        return 0.5
    return conf_count / total


def format_score(reply: str, expected: str) -> float:
    """Does reply match expected format (JSON, letter, etc.)?"""
    expected_lower = expected.lower().strip()
    reply_lower = reply.lower().strip()

    if expected_lower in ("json", "json object", "json array"):
        has_json = bool(re.search(r"\{.*:.*\}|\[.*\]", reply, re.DOTALL))
        return 1.0 if has_json else 0.3

    if expected_lower in ("letter", "letter answer", "a", "b", "c", "d"):
        letters = re.findall(r"\b([a-d])\b", reply_lower)
        if letters:
            return 1.0
        single = re.findall(r"\b([a-d])\b", expected_lower)
        if single and single[0] in reply_lower:
            return 1.0
        return 0.2

    if expected_lower in ("number", "numeric", "integer", "float"):
        has_number = bool(re.search(r"\d+\.?\d*", reply))
        return 1.0 if has_number else 0.3

    if expected_lower in ("code", "python", "function"):
        has_code = bool(re.search(r"(def |class |import |return |print\()", reply))
        return 1.0 if has_code else 0.4

    if expected_lower in ("yes/no", "boolean", "true/false"):
        has_bool = bool(re.search(r"\b(yes|no|true|false)\b", reply_lower))
        return 1.0 if has_bool else 0.3

    return 0.5


def error_density(reply: str) -> float:
    """Ratio of error-related words to total words."""
    error_words = [
        "error",
        "failed",
        "exception",
        "bug",
        "crash",
        "wrong",
        "mistake",
        "incorrect",
        "invalid",
        "undefined",
        "null",
        "none",
        "missing",
        "cannot",
        "unable",
        "sorry",
    ]
    tokens = tokenize(reply)
    if not tokens:
        return 0.0
    count = sum(1 for t in tokens if t in error_words)
    return count / len(tokens)


def info_density(reply: str) -> float:
    """Vocabulary richness: unique words / total words."""
    tokens = tokenize(reply)
    if not tokens:
        return 0.0
    return len(set(tokens)) / len(tokens)


def readability_kincaid(reply: str) -> float:
    """Approximate Flesch-Kincaid grade level."""
    tokens = tokenize(reply)
    sentences = [s.strip() for s in re.split(r"[.!?\n]+", reply) if s.strip()]

    if not tokens or not sentences:
        return 0.0

    total_syllables = sum(syllable_count(t) for t in tokens)
    word_count = len(tokens)
    sentence_count = len(sentences)

    if sentence_count == 0 or word_count == 0:
        return 0.0

    grade = (
        0.39 * (word_count / sentence_count)
        + 11.8 * (total_syllables / word_count)
        - 15.59
    )
    return max(grade, 0.0)


# --- Composite ---


def analyze_response_quality(reply: str, prompt: str, expected: str) -> dict[str, Any]:
    """Main entry point: decompose a response into quality factors."""
    return {
        "relevance_score": relevance_score(reply, prompt),
        "coherence_score": coherence_score(reply),
        "completeness_score": completeness_score(reply, "medium"),
        "accuracy_hints": accuracy_hints(reply),
        "format_score": format_score(reply, expected),
        "error_density": error_density(reply),
        "info_density": info_density(reply),
        "readability": readability_kincaid(reply),
    }


# --- Failure Decomposition ---

_FAILURE_RULES = [
    ("timeout", "timed out", "time limit"),
    ("error", "failed", "exception", "traceback"),
    ("i don't know", "i'm not sure", "no idea"),
    ("retry", "tried again", "attempted"),
    ("format", "expected", "should be"),
    ("too long", "truncated", "context window"),
    ("refactor", "implement", "fix", "add"),
    ("question", "answer", "choose"),
]

_FAILURE_LABELS = [
    "harness_compat",
    "tool_calling",
    "llm_quality",
    "loop_engineering",
    "harness_compat",
    "context_overflow",
    "swe_eng",
    "prompt_eng",
]


def decompose_failure_mode(reply: str, prompt: str, expected: str) -> dict[str, Any]:
    """Classify the failure mode from a single reply."""
    lower = reply.lower()
    scores: dict[str, float] = {}
    evidence_map: dict[str, list[str]] = {}

    for label_group, label in zip(_FAILURE_RULES, _FAILURE_LABELS):
        matches = [kw for kw in label_group if kw in lower]
        if matches:
            scores[label] = scores.get(label, 0) + len(matches)
            evidence_map.setdefault(label, []).extend(matches)

    if not scores:
        primary = "llm_quality"
        confidence = 0.3
        evidence_list = []
    else:
        primary = max(scores, key=scores.get)  # type: ignore[arg-type]
        total = sum(scores.values())
        confidence = scores[primary] / total if total else 0.5
        evidence_list = evidence_map.get(primary, [])

    secondary = [f for f in scores if f != primary]

    return {
        "primary_factor": primary,
        "confidence": round(confidence, 3),
        "secondary_factors": secondary,
        "evidence": evidence_list,
    }


# --- Progress Simulation ---


def compute_task_progress(reply: str, prompt: str, difficulty: str) -> list[dict[str, Any]]:
    """Simulate a progress trace from a single response."""
    sentences = [s.strip() for s in re.split(r"[.!?\n]+", reply) if s.strip()]
    if not sentences:
        return []

    n = len(sentences)
    milestones = [
        "initial_response",
        "reasoning_started",
        "key_insight",
        "solution_formed",
        "solution_delivered",
        "verification",
    ]

    prompt_tokens = set(tokenize(prompt))
    trace = []

    for i, sent in enumerate(sentences):
        sent_tokens = set(tokenize(sent))
        overlap = len(sent_tokens & prompt_tokens) / max(
            len(sent_tokens | prompt_tokens), 1
        )
        sent_len = len(sent_tokens)
        density = len(sent_tokens) / max(sent_len, 1)
        length_bonus = min(sent_len / 50, 0.3)
        quality = min(overlap * 0.5 + density * 0.2 + length_bonus + 0.2, 1.0)

        # assign milestone based on position ratio
        ratio = i / max(n - 1, 1)
        if ratio < 0.1:
            ms = milestones[0]
        elif ratio < 0.25:
            ms = milestones[1]
        elif ratio < 0.45:
            ms = milestones[2]
        elif ratio < 0.65:
            ms = milestones[3]
        elif ratio < 0.85:
            ms = milestones[4]
        else:
            ms = milestones[5]

        trace.append({"t": i, "quality": round(quality, 3), "milestone": ms})

    return trace


# --- Aggregate ---


def score_factor_decomposition(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate factor analysis across all cells.

    Each cell is expected to be a dict with at least 'primary_factor' and
    'quality' (0-1 float) keys.
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    for cell in cells:
        factor = cell.get("primary_factor", "unknown")
        grouped.setdefault(factor, []).append(cell)

    result = {}
    for factor, items in grouped.items():
        qualities = [it.get("quality", 0.0) for it in items]
        mean_q = sum(qualities) / len(qualities) if qualities else 0.0
        worst = sorted(items, key=lambda x: x.get("quality", 1.0))[:3]
        result[factor] = {
            "count": len(items),
            "mean_quality": round(mean_q, 4),
            "worst_tasks": [
                {"task": it.get("task", "unknown"), "quality": it.get("quality", 0.0)}
                for it in worst
            ],
        }

    return result
