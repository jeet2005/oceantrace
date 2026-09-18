from oceantrace_common.models import InvestigationResult


def build_demo_investigation(case_number: str = "OT-2026-0001") -> InvestigationResult:
    from oceantrace_api.services.pipeline_service import InvestigationPipelineService

    return InvestigationPipelineService().run_demo(case_number)
