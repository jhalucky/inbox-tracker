from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TextIO

from app.config import Settings, get_settings
from app.pipeline.cleaning import clean_body
from app.pipeline.rules_filter import should_skip
from app.pipeline.scoring import apply_sender_weight
from app.providers.base import Classification, EmailInput, LLMProvider
from app.providers.factory import LLMConfigError, get_llm_provider


def coerce_needs_reply_label(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in {0, 1}:
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "yes", "needs_reply", "1"}:
        return True
    if text in {"false", "no", "no_reply", "0"}:
        return False
    return None


def estimate_cost(
    prompt_tokens: int,
    completion_tokens: int,
    settings: Settings,
) -> float | None:
    if settings.llm_price_input_per_m is None and settings.llm_price_output_per_m is None:
        return None
    inp = settings.llm_price_input_per_m or 0.0
    out = settings.llm_price_output_per_m or 0.0
    return (prompt_tokens / 1_000_000) * inp + (completion_tokens / 1_000_000) * out


@dataclass
class ItemResult:
    index: int
    subject: str
    skipped: bool
    classification: Classification | None
    label: bool | None


@dataclass
class RunReport:
    items: list[ItemResult] = field(default_factory=list)

    @property
    def skipped_count(self) -> int:
        return sum(1 for item in self.items if item.skipped)

    @property
    def prompt_tokens(self) -> int:
        return sum(
            item.classification.prompt_tokens for item in self.items if item.classification
        )

    @property
    def completion_tokens(self) -> int:
        return sum(
            item.classification.completion_tokens for item in self.items if item.classification
        )

    def labeled_classified(self) -> list[ItemResult]:
        return [
            item
            for item in self.items
            if not item.skipped and item.label is not None and item.classification is not None
        ]

    def predicted_needs_reply(self, item: ItemResult) -> bool:
        if item.classification is None or item.classification.needs_reply is None:
            return False
        return item.classification.needs_reply

    def accuracy(self) -> tuple[float, int, int] | None:
        labeled = self.labeled_classified()
        if not labeled:
            return None
        correct = sum(
            1 for item in labeled if self.predicted_needs_reply(item) == item.label
        )
        return correct / len(labeled), correct, len(labeled)

    def precision_recall(self) -> tuple[float | None, float | None]:
        labeled = self.labeled_classified()
        if not labeled:
            return None, None
        tp = fp = fn = 0
        for item in labeled:
            pred = self.predicted_needs_reply(item)
            if pred and item.label:
                tp += 1
            elif pred and not item.label:
                fp += 1
            elif not pred and item.label:
                fn += 1
        precision = tp / (tp + fp) if (tp + fp) else None
        recall = tp / (tp + fn) if (tp + fn) else None
        return precision, recall

    def wrong(self) -> list[ItemResult]:
        return [
            item
            for item in self.labeled_classified()
            if self.predicted_needs_reply(item) != item.label
        ]


def classify_one(
    email: EmailInput,
    provider: LLMProvider,
    *,
    importance_weight: float = 1.0,
) -> tuple[bool, Classification | None]:
    if should_skip(email):
        return True, None
    cleaned = email.model_copy(update={"body": clean_body(email.body)})
    result = provider.classify(cleaned)
    result.adjusted_urgency = apply_sender_weight(result.urgency, importance_weight)
    return False, result


def run(
    emails: list[dict[str, Any]],
    provider: LLMProvider,
    *,
    limit: int | None = None,
    importance_weight: float = 1.0,
) -> RunReport:
    report = RunReport()
    selected = emails[:limit] if limit is not None else emails
    for index, raw in enumerate(selected):
        email = EmailInput.model_validate(raw)
        skipped, classification = classify_one(
            email, provider, importance_weight=importance_weight
        )
        report.items.append(
            ItemResult(
                index=index,
                subject=email.subject,
                skipped=skipped,
                classification=classification,
                label=coerce_needs_reply_label(raw.get("label")),
            )
        )
    return report


def _truncate(text: str, width: int = 60) -> str:
    compact = " ".join(text.split())
    if len(compact) <= width:
        return compact
    return compact[: width - 3] + "..."


def _fmt_float(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}"


def format_report(report: RunReport, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    lines: list[str] = []
    for item in report.items:
        subject = _truncate(item.subject)
        if item.skipped:
            lines.append(f"{item.index}\t{subject}\tskipped by rules")
            continue
        assert item.classification is not None
        c = item.classification
        lines.append(
            f"{item.index}\t{subject}\t"
            f"needs_reply={c.needs_reply} urgency={c.urgency} "
            f"category={c.category} reason={c.reason}"
        )

    lines.append("")
    lines.append(f"skipped: {report.skipped_count}")
    acc = report.accuracy()
    if acc is None:
        lines.append("accuracy: n/a (no labels)")
        lines.append("precision: n/a  recall: n/a")
    else:
        ratio, correct, total = acc
        lines.append(f"accuracy: {ratio:.2f} ({correct}/{total})")
        precision, recall = report.precision_recall()
        lines.append(
            f"precision: {_fmt_float(precision)}  recall: {_fmt_float(recall)}  "
            "(needs_reply=true)"
        )
        wrong = report.wrong()
        if wrong:
            lines.append("wrong:")
            for item in wrong:
                reason = item.classification.reason if item.classification else ""
                lines.append(f"  {item.index}\t{_truncate(item.subject)}\t{reason}")
        else:
            lines.append("wrong: none")

    total_tokens = report.prompt_tokens + report.completion_tokens
    lines.append(
        f"tokens: prompt={report.prompt_tokens} completion={report.completion_tokens} "
        f"total={total_tokens}"
    )
    cost = estimate_cost(report.prompt_tokens, report.completion_tokens, settings)
    if cost is None:
        lines.append(
            "estimated cost: n/a (set LLM_PRICE_INPUT_PER_M and LLM_PRICE_OUTPUT_PER_M)"
        )
    else:
        lines.append(f"estimated cost: ${cost:.6f}")
    return "\n".join(lines) + "\n"


def load_emails(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("emails JSON must be a list of objects")
    return data


def main(argv: list[str] | None = None, out: TextIO | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Classify emails from a JSON file (no bodies are printed)."
    )
    parser.add_argument("emails_json", type=Path)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)

    emails = load_emails(args.emails_json)
    try:
        provider = get_llm_provider()
    except LLMConfigError as exc:
        print(exc, file=sys.stderr)
        return 2
    report = run(emails, provider, limit=args.limit)
    text = format_report(report)
    (out or sys.stdout).write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
