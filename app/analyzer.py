# app/analyzer.py
import re
from typing import List, Dict, Any, Tuple, Optional

# Regex patterns (case-insensitive, deterministic)
RE_LOOP_START = re.compile(r'^\s*LOOP\b', re.IGNORECASE)
RE_DO_START = re.compile(r'^\s*DO\b', re.IGNORECASE)
RE_WHILE_START = re.compile(r'^\s*WHILE\b', re.IGNORECASE)

RE_ENDLOOP = re.compile(r'^\s*ENDLOOP\b', re.IGNORECASE)
RE_ENDDO = re.compile(r'^\s*ENDDO\b', re.IGNORECASE)
RE_ENDWHILE = re.compile(r'^\s*ENDWHILE\b', re.IGNORECASE)

# SELECT statements, but not SELECT-OPTIONS (selection screen)
RE_SELECT_SQL = re.compile(r'^\s*SELECT(?!-OPTIONS)\b', re.IGNORECASE)

# FOR ALL ENTRIES pattern
RE_FOR_ALL_ENTRIES = re.compile(r'\bFOR\s+ALL\s+ENTRIES\s+IN\b', re.IGNORECASE)

SUGGEST_NESTED_LOOPS = "avoid nested loop for performance optimization."
SUGGEST_SELECT_IN_LOOP = "avoid select inside loop for performance optimization."
SUGGEST_FOR_ALL_ENTRIES = "avoid select with for all entries , with relevant select on Join condition."


def strip_abab_line_comments(line: str) -> str:
    if line.lstrip().startswith("*"):
        return ""
    quote_idx = line.find('"')
    if quote_idx != -1:
        return line[:quote_idx]
    return line


def normalize_newlines(text: str) -> str:
    return (text or "").replace("\r\n", "\n").replace("\r", "\n")


def build_lines(code: str) -> List[Dict[str, Any]]:
    code = normalize_newlines(code or "")
    lines = code.split("\n")
    result = []
    for i, raw in enumerate(lines, start=1):
        clean = strip_abab_line_comments(raw)
        result.append({"no": i, "raw": raw, "clean": clean})
    return result


def is_loop_start(text: str) -> Optional[str]:
    if RE_LOOP_START.match(text):
        return "LOOP"
    if RE_DO_START.match(text):
        return "DO"
    if RE_WHILE_START.match(text):
        return "WHILE"
    return None


def is_loop_end(text: str) -> Optional[str]:
    if RE_ENDLOOP.match(text):
        return "LOOP"
    if RE_ENDDO.match(text):
        return "DO"
    if RE_ENDWHILE.match(text):
        return "WHILE"
    return None


def find_matching_end(lines: List[Dict[str, Any]], start_idx: int, block_type: str) -> Optional[int]:
    depth = 1
    for i in range(start_idx + 1, len(lines)):
        clean = lines[i]["clean"]
        if not clean.strip():
            continue
        if is_loop_start(clean) == block_type:
            depth += 1
        elif is_loop_end(clean) == block_type:
            depth -= 1
            if depth == 0:
                return i
    return None


