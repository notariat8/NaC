from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_CATALOG_GLOB = "usecases/*/knowledge-graph.graph.json"
EMPTY_VALUES = (None, "", [], {})


@dataclass(frozen=True, slots=True)
class CaseSummary:
    catalog_id: str
    case_id: str
    slug: str
    title: str
    status: str
    priority: str
    usecase_path: str
    required_information: int
    open_required_information: int
    documents: int
    decisions: int
    gates: int
    evidence: int
    plugin_dependencies: tuple[str, ...]
    workflow_dependencies: tuple[str, ...]
    first_open_questions: tuple[str, ...]
    non_empty_values: tuple[str, ...]

    @property
    def ready_for_development(self) -> bool:
        return self.required_information > 0 and not self.non_empty_values

    def to_dict(self) -> dict[str, Any]:
        return {
            "catalog_id": self.catalog_id,
            "case_id": self.case_id,
            "slug": self.slug,
            "title": self.title,
            "status": self.status,
            "priority": self.priority,
            "usecase_path": self.usecase_path,
            "required_information": self.required_information,
            "open_required_information": self.open_required_information,
            "documents": self.documents,
            "decisions": self.decisions,
            "gates": self.gates,
            "evidence": self.evidence,
            "plugin_dependencies": list(self.plugin_dependencies),
            "workflow_dependencies": list(self.workflow_dependencies),
            "first_open_questions": list(self.first_open_questions),
            "non_empty_values": list(self.non_empty_values),
            "ready_for_development": self.ready_for_development,
        }


@dataclass(frozen=True, slots=True)
class CatalogSummary:
    graph_id: str
    title: str
    status: str
    case_count: int
    open_required_information: int
    p0_cases: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "title": self.title,
            "status": self.status,
            "case_count": self.case_count,
            "open_required_information": self.open_required_information,
            "p0_cases": self.p0_cases,
        }


class KnowledgeGraphCatalog:
    def __init__(self, repo_root: Path, source_path: Path, payload: dict[str, Any]) -> None:
        self.repo_root = repo_root
        self.source_path = source_path
        self.payload = payload

    @property
    def graph_id(self) -> str:
        return str(self.payload.get("graph_id", self.source_path.stem))

    @property
    def title(self) -> str:
        return str(self.payload.get("title", self.graph_id))

    @property
    def status(self) -> str:
        return str(self.payload.get("status", "unknown"))

    def case_summaries(self) -> list[CaseSummary]:
        return [self._case_summary(case) for case in self.payload.get("cases", [])]

    def summary(self) -> CatalogSummary:
        cases = self.case_summaries()
        return CatalogSummary(
            graph_id=self.graph_id,
            title=self.title,
            status=self.status,
            case_count=len(cases),
            open_required_information=sum(case.open_required_information for case in cases),
            p0_cases=sum(1 for case in cases if case.priority == "P0"),
        )

    def find_case(self, slug: str) -> CaseSummary | None:
        for case in self.case_summaries():
            if case.slug == slug:
                return case
        return None

    def _case_summary(self, case: dict[str, Any]) -> CaseSummary:
        required_information = _as_list(case.get("required_information"))
        open_items = [
            item
            for item in required_information
            if isinstance(item, dict) and item.get("status") == "open"
        ]
        first_open_questions = tuple(
            str(item.get("question", item.get("label", item.get("id", ""))))
            for item in open_items[:5]
        )
        non_empty_values = tuple(
            str(item.get("id", "<missing-id>"))
            for item in required_information
            if isinstance(item, dict) and item.get("value") not in EMPTY_VALUES
        )

        return CaseSummary(
            catalog_id=self.graph_id,
            case_id=str(case.get("id", "")),
            slug=str(case.get("slug", "")),
            title=str(case.get("title", "")),
            status=str(case.get("status", "unknown")),
            priority=str(case.get("priority", "P2")),
            usecase_path=str(case.get("usecase_path", "")),
            required_information=len(required_information),
            open_required_information=len(open_items),
            documents=len(_as_list(case.get("documents"))),
            decisions=len(_as_list(case.get("decisions"))),
            gates=len(_as_list(case.get("gates"))),
            evidence=len(_as_list(case.get("evidence"))),
            plugin_dependencies=tuple(str(item) for item in _as_list(case.get("plugin_dependencies"))),
            workflow_dependencies=tuple(str(item) for item in _as_list(case.get("workflow_dependencies"))),
            first_open_questions=first_open_questions,
            non_empty_values=non_empty_values,
        )


def load_catalogs(
    repo_root: Path,
    catalog_files: tuple[str, ...] | None = None,
) -> list[KnowledgeGraphCatalog]:
    catalogs: list[KnowledgeGraphCatalog] = []
    if catalog_files is None:
        paths = sorted(repo_root.glob(DEFAULT_CATALOG_GLOB))
    else:
        paths = [repo_root / relative_path for relative_path in catalog_files]

    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        catalogs.append(KnowledgeGraphCatalog(repo_root=repo_root, source_path=path, payload=payload))
    return catalogs


def all_case_summaries(catalogs: list[KnowledgeGraphCatalog]) -> list[CaseSummary]:
    cases: list[CaseSummary] = []
    for catalog in catalogs:
        cases.extend(catalog.case_summaries())
    return cases


def find_case(catalogs: list[KnowledgeGraphCatalog], slug: str) -> CaseSummary | None:
    for catalog in catalogs:
        summary = catalog.find_case(slug)
        if summary is not None:
            return summary
    return None


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []

