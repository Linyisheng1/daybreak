from fastapi import APIRouter, Depends, Query

from handler.poc.verifications import (
    delete_poc_handler,
    import_poc_handler,
    query_poc_runs_handler,
    query_pocs_handler,
    run_poc_handler,
)
from middleware.auth import AuthUser, require_user
from router.common.responses import BAD_REQUEST_RESPONSE, COMMON_ERROR_RESPONSES, not_found_response
from schema.common.responses import CommonResponse
from schema.poc.verifications import (
    ImportPocRequest,
    PocDefinitionSchema,
    PocRunSchema,
    QueryPocRunsResponse,
    QueryPocsResponse,
    RunPocRequest,
)


NOT_FOUND_RESPONSE = not_found_response("PoC")

router = APIRouter(
    prefix="/poc-verifications",
    tags=["poc-verifications"],
    dependencies=[Depends(require_user)],
)


async def import_poc_route(
    request: ImportPocRequest,
    user: AuthUser = Depends(require_user),
) -> CommonResponse[PocDefinitionSchema]:
    return await import_poc_handler(request, user)


async def query_pocs_route(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=100, ge=1, le=100),
    keyword: str = Query(default=""),
    severity: str = Query(default="", max_length=32),
    category: str = Query(default="", max_length=128),
) -> CommonResponse[QueryPocsResponse]:
    return await query_pocs_handler(
        page=page,
        size=size,
        keyword=keyword,
        severity=severity,
        category=category,
    )


async def delete_poc_route(id: int) -> CommonResponse:
    return await delete_poc_handler(id)


async def run_poc_route(
    id: int,
    request: RunPocRequest,
    user: AuthUser = Depends(require_user),
) -> CommonResponse[PocRunSchema]:
    return await run_poc_handler(id=id, request=request, user=user)


async def query_poc_runs_route(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=100),
    poc_id: int | None = Query(default=None, ge=1),
) -> CommonResponse[QueryPocRunsResponse]:
    return await query_poc_runs_handler(page=page, size=size, poc_id=poc_id)


router.add_api_route(
    "",
    query_pocs_route,
    methods=["GET"],
    response_model=CommonResponse[QueryPocsResponse],
    responses=COMMON_ERROR_RESPONSES,
)

router.add_api_route(
    "/import",
    import_poc_route,
    methods=["POST"],
    response_model=CommonResponse[PocDefinitionSchema],
    responses={**COMMON_ERROR_RESPONSES, **BAD_REQUEST_RESPONSE},
)

router.add_api_route(
    "/runs",
    query_poc_runs_route,
    methods=["GET"],
    response_model=CommonResponse[QueryPocRunsResponse],
    responses=COMMON_ERROR_RESPONSES,
)

router.add_api_route(
    "/{id}/run",
    run_poc_route,
    methods=["POST"],
    response_model=CommonResponse[PocRunSchema],
    responses={**COMMON_ERROR_RESPONSES, **BAD_REQUEST_RESPONSE, **NOT_FOUND_RESPONSE},
)

router.add_api_route(
    "/{id}",
    delete_poc_route,
    methods=["DELETE"],
    response_model=CommonResponse,
    responses={**COMMON_ERROR_RESPONSES, **NOT_FOUND_RESPONSE},
)
