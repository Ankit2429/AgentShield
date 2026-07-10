"""Default threat-detection rules for the AgentShield Detection Engine.

Each :class:`~app.core.models.ThreatRule` in :data:`DEFAULT_RULES` maps a
compiled-ready regex pattern to a semantic category, a human-readable name,
a short description, and a :class:`~app.core.severity.Severity` level.

Rules are intentionally broad: they are designed to flag *suspicious* patterns
early and pass context to human reviewers or downstream mitigation logic.
False-positive rates should be tuned per deployment environment.

Categories
----------
command_injection
    Shell meta-characters and destructive commands that could be embedded in
    agent-to-agent messages to hijack execution.
prompt_injection
    Natural-language instructions that attempt to override an LLM's system
    prompt or safety guidelines.
sql_injection
    SQL syntax fragments that may indicate attempts to manipulate database
    queries.
path_traversal
    Directory-traversal sequences that can expose files outside the intended
    working directory.
code_execution
    Python / OS-level constructs that would execute arbitrary code if evaluated.
network_exfiltration
    Network utility invocations that may leak data to external endpoints.
"""

from __future__ import annotations

from app.core.models import ThreatRule
from app.core.severity import Severity

# ---------------------------------------------------------------------------
# Command Injection
# ---------------------------------------------------------------------------
_CMD_INJECTION_RULES: list[ThreatRule] = [
    ThreatRule(
        pattern=r"(?:^|[^&|;])\s*;\s*\w",
        name="Shell Statement Separator",
        description=(
            "Semicolons can chain shell commands, allowing an attacker to "
            "append arbitrary commands to a benign-looking instruction."
        ),
        category="command_injection",
        severity=Severity.HIGH,
    ),
    ThreatRule(
        pattern=r"&&",
        name="Shell AND Operator",
        description=(
            "The '&&' operator chains commands conditionally, enabling command "
            "injection if the first command succeeds."
        ),
        category="command_injection",
        severity=Severity.HIGH,
    ),
    ThreatRule(
        pattern=r"\|\|",
        name="Shell OR Operator",
        description=(
            "The '||' operator chains commands, executing the second if the "
            "first fails — a common injection vector."
        ),
        category="command_injection",
        severity=Severity.HIGH,
    ),
    ThreatRule(
        pattern=r"\brm\s+-rf\b",
        name="Destructive Remove Command",
        description=(
            "'rm -rf' recursively deletes files without confirmation.  Its "
            "presence in any agent message is almost certainly malicious."
        ),
        category="command_injection",
        severity=Severity.CRITICAL,
    ),
]

# ---------------------------------------------------------------------------
# Prompt Injection
# ---------------------------------------------------------------------------
_PROMPT_INJECTION_RULES: list[ThreatRule] = [
    ThreatRule(
        pattern=r"ignore\s+(?:all\s+)?previous\s+instructions?",
        name="Ignore Previous Instructions",
        description=(
            "Classic prompt-injection phrasing attempting to override the "
            "model's existing instructions."
        ),
        category="prompt_injection",
        severity=Severity.CRITICAL,
    ),
    ThreatRule(
        pattern=r"reveal\s+(?:your\s+)?(?:system\s+prompt|instructions?|prompt)",
        name="System Prompt Extraction",
        description=(
            "Attempts to make the model disclose its system prompt or internal "
            "instructions to an unauthorised party."
        ),
        category="prompt_injection",
        severity=Severity.HIGH,
    ),
    ThreatRule(
        pattern=r"bypass\s+(?:safety|filters?|restrictions?|guardrails?)",
        name="Safety Bypass Attempt",
        description=(
            "Explicit request to circumvent safety filters or content "
            "restrictions imposed on the model."
        ),
        category="prompt_injection",
        severity=Severity.CRITICAL,
    ),
    ThreatRule(
        pattern=r"forget\s+(?:all\s+)?(?:your\s+)?(?:previous\s+)?instructions?",
        name="Forget Instructions",
        description=(
            "Instructs the model to discard its configured behaviour, "
            "effectively attempting a context reset."
        ),
        category="prompt_injection",
        severity=Severity.HIGH,
    ),
    ThreatRule(
        pattern=r"act\s+as\s+(?:a\s+)?(?:system|root|admin|superuser|god|unrestricted)",
        name="Privileged Role Assumption",
        description=(
            "Attempts to make the model behave as if it has elevated or "
            "unrestricted system-level privileges."
        ),
        category="prompt_injection",
        severity=Severity.HIGH,
    ),
]

# ---------------------------------------------------------------------------
# SQL Injection
# ---------------------------------------------------------------------------
_SQL_INJECTION_RULES: list[ThreatRule] = [
    ThreatRule(
        pattern=r"\bDROP\s+TABLE\b",
        name="DROP TABLE Statement",
        description=(
            "Destructive SQL statement that permanently removes a database "
            "table and all its data."
        ),
        category="sql_injection",
        severity=Severity.CRITICAL,
    ),
    ThreatRule(
        pattern=r"\bUNION\s+(?:ALL\s+)?SELECT\b",
        name="UNION SELECT Injection",
        description=(
            "UNION-based SQL injection that appends a second SELECT to exfiltrate "
            "data from arbitrary tables."
        ),
        category="sql_injection",
        severity=Severity.CRITICAL,
    ),
    ThreatRule(
        pattern=r"(?:'|\b)\s*OR\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+['\"]?",
        name="OR Tautology Injection",
        description=(
            "Classic tautology pattern (e.g. OR 1=1) used to force a WHERE "
            "clause to always evaluate as true."
        ),
        category="sql_injection",
        severity=Severity.HIGH,
    ),
    ThreatRule(
        pattern=r"\bINSERT\s+INTO\b",
        name="INSERT INTO Statement",
        description=(
            "SQL INSERT command that may be injected to write arbitrary records "
            "into the database."
        ),
        category="sql_injection",
        severity=Severity.MEDIUM,
    ),
    ThreatRule(
        pattern=r"\bDELETE\s+FROM\b",
        name="DELETE FROM Statement",
        description=(
            "SQL DELETE command that can erase rows from a table; dangerous "
            "without a validated WHERE clause."
        ),
        category="sql_injection",
        severity=Severity.HIGH,
    ),
]

