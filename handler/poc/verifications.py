from http import HTTPStatus

from middleware.auth import AuthUser
from schema.common.responses import CommonResponse
from schema.poc.verifications import (
    ImportPocRequest,
    PocDefinitionSchema,
    QueryPocRunsResponse,
    QueryPocsResponse,
    RunPocRequest,
)
from service.common.pagination import paginated_payload
from service.poc.verifications import (
    PocExecutionError,
    PocValidationError,
    create_poc,
    delete_poc,
    parse_poc_document,
    query_poc_runs,
    query_pocs,
    run_poc,
)


async def import_poc_handler(request: ImportPocRequest, user: AuthUser) -> CommonResponse[PocDefinitionSchema]:
    try:
        parsed = parse_poc_document(request.content)
    except PocValidationError as exc:
        return CommonResponse(code=HTTPStatus.BAD_REQUEST.value, message=str(exc))
    poc = await create_poc(parsed, user_id=user.id)
    return CommonResponse(message="PoC imported", data=poc)


async def query_pocs_handler(
    page: int,
    size: int,
    keyword: str,
    severity: str,
    category: str,
) -> CommonResponse[QueryPocsResponse]:
    pocs = await query_pocs(
        page=page,
        size=size,
        keyword=keyword,
        severity=severity,
        category=category,
    )
    return CommonResponse(data=QueryPocsResponse(**paginated_payload(pocs, pocs.items)))


async def delete_poc_handler(id: int) -> CommonResponse:
    if not await delete_poc(id):
        return CommonResponse(code=HTTPStatus.NOT_FOUND.value, message="PoC not found")
    return CommonResponse(message="PoC deleted", data={"id": id})


async def run_poc_handler(id: int, request: RunPocRequest, user: AuthUser) -> CommonResponse:
    try:
        result = await run_poc(id, request, user_id=user.id, user_role=user.role)
    except PocExecutionError as exc:
        return CommonResponse(code=HTTPStatus.BAD_REQUEST.value, message=str(exc))
    if result is None:
        return CommonResponse(code=HTTPStatus.NOT_FOUND.value, message="PoC not found")
    return CommonResponse(message="PoC verification finished", data=result)


async def query_poc_runs_handler(
    page: int,
    size: int,
    poc_id: int | None,
) -> CommonResponse[QueryPocRunsResponse]:
    runs = await query_poc_runs(page=page, size=size, poc_id=poc_id)
    return CommonResponse(data=QueryPocRunsResponse(**paginated_payload(runs, runs.items)))
