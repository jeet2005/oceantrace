from uuid import UUID

from oceantrace_common.models import InvestigationResult


class InMemoryInvestigationRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, InvestigationResult] = {}

    def save(self, result: InvestigationResult) -> InvestigationResult:
        self._items[result.case.id] = result
        return result

    def get(self, case_id: UUID) -> InvestigationResult | None:
        return self._items.get(case_id)

    def list(self) -> list[InvestigationResult]:
        return sorted(self._items.values(), key=lambda result: result.case.created_at, reverse=True)


repository = InMemoryInvestigationRepository()