# ---------------------------------------------------------------------------
# Path Traversal
# ---------------------------------------------------------------------------
_PATH_TRAVERSAL_RULES: list[ThreatRule] = [
    ThreatRule(
        pattern=r"\.\./",
        name="Unix Path Traversal (../)",
        description=(
            "Directory traversal sequence for Unix-like systems that climbs "
            "the directory tree to access restricted files."
        ),
        category="path_traversal",
        severity=Severity.HIGH,
    ),
    ThreatRule(
        pattern=r"\.\.[/\\\\]",
        name="Windows Path Traversal (..\\ or ../)",
        description=(
            "Directory traversal sequence targeting Windows file paths to "
            "escape the intended working directory."
        ),
        category="path_traversal",
        severity=Severity.HIGH,
    ),
    ThreatRule(
        pattern=r"/etc/passwd",
        name="Unix Password File Access",
        description=(
            "Direct reference to /etc/passwd, a sensitive file containing "
            "system user information on Unix-like systems."
        ),
        category="path_traversal",
        severity=Severity.CRITICAL,
    ),
    ThreatRule(
        pattern=r"[Ww]indows[/\\\\][Ss]ystem32",
        name="Windows System32 Directory Access",
        description=(
            "Reference to the Windows System32 directory, which contains "
            "critical OS binaries and is a common exfiltration target."
        ),
        category="path_traversal",
        severity=Severity.HIGH,
    ),
]

# ---------------------------------------------------------------------------
# Code Execution
# ---------------------------------------------------------------------------
_CODE_EXECUTION_RULES: list[ThreatRule] = [
    ThreatRule(
        pattern=r"\beval\s*\(",
        name="eval() Call",
        description=(
            "eval() executes a string as code at runtime, providing a direct "
            "vector for arbitrary code execution."
        ),
        category="code_execution",
        severity=Severity.CRITICAL,
    ),
    ThreatRule(
        pattern=r"\bexec\s*\(",
        name="exec() Call",
        description=(
            "exec() executes dynamically constructed Python code objects or "
            "strings, enabling arbitrary code execution."
        ),
        category="code_execution",
        severity=Severity.CRITICAL,
    ),
    ThreatRule(
        pattern=r"\bpython(?:3)?\s+-c\b",
        name="Python Inline Command (-c flag)",
        description=(
            "The -c flag executes a Python expression directly from the "
            "command line, bypassing script-based controls."
        ),
        category="code_execution",
        severity=Severity.CRITICAL,
    ),
    ThreatRule(
        pattern=r"\bos\.system\s*\(",
        name="os.system() Call",
        description=(
            "os.system() passes a command string to the OS shell, potentially "
            "running arbitrary system commands."
        ),
        category="code_execution",
        severity=Severity.HIGH,
    ),
    ThreatRule(
        pattern=r"\bsubprocess\b",
        name="subprocess Module Reference",
        description=(
            "The subprocess module spawns child processes; its presence may "
            "indicate an attempt to execute shell commands."
        ),
        category="code_execution",
        severity=Severity.MEDIUM,
    ),
]

# ---------------------------------------------------------------------------
# Network Exfiltration
# ---------------------------------------------------------------------------
_NETWORK_EXFILTRATION_RULES: list[ThreatRule] = [
    ThreatRule(
        pattern=r"\bcurl\b",
        name="curl Invocation",
        description=(
            "curl is a command-line HTTP client commonly used to send data to "
            "remote servers in exfiltration scenarios."
        ),
        category="network_exfiltration",
        severity=Severity.HIGH,
    ),
    ThreatRule(
        pattern=r"\bwget\b",
        name="wget Invocation",
        description=(
            "wget downloads files from the network and can also be used to "
            "POST data to an attacker-controlled endpoint."
        ),
        category="network_exfiltration",
        severity=Severity.HIGH,
    ),
    ThreatRule(
        pattern=r"\bInvoke-WebRequest\b",
        name="PowerShell Invoke-WebRequest",
        description=(
            "PowerShell's Invoke-WebRequest cmdlet can make arbitrary HTTP "
            "requests, often used in Windows-based exfiltration."
        ),
        category="network_exfiltration",
        severity=Severity.HIGH,
    ),
]

# ---------------------------------------------------------------------------
# Aggregated default rule set
# ---------------------------------------------------------------------------

DEFAULT_RULES: list[ThreatRule] = (
    _CMD_INJECTION_RULES
    + _PROMPT_INJECTION_RULES
    + _SQL_INJECTION_RULES
    + _PATH_TRAVERSAL_RULES
    + _CODE_EXECUTION_RULES
    + _NETWORK_EXFILTRATION_RULES
)
"""The complete set of rules loaded by the engine on startup.

Extend this list — or provide an alternative list at construction time — to add
custom rules without modifying engine internals.
"""
