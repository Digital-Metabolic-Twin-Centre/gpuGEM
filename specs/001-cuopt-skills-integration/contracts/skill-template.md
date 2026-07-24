# cuOpt Skill Template (Contract)

**Purpose**: Canonical template for all cuOpt Claude Code skills  
**Version**: 1.0.0  
**Status**: Normative (all skills MUST conform to this structure)

---

# [SKILL TITLE]

> **Skill ID**: `cuopt-[domain-name]`  
> **Category**: [setup|concepts|api-reference|deployment|advanced]  
> **Difficulty**: [beginner|intermediate|advanced]  
> **Time**: [15|20|30|45] minutes  
> **Prerequisites**: [cuopt-install], [list other prerequisite skills]

---

## Overview

[1–2 sentence summary of what this skill covers and who should use it]

**Target Audience**: [e.g., "Python developers new to optimization", "DevOps teams deploying cuOpt", "researchers exploring multi-objective tradeoffs"]

---

## Concepts

[Explanation of key ideas WITHOUT code. Introduce vocabulary, explain mental models, provide intuition.]

### Key Idea 1: [Concept Name]

[Paragraph explaining the concept, why it matters, how it relates to cuOpt]

**Example scenario**: [Brief narrative showing when/why this concept applies]

### Key Idea 2: [Concept Name]

[Similar structure...]

---

## API Reference

[For API-reference skills ONLY. Skip for conceptual skills.]

### Function/Method 1: `function_name(param1, param2, ...)`

**Purpose**: [1–2 sentence description of what this does]

**Signature**:
```
function_name(
    param1: Type,
    param2: Type = default_value,
    ...
) → ReturnType
```

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `param1` | `int` | Yes | Description of param1 |
| `param2` | `str` | No | Description of param2; default: `"default_value"` |

**Returns**: 

`ReturnType` — Description of what is returned and how to interpret it.

**Raises**:

- `ExceptionType`: Raised when [condition]; resolution: [how to handle]
- `OtherException`: Raised when [condition]

**Typical Usage**:

```python
result = function_name(param1=value1, param2=value2)
# Returns result of type ReturnType
```

**See Also**: [Related functions, skills, or documentation links]

---

### Function/Method 2: `another_function(...)`

[Repeat structure above for each API function]

---

## Examples

### Example 1: [Title]

**What you'll learn**: [1–2 sentence description]

**Prerequisites**: [Tools/libraries/knowledge needed: "numpy", "basic Python", etc.]

**Time**: [5–10 minutes]

**Code**:

```python
[10–50 lines of executable, runnable Python code]
```

**What's Happening**:

[Line-by-line or block-by-block explanation of the code, highlighting key points]

**Expected Output**:

```
[Sample output the user should see when running]
```

**Try This Variation**: [Suggestion for how to modify the example to explore further, e.g., "Change the objective from minimization to maximization"]

---

### Example 2: [Title]

[Repeat structure above for each example]

---

## Common Patterns

### Pattern 1: [Problem/Use Case]

**Scenario**: [When you'd use this pattern]

**Solution**:

```python
[Brief code snippet showing the pattern]
```

**Why This Works**: [Explanation]

### Pattern 2: [Problem/Use Case]

[Repeat structure above]

---

## Known Limitations

[Document cuOpt-specific quirks, solver bugs, unsupported features, and workarounds]

### Limitation 1: [Issue Name]

**Affected Versions**: cuOpt [0.4.x|0.3.x|all]

**What Happens**: [Describe the issue: e.g., "Presolve declares feasible problems as infeasible"]

**Why**: [Brief explanation of root cause]

**Workaround**: [How to work around it, or "No workaround; use alternative API"]

**Status**: [Open in cuOpt repository|Closed as of version X.Y.Z|Not fixed]

**Reference**: [Link to cuOpt GitHub issue or documentation]

### Limitation 2: [Issue Name]

[Repeat structure above]

---

## Next Steps

[Pointers to follow-on skills, advanced topics, or related domains]

- **For [specific use case]**: See [skill-name] to learn about [topic]
- **To go deeper**: Explore [cuOpt official documentation link]
- **Related skill**: Try [other-skill-name] to [learn about|practice]

---

## See Also

- [Link to gpuGEM documentation]
- [Link to cuOpt official API documentation]
- [Link to related Claude Code skills]

---

## Glossary

[Optional: Define terms specific to this skill that might not be obvious]

| Term | Definition |
|------|-----------|
| **[Term]** | [Definition] |

---

## Skill Metadata

**Last Updated**: [YYYY-MM-DD]  
**Author(s)**: [Claude Code Team]  
**Status**: [draft|published|deprecated]  
**Version**: 1.0.0  
**Feedback**: [Link to feedback/issue tracking for this skill]

---

## Template Notes

- **Mandatory Sections**: Overview, Concepts, Examples, Known Limitations, Next Steps
- **Conditional Sections**: API Reference (required only for API-reference category skills)
- **Optional Sections**: See Also, Glossary, Skill Metadata
- **Code Style**: All Python code must be PEP 8 compliant; examples must be runnable standalone
- **Example Validation**: Every example must include result validation (e.g., checking solver status and feasibility) per gpuGEM constitution
- **Cross-References**: Use relative links to other skills when possible; use full URLs for external resources
