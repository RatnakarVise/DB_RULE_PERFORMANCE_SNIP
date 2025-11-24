# app/schemas.py
from typing import List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict

# Payload structure (same as before, compatible with new format)
class PayloadItem(BaseModel):
    pgm_name: Optional[str] = None
    inc_name: Optional[str] = None
    type: Optional[str] = None
    name: Optional[str] = None
    class_implementations: Optional[Any] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    code: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
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
                        "ENDLOOP.\n"
                        "SELECT * FROM mara FOR ALL ENTRIES IN lt_tab WHERE matnr = lt_tab-matnr."
                    )
                }
            ]
        }
    )


# Final-format finding (Credit Master style)
class Finding(BaseModel):
    prog_name: Optional[str] = None
    incl_name: Optional[str] = None
    types: Optional[str] = None
    blockname: Optional[str] = None
    starting_line: int = 0
    ending_line: int = 0
    issues_type: str = "PerformanceIssue"
    severity: str = "warning"
    message: str
    suggestion: str
    snippet: str


class ResponseItem(BaseModel):
    pgm_name: Optional[str] = None
    inc_name: Optional[str] = None
    type: Optional[str] = None
    name: Optional[str] = None
    code: Optional[str] = None
    findings: List[Finding] = Field(default_factory=list)
