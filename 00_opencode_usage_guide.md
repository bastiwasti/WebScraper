# OpenCode CLI Guide for WebScraper URL Setup

**Purpose:** Use opencode CLI to run URL setup agent headlessly

---

## Overview

OpenCode is a powerful CLI that supports **agents** - AI assistants with tools, system prompts, and custom configurations.

**Best Approach:** Create a custom agent or use `opencode run` directly with your prompt

---

## Primary Command

### Option 1: Direct Run (RECOMMENDED)

```bash
# Run with your prompt directly
opencode run "YOUR_PROMPT_HERE"
```

**Pros:**
- Simple and direct
- No agent configuration needed
- Immediate execution
- Can attach files with `--file` flag

**Example:**
```bash
opencode run --file docs/00_url_setup_prompt.md \
  "User provides URL: https://www.duesseldorf.de/veranstaltungen, City: duesseldorf. Read docs/00_url_setup_prompt.md and implement following the workflow."
```

### Option 2: Create Custom Agent

If you need more advanced control:

```bash
# Create a WebScraper-specific agent
opencode agent create webscraper-setup

# The agent can have:
# - System prompt referencing docs
# - Tool access (Read, Write, Bash, Edit, Glob, Grep)
# - File attachments
```

**Pros:**
- Reusable for multiple URL setups
- Can reference documentation directly
- Configurable tools and permissions

**Cons:**
- Requires agent creation upfront
- More complex initial setup

---

## Key Flags

| Flag | Description | Example |
|-------|-------------|----------|
| `--file` | Attach file(s) to message | `opencode run --file prompt.md` |
| `--agent` | Use specific agent | `opencode run --agent webscraper-setup` |
| `--format` | Output format (default/json) | `opencode run --format json` |
| `--share` | Share session with team | `opencode run --share` |
| `--session` | Continue from previous session | `opencode run --session abc123` |

---

## Recommended Workflow for WebScraper

### Step 1: Prepare Your Prompt

**Option A: Reference Documentation File**
```bash
opencode run \
  --file docs/00_url_setup_prompt.md \
  "Read the setup guide at docs/00_url_setup_prompt.md and implement the workflow for WebScraper. User will provide: Full URL and City Name."
```

**Option B: Include Full Instructions**
```bash
opencode run \
  "Implement a new event scraper for WebScraper codebase.

## Context
You are working on the WebScraper project in /home/vscode/projects/WebScraper.

## Task
Create a new URL scraper for a user-provided URL and city name.

## Required Input
User will provide:
1. Full URL: Complete event calendar URL
2. City Name: City name (lowercase, no spaces)

## Your Workflow
1. Read docs/00_url_setup_prompt.md for setup instructions
2. Read 14_categories.md for category system reference
3. Analyze the URL to detect which of 7 proven patterns to use:
   - Pattern 1: REST API (JSON)
   - Pattern 2: Static HTML (Basic)
   - Pattern 3: Static HTML + 2-Level
   - Pattern 4: Dynamic HTML + Load More
   - Pattern 5: Static HTML + Pagination
   - Pattern 6: 2-Level with URL Extraction
   - Pattern 7: Custom HTML Parsing
4. Implement scraper using matching template from rules/cities/ directory
5. Register URL in rules/urls.py
6. Test with: python3 main.py --url {target_url} --no-db --verbose
7. Fix issues with up to 3 self-correction attempts
8. Create summary file: 2x_{city}_autonomous_{timestamp}.md

## Implementation Rules
- Each URL gets own subfolder: rules/cities/{city}/{subfolder}/
- Class names: {SubfolderName}Scraper and {SubfolderName}Regex
- Import: from rules import categories, utils
- Use categories.infer_category() for categorization
- Use categories.normalize_category() for normalization
- Use utils.normalize_date() for date normalization
- Use utils.normalize_time() for time normalization
- Set needs_browser property correctly
- Register URL in rules/urls.py

## Required Event Fields
- name (required): Event title
- description (required): Event description
- location (required): Venue/address
- date (required): DD.MM.YYYY format
- time (required): HH:MM format
- source (required): Source URL
- category (inferred): Use category system
- event_url (optional): Detail page URL
- end_time (optional): End time if available
- raw_data (optional): Level 2 data

## Testing
Test 1: Module imports - python3 -c 'from rules import categories, utils'
Test 2: Single URL - python3 main.py --url {url} --no-db --verbose
Verify: events extracted count > 0, all required fields present

## Self-Correction
Maximum 3 attempts. For each:
1. Diagnose issue from error output
2. Apply appropriate fix (selector issues, date parsing, pagination, timeout)
3. Retest and verify

## Summary File
After completion, create summary file:
Filename: 2x_{city}_autonomous_{timestamp}.md
Timestamp format: YYYY-MM-DDTHH:MM:SS

Include:
- Task information
- Implementation details
- Testing results
- Self-correction attempts (up to 3)
- Issues encountered (table format)
- Final status (SUCCESS/FAILED)
- Recommendations

## Output
Report summary file path and final status."
```

