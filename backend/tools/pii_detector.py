"""
tools/pii_detector.py
----------------------
Detects Personally Identifiable Information in document text.
Uses Microsoft Presidio when available; falls back to regex patterns.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from core.logger import get_logger

logger = get_logger(__name__)

# Regex fallback patterns
_PII_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("email",   re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")),
    ("phone",   re.compile(r"\b(\+?\d[\d\s\-().]{7,}\d)\b")),
    ("ssn",     re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("credit_card", re.compile(r"\b(?:\d[ -]?){13,16}\b")),
    ("ip_addr", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
]


@dataclass
class PIIResult:
    has_pii: bool
    findings: list[dict]       # [{"type": str, "text": str, "start": int, "end": int}]
    redacted_text: str


def detect_pii(text: str) -> PIIResult:
    """
    Run PII detection.
    Tries Presidio first; falls back to regex.
    """
    try:
        return _presidio_detect(text)
    except Exception as exc:
        logger.warning("presidio_unavailable", error=str(exc), fallback="regex")
        return _regex_detect(text)


_analyzer = None  # singleton — loaded once, reused on every call

def _get_analyzer():
    global _analyzer
    if _analyzer is None:
        from presidio_analyzer import AnalyzerEngine  # type: ignore
        logger.info("presidio_loading")
        _analyzer = AnalyzerEngine()
        logger.info("presidio_ready")
    return _analyzer


_PII_SCORE_THRESHOLD = 0.7  # only flag high-confidence detections to avoid false positives

def _presidio_detect(text: str) -> PIIResult:
    analyzer = _get_analyzer()
    results = analyzer.analyze(text=text, language="en", score_threshold=_PII_SCORE_THRESHOLD)

    findings = []
    redacted = text
    for res in sorted(results, key=lambda r: r.start, reverse=True):
        span = text[res.start : res.end]
        findings.append({
            "type": res.entity_type,
            "text": span,
            "start": res.start,
            "end": res.end,
            "score": res.score,
        })
        redacted = redacted[: res.start] + f"[{res.entity_type}]" + redacted[res.end :]

    has_pii = len(findings) > 0
    logger.info("pii_presidio", has_pii=has_pii, count=len(findings))
    return PIIResult(has_pii=has_pii, findings=findings, redacted_text=redacted)


def _regex_detect(text: str) -> PIIResult:
    findings = []
    redacted = text

    for label, pattern in _PII_PATTERNS:
        for match in pattern.finditer(text):
            findings.append({
                "type": label,
                "text": match.group(),
                "start": match.start(),
                "end": match.end(),
            })

    # Redact in reverse order
    sorted_findings = sorted(findings, key=lambda f: f["start"], reverse=True)
    for f in sorted_findings:
        redacted = redacted[: f["start"]] + f"[{f['type'].upper()}]" + redacted[f["end"] :]

    has_pii = len(findings) > 0
    logger.info("pii_regex", has_pii=has_pii, count=len(findings))
    return PIIResult(has_pii=has_pii, findings=findings, redacted_text=redacted)