def collect_loop_blocks(lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    blocks = []
    stack: List[Tuple[str, int]] = []
    for idx, ld in enumerate(lines):
        clean = ld["clean"]
        if not clean.strip():
            continue
        start_type = is_loop_start(clean)
        end_type = is_loop_end(clean)
        if start_type:
            stack.append((start_type, idx))
        elif end_type:
            for s in range(len(stack) - 1, -1, -1):
                t, sidx = stack[s]
                if t == end_type:
                    end_idx = idx
                    blocks.append({"type": t, "start_idx": sidx, "end_idx": end_idx})
                    stack = stack[:s]
                    break
    blocks.sort(key=lambda b: b["start_idx"])
    return blocks


def find_nested_loops(lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Same core logic as original: detect nested LOOP/DO/WHILE.
    Now we also record line number from inner_start_idx (metadata only).
    """
    findings = []
    stack: List[Tuple[str, int]] = []
    for idx, ld in enumerate(lines):
        text = ld["clean"]
        if not text.strip():
            continue
        stype = is_loop_start(text)
        etype = is_loop_end(text)
        if stype:
            # Nested loop if we already have one on stack
            if any(t in ("LOOP", "DO", "WHILE") for (t, _) in stack):
                inner_start_idx = idx
                inner_end_idx = find_matching_end(lines, inner_start_idx, stype)
                snippet_lines = []
                if inner_end_idx is not None:
                    end_clip = min(inner_end_idx, inner_start_idx + 11)
                    for j in range(inner_start_idx, end_clip + 1):
                        snippet_lines.append(lines[j]["raw"])
                else:
                    end_clip = min(len(lines) - 1, inner_start_idx + 5)
                    for j in range(inner_start_idx, end_clip + 1):
                        snippet_lines.append(lines[j]["raw"])

                findings.append({
                    "suggestion": SUGGEST_NESTED_LOOPS,
                    "snippet": "\n".join(snippet_lines).strip(),
                    "line": lines[inner_start_idx]["no"],
                })
            stack.append((stype, idx))
        elif etype:
            for s in range(len(stack) - 1, -1, -1):
                t, _ = stack[s]
                if t == etype:
                    stack = stack[:s]
                    break
    return findings


def find_select_inside_loops(lines: List[Dict[str, Any]], loop_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Same logic as original: detect SELECT inside any loop block.
    Now we attach line number of SELECT line.
    """
    findings = []
    for block in loop_blocks:
        sidx = block["start_idx"]
        eidx = block["end_idx"]
        loop_header = lines[sidx]["raw"].strip()
        reported_line_nos = set()
        for i in range(sidx + 1, eidx + 1):
            clean = lines[i]["clean"]
            if RE_SELECT_SQL.match(clean):
                line_no = lines[i]["no"]
                if line_no in reported_line_nos:
                    continue
                reported_line_nos.add(line_no)
                select_line = lines[i]["raw"].strip()
                snippet = f"{loop_header}\n{select_line}"
                findings.append({
                    "suggestion": SUGGEST_SELECT_IN_LOOP,
                    "snippet": snippet,
                    "line": line_no,
                })
    return findings


def find_for_all_entries(lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Same logic: detect FOR ALL ENTRIES.
    Now we also keep line number of the FOR ALL ENTRIES occurrence.
    """
    findings = []
    for i, ld in enumerate(lines):
        clean = ld["clean"]
        if RE_FOR_ALL_ENTRIES.search(clean):
            start = max(0, i - 1)
            end = min(len(lines) - 1, i + 1)
            snippet_lines = [lines[j]["raw"] for j in range(start, end + 1)]
            findings.append({
                "suggestion": SUGGEST_FOR_ALL_ENTRIES,
                "snippet": "\n".join(snippet_lines).strip(),
                "line": lines[i]["no"],
            })
    return findings


def analyze_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Core logic: unchanged detection, only response shape adapted
    to the Credit Master 'final format' style.
    """
    code = item.get("code", "") or ""
    lines = build_lines(code)

    raw_findings: List[Dict[str, Any]] = []
    raw_findings.extend(find_nested_loops(lines))
    loop_blocks = collect_loop_blocks(lines)
    raw_findings.extend(find_select_inside_loops(lines, loop_blocks))
    raw_findings.extend(find_for_all_entries(lines))

    # Build final-format response
    findings_final: List[Dict[str, Any]] = []
    for f in raw_findings:
        line_no = f.get("line", 0) or 0
        findings_final.append({
            "prog_name": item.get("pgm_name"),
            "incl_name": item.get("inc_name"),
            "types": item.get("type"),
            "blockname": item.get("name"),
            "starting_line": line_no,
            "ending_line": line_no,
            "issues_type": "PerformanceIssue",          # fixed type label
            "severity": "warning",                      # as per your pattern
            "message": f"Performance issue: {f['suggestion']}",
            "suggestion": f["suggestion"],
            "snippet": f["snippet"],
        })

    return {
        "pgm_name": item.get("pgm_name"),
        "inc_name": item.get("inc_name"),
        "type": item.get("type"),
        "name": item.get("name"),
        "code": code,
        "findings": findings_final,
    }