### Step 2: Run the Command

```bash
# Execute the setup
opencode run --file docs/00_url_setup_prompt.md "YOUR_COMPLETE_PROMPT_FROM_STEP_1"
```

**Or for Option A (just referencing docs):**

```bash
# Simple execution with doc reference
opencode run \
  "Implement WebScraper URL setup for URL: https://www.duesseldorf.de/veranstaltungen, City: duesseldorf. 
   Follow workflow in docs/00_url_setup_prompt.md."
```

---

## Advanced Options

### Attach Multiple Files

```bash
# Attach all documentation
opencode run \
  --file docs/00_url_setup_prompt.md \
  --file 14_categories.md \
  --file 01_setup_guide.md \
  "Implement WebScraper scraper following documentation."
```

### Custom Agent Approach

```bash
# Create dedicated agent
opencode agent create webscraper-url-setup

# Use the agent
opencode run --agent webscraper-url-setup "YOUR_PROMPT"
```

---

## Session Management

### Share Session

```bash
# Share with team for review
opencode run --share "Implement WebScraper scraper..."
```

### Continue from Previous Session

```bash
# List sessions
opencode session list

# Continue from session
opencode run --session SESSION_ID "Continue the task..."
```

---

## Troubleshooting

### Agent Not Found

```bash
# List available agents
opencode agent list

# Check if custom agent exists
# If using custom agent, verify it was created successfully
```

### File Access Issues

```bash
# Check working directory
pwd
ls docs/

# If agent can't access files:
# 1. Ensure you're in correct directory: /home/vscode/projects/WebScraper
# 2. Verify file exists: ls -la docs/00_url_setup_prompt.md
# 3. Use absolute paths if needed
```

---

## Best Practices

### For Reliability

1. **Reference Documentation**
   - Always point to existing docs files
   - Don't duplicate information
   - Leverage 11,000+ lines of existing documentation

2. **Use File Attachments**
   - Attach key docs with `--file` flag
   - Reduces prompt size
   - Ensures documentation is current

3. **Clear Workflow Steps**
   - Numbered steps (1, 2, 3, etc.)
   - Clear start and end conditions
   - Verification points after each step

4. **Specific File Names and Paths**
   - Use absolute paths for clarity
   - Reference specific files (not "the documentation")

### For Efficiency

1. **Keep Prompts Concise**
   - Reference docs instead of repeating everything
   - Focus on workflow, not re-explaining existing docs

2. **Leverage Agent Capabilities**
   - Use Read tool to inspect code
   - Use Grep tool to find patterns
   - Use Edit tool to make changes
   - Use Bash tool to run tests

3. **Test Before Full Run**
   - Test individual steps
   - Verify file access
   - Check imports work

---

## Quick Reference

| Task | Command |
|-------|----------|
| **Run with file attachment** | `opencode run --file docs/00_url_setup_prompt.md "PROMPT"` |
| **Simple doc reference** | `opencode run "Follow docs/00_url_setup_prompt.md for URL setup"` |
| **List available agents** | `opencode agent list` |
| **List sessions** | `opencode session list` |
| **Share session** | `opencode run --share "TASK"` |

---

## Summary

**Recommended Approach:** Use `opencode run` with file attachments

**Benefits:**
- Simple and direct
- Leverages existing documentation
- No agent configuration needed
- Can attach multiple documentation files
- Supports session management

**Time Estimate:** 30-60 minutes for typical URL setup

**Documentation Reference:** 
- Primary guide: `docs/00_url_setup_prompt.md` (129 lines)
- Category system: `14_categories.md` (480 lines)
- Detailed setup: `01_setup_guide.md` (1,800 lines)

---

