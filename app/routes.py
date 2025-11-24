# app/routes.py
from typing import List
from fastapi import APIRouter
from app.schemas import PayloadItem, ResponseItem
from app.analyzer import analyze_item

router = APIRouter()

example_request = [
    {
        "pgm_name": "Z_DEMO",
        "inc_name": "Z_INC",
        "type": "PROG",
        "name": "MAIN",
        "class_implementations": [],
        "start_line": 1,
        "end_line": 999,
        "code": (
            "LOOP AT lt_tab INTO ls_tab.\n"
            "  SELECT * FROM mara INTO TABLE lt_mara WHERE matnr = ls_tab-matnr.\n"
            "  LOOP AT lt_inner INTO ls_inner.\n"
            "    WHILE sy-index < 10.\n"
            "      DO 5 TIMES.\n"
            "      ENDDO.\n"
            "    ENDWHILE.\n"
            "  ENDLOOP.\n"
            "ENDLOOP.\n"
            "SELECT * FROM mara FOR ALL ENTRIES IN lt_tab WHERE matnr = lt_tab-matnr."
        )
    }
]

# Final-format style: two endpoints, /remediate and /remediate-array

@router.post(
    "/remediate-array",
    response_model=List[ResponseItem],
    summary="Analyze ABAP code for performance issues (array)",
    description="Accepts an array of payload objects and returns an array with findings for each item.",
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "examples": {
                        "sample": {
                            "summary": "Sample ABAP analysis request",
                            "value": example_request
                        }
                    }
                }
            }
        }
    },
)
async def remediate_array(payload: List[PayloadItem]) -> List[ResponseItem]:
    results: List[ResponseItem] = []
    for item in payload:
        analyzed_dict = analyze_item(item.model_dump())
        results.append(ResponseItem(**analyzed_dict))
    return results


@router.post(
    "/remediate",
    response_model=List[ResponseItem],
    summary="Analyze a single ABAP unit for performance issues",
    description="Accepts a single payload object and returns findings wrapped in a list (for consistency).",
)
async def remediate_single(item: PayloadItem) -> List[ResponseItem]:
    analyzed_dict = analyze_item(item.model_dump())
    return [ResponseItem(**analyzed_dict)]
