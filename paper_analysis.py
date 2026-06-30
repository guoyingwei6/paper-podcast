from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import TypeAlias

JsonValue: TypeAlias = str | list[str]

REQUIRED_FIELDS = (
    "research_question",
    "why_it_matters",
    "study_design",
    "data_and_samples",
    "methods",
    "key_findings_with_numbers",
    "mechanism_or_interpretation",
    "limitations",
    "field_context",
    "talking_points_for_podcast",
    "caveats_for_hosts",
)


@dataclass(frozen=True, slots=True)
class PaperAnalysis:
    research_question: str
    why_it_matters: str
    study_design: str
    data_and_samples: str
    methods: str
    key_findings_with_numbers: tuple[str, ...]
    mechanism_or_interpretation: str
    limitations: str
    field_context: str
    talking_points_for_podcast: tuple[str, ...]
    caveats_for_hosts: tuple[str, ...]

    def to_summary(self) -> str:
        findings = "；".join(self.key_findings_with_numbers)
        return (
            f"研究问题：{self.research_question}\n"
            f"重要性：{self.why_it_matters}\n"
            f"研究设计与数据：{self.study_design}；{self.data_and_samples}\n"
            f"方法：{self.methods}\n"
            f"关键结果：{findings}\n"
            f"解释：{self.mechanism_or_interpretation}\n"
            f"局限：{self.limitations}\n"
            f"领域语境：{self.field_context}"
        )

    def to_prompt_text(self) -> str:
        findings = "\n".join(f"- {item}" for item in self.key_findings_with_numbers)
        talking_points = "\n".join(f"- {item}" for item in self.talking_points_for_podcast)
        caveats = "\n".join(f"- {item}" for item in self.caveats_for_hosts)
        return (
            f"研究问题：{self.research_question}\n"
            f"为什么重要：{self.why_it_matters}\n"
            f"研究设计：{self.study_design}\n"
            f"数据与样本：{self.data_and_samples}\n"
            f"方法：{self.methods}\n"
            f"关键结果（保留数字和比较对象）：\n{findings}\n"
            f"机制或解释：{self.mechanism_or_interpretation}\n"
            f"局限性：{self.limitations}\n"
            f"领域背景：{self.field_context}\n"
            f"播客讨论点：\n{talking_points}\n"
            f"主持人谨慎点：\n{caveats}"
        )


def parse_paper_analysis_json(raw_text: str) -> PaperAnalysis:
    payload = _load_json_object(raw_text)
    missing = [field for field in REQUIRED_FIELDS if not _has_content(payload.get(field))]
    if missing:
        raise ValueError(f"paper analysis missing fields: {', '.join(missing)}")

    return PaperAnalysis(
        research_question=_as_text(payload["research_question"]),
        why_it_matters=_as_text(payload["why_it_matters"]),
        study_design=_as_text(payload["study_design"]),
        data_and_samples=_as_text(payload["data_and_samples"]),
        methods=_as_text(payload["methods"]),
        key_findings_with_numbers=_as_text_tuple(payload["key_findings_with_numbers"]),
        mechanism_or_interpretation=_as_text(payload["mechanism_or_interpretation"]),
        limitations=_as_text(payload["limitations"]),
        field_context=_as_text(payload["field_context"]),
        talking_points_for_podcast=_as_text_tuple(payload["talking_points_for_podcast"]),
        caveats_for_hosts=_as_text_tuple(payload["caveats_for_hosts"]),
    )


def _load_json_object(raw_text: str) -> dict[str, JsonValue]:
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end < start:
        raise ValueError("paper analysis response does not contain a JSON object")

    data = json.loads(cleaned[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("paper analysis response must be a JSON object")
    return data


def _has_content(value: JsonValue | None) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(isinstance(item, str) and item.strip() for item in value)
    return False


def _as_text(value: JsonValue) -> str:
    if isinstance(value, str):
        return value.strip()
    return "；".join(item.strip() for item in value if isinstance(item, str) and item.strip())


def _as_text_tuple(value: JsonValue) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value.strip(),)
    return tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
