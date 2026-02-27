# Agent Error Log

*Historical errors encountered during development and their solutions. Use the patterns section at the bottom to prevent recurring issues.*

---

## Resolved Errors Summary

| # | Date | Error | Root Cause | Status |
|---|------|-------|------------|--------|
| 002 | 2026-02-06 | Regex not matching event blocks | Pattern too restrictive for markdown-wrapped JSON; capture broadly then clean | Resolved |
| 003 | 2026-02-06 | TypeError with None in category inference | `description` was None from LLM fallback; added `description = description or ""` | Resolved |
| 004 | 2026-02-06 | LSP type errors for optional params | Type hints said `int` but default was `None`; changed to `int \| None` | Resolved |
| 005 | 2026-02-06 | LLM timeout on large prompts (Langenfeld) | No explicit timeout + no chunking; added 600s timeout + adaptive chunking + pre-structured extraction bypass | Resolved |
| 007 | 2026-02-06 | LangChain api_key type error | ChatOpenAI expects SecretStr, not str; wrapped in `lambda: DEEPSEEK_API_KEY` | Resolved |
| 008 | 2026-02-06 | Pipeline import error | Added function to storage.py with indentation issues; reverted and fixed imports | Resolved |
| 009 | 2026-02-06 | Storage module indentation/type errors | Debug code mixed into critical functions; reverted to clean state | Resolved |
| 010 | 2026-02-06 | Full run event loss (91% data loss) | Dict reference issues in event normalization pipeline; fixed all 4 bugs in data flow | Resolved |
| 011 | 2026-02-06 | Silent event loss in DB insert | LLM path missing normalization + wrong variable in extend + missing city in get_events + missing INSERT placeholder | Resolved |
| 012 | 2026-02-06 | Positional vs keyword argument bug | `_infer_category()` called with positional args instead of keyword args | Resolved |
| 013 | 2026-02-06 | LLM path missing normalization | LLM analysis path didn't call `_normalize_field_names()` or `_infer_category()` | Resolved |
| 014 | 2026-02-06 | SQLite 11 values for 10 columns | Missing placeholder for `created_at` in INSERT statement | Resolved |

---

## Open Error: City Field Data Quality

**Error #008 (original)** — Events extracted with correct city field, but saved to database with empty city field.

- **Files**: `agents/analyzer_agent.py`, `storage.py`
- **Symptoms**: Debug output shows `"City: hilden"` during processing, but database shows empty city field after save
- **Impact**: Data quality issue only — events are saved and functional, but lack city metadata
- **Status**: **NOT FULLY RESOLVED** — may be a dict reference or SQL parameter mismatch issue
- **Workaround**: City information is available in the `source` URL and `origin` field

---

## General Patterns and Prevention Strategies

### Pattern 1: Type Mismatches with LangChain
**Prevention**:
- Always check ChatOpenAI parameter types
- Use lambda wrappers for sensitive parameters: `api_key=lambda: KEY`
- Set type hints as `Type | None` if default is None

### Pattern 2: Regex Matching Failures
**Prevention**:
- Test regex patterns with actual sample data
- Capture broadly, then clean (better than precise matching)
- Handle markdown code fences in LLM output
- Print input when regex fails for debugging

### Pattern 3: None Value Handling
**Prevention**:
- Add `| None` to type hints for optional parameters
- Use `x or ""` idiom for None/empty string defaults
- Validate external input even from internal sources

### Pattern 4: LLM Timeout and Performance
**Prevention**:
- Always set explicit timeout (600s+ for large prompts)
- Check for redundant processing in data flow
- Implement adaptive chunking (event count + char limit)
- Detect and use pre-structured data to bypass LLM

### Pattern 5: Data Flow Verification
**Prevention**:
- When events pass through multiple transformations, verify each step
- Console debug output is not sufficient — check database values directly
- Test full-run mode separately from individual city tests

---

## Future Checklist

Before making changes, check this log for:
- [ ] LangChain type patterns (#007)
- [ ] Regex testing strategy (#002)
- [ ] None value handling (#003, #004)
- [ ] Timeout configuration (#005)
- [ ] Data flow verification (#010, #011)

**Remember**: When in doubt, read the code first, test locally, then implement.
