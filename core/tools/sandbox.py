import asyncio
import json
import re
import shlex
from dataclasses import replace

from agents import RunContextWrapper, function_tool

from core.runtime.context import AgentRuntimeContext
from core.sandbox import command_output
from core.sandbox.command_jobs import cancel_async_sandbox_command, start_async_sandbox_command
from core.sandbox.command_output import COMMAND_TIMEOUT_ERROR
from schema.sandbox.async_jobs import SandboxAsyncJobStatus
from schema.common.tool_results import ToolResultSchema, ToolResultStatusSchema, ToolResultTypeSchema
from service.sandbox import async_jobs as sandbox_async_jobs
from service.sandbox.commands import SandboxContainerCommandTimeoutError, execute_sandbox_container_command
from utils.markdown import markdown_body_without_front_matter


_SKILL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
SANDBOX_SKILLS_DIR = ".agents/skills"
_SKILL_RESOURCE_FILES_MARKER = "__Z3R0_SKILL_RESOURCE_FILES__"
_SKILL_RESOURCE_FILES_TRUNCATED_MARKER = "__Z3R0_SKILL_RESOURCE_FILES_TRUNCATED__"
_MAX_SKILL_RESOURCE_FILES = 200
_SYNC_COMMAND_TIMEOUT_SECONDS = 30
_ASYNC_COMMAND_TIMEOUT_SECONDS = 300
_ASYNC_COMMAND_CONCURRENCY_LIMIT = 3

# Skill alias map — ported from Xalgorix's skillAliases.
# Maps common shorthand names to canonical skill directory names.
# NOTE: "nmap" and "sqlmap" are EXCLUDED because they match existing
# Daybreak tool-reference skills. Exact-name match takes priority over alias.
SKILL_ALIASES: dict[str, str] = {
    # ── Web application vulnerabilities ──────────────────────────────
    "sql-injection": "exploiting-sql-injection-vulnerabilities",
    "sqli": "exploiting-sql-injection-vulnerabilities",
    "sql-injection-sqlmap": "exploiting-sql-injection-with-sqlmap",
    "nosql-injection": "exploiting-nosql-injection-vulnerabilities",
    "nosqli": "exploiting-nosql-injection-vulnerabilities",
    "xss": "testing-for-xss-vulnerabilities",
    "cross-site-scripting": "testing-for-xss-vulnerabilities",
    "xss-burp": "testing-for-xss-vulnerabilities-with-burpsuite",
    "ssrf": "performing-ssrf-vulnerability-exploitation",
    "blind-ssrf": "performing-blind-ssrf-exploitation",
    "csrf": "performing-csrf-attack-simulation",
    "cross-site-request-forgery": "performing-csrf-attack-simulation",
    "xxe": "testing-for-xxe-injection-vulnerabilities",
    "xml-external-entity": "testing-for-xxe-injection-vulnerabilities",
    "idor": "exploiting-idor-vulnerabilities",
    "insecure-direct-object-reference": "exploiting-idor-vulnerabilities",
    "ssti": "exploiting-template-injection-vulnerabilities",
    "template-injection": "exploiting-template-injection-vulnerabilities",
    "server-side-template-injection": "exploiting-template-injection-vulnerabilities",
    "cors": "testing-cors-misconfiguration",
    "cors-misconfiguration": "testing-cors-misconfiguration",
    "open-redirect": "testing-for-open-redirect-vulnerabilities",
    "clickjacking": "performing-clickjacking-attack-test",
    "deserialization": "exploiting-insecure-deserialization",
    "insecure-deserialization": "exploiting-insecure-deserialization",
    "race-condition": "exploiting-race-condition-vulnerabilities",
    "mass-assignment": "exploiting-mass-assignment-in-rest-apis",
    "api-injection": "exploiting-api-injection-vulnerabilities",
    "command-injection": "detecting-modbus-command-injection-attacks",
    # ── Authentication & authorization ───────────────────────────────
    "jwt": "exploiting-jwt-algorithm-confusion-attack",
    "jwt-attack": "exploiting-jwt-algorithm-confusion-attack",
    "jwt-signing": "implementing-jwt-signing-and-verification",
    "oauth": "exploiting-oauth-misconfiguration",
    "oauth-misconfig": "exploiting-oauth-misconfiguration",
    "oauth-token-theft": "detecting-oauth-token-theft",
    "forced-browsing": "bypassing-authentication-with-forced-browsing",
    "brute-force": "detecting-rdp-brute-force-attacks",
    "passwordless": "implementing-passwordless-authentication-with-fido2",
    "fido2": "implementing-passwordless-authentication-with-fido2",
    # ── Reconnaissance ───────────────────────────────────────────────
    "recon": "conducting-external-reconnaissance-with-osint",
    "reconnaissance": "conducting-external-reconnaissance-with-osint",
    "osint": "performing-open-source-intelligence-gathering",
    "subdomain": "performing-subdomain-enumeration-with-subfinder",
    "subdomain-enum": "performing-subdomain-enumeration-with-subfinder",
    "subfinder": "performing-subdomain-enumeration-with-subfinder",
    "network-scan": "scanning-network-with-nmap-advanced",
    "api-enumeration": "detecting-api-enumeration-attacks",
    "shadow-api": "detecting-shadow-api-endpoints",
    "cert-transparency": "analyzing-certificate-transparency-for-phishing",
    # ── API security ─────────────────────────────────────────────────
    "api-security": "conducting-api-security-testing",
    "api-gateway": "implementing-api-gateway-security-controls",
    "api-rate-limiting": "implementing-api-rate-limiting-and-throttling",
    "api-schema": "implementing-api-schema-validation-security",
    "api-keys": "implementing-api-key-security-controls",
    "api-abuse": "implementing-api-abuse-detection-with-rate-limiting",
    "api-posture": "implementing-api-security-posture-management",
    "data-exposure": "exploiting-excessive-data-exposure-in-api",
    # ── Active Directory ─────────────────────────────────────────────
    "ad-pentest": "performing-active-directory-penetration-test",
    "active-directory": "performing-active-directory-penetration-test",
    "bloodhound": "exploiting-active-directory-with-bloodhound",
    "ad-acl": "analyzing-active-directory-acl-abuse",
    "kerberoasting": "performing-active-directory-penetration-test",
    "dcsync": "detecting-dcsync-attack-in-active-directory",
    "ad-cert": "exploiting-active-directory-certificate-services-esc1",
    # ── Lateral movement & privilege escalation ──────────────────────
    "lateral-movement": "detecting-lateral-movement-in-network",
    "privilege-escalation": "detecting-privilege-escalation-attempts",
    "privesc": "detecting-privilege-escalation-attempts",
    "aws-privesc": "detecting-aws-iam-privilege-escalation",
    "azure-lateral": "detecting-azure-lateral-movement",
    "dcom": "hunting-for-dcom-lateral-movement",
    "wmi": "hunting-for-lateral-movement-via-wmi",
    # ── Phishing ─────────────────────────────────────────────────────
    "phishing": "conducting-phishing-incident-response",
    "spearphishing": "conducting-spearphishing-simulation-campaign",
    "phishing-simulation": "executing-phishing-simulation-campaign",
    "qr-phishing": "detecting-qr-code-phishing-with-email-security",
    "email-headers": "analyzing-email-headers-for-phishing-investigation",
    # ── Cloud & Kubernetes ───────────────────────────────────────────
    "k8s-privesc": "detecting-privilege-escalation-in-kubernetes-pods",
    "opa-gatekeeper": "implementing-opa-gatekeeper-for-policy-enforcement",
    "azure-ad": "auditing-azure-active-directory-configuration",
    "azure-pim": "implementing-azure-ad-privileged-identity-management",
    # ── Memory / binary exploitation ─────────────────────────────────
    "heap-spray": "analyzing-heap-spray-exploitation",
    # ── Detection & monitoring ───────────────────────────────────────
    "sql-injection-waf": "detecting-sql-injection-via-waf-logs",
    "lateral-splunk": "detecting-lateral-movement-with-splunk",
    "lateral-zeek": "detecting-lateral-movement-with-zeek",
    # ── Mobile ───────────────────────────────────────────────────────
    "burpsuite-mobile": "intercepting-mobile-traffic-with-burpsuite",
    "burp": "intercepting-mobile-traffic-with-burpsuite",
    # ── File upload testing ──────────────────────────────────────────
    "file-upload": "exploiting-file-upload-vulnerabilities",
    "upload": "exploiting-file-upload-vulnerabilities",
    "upload-bypass": "exploiting-file-upload-vulnerabilities",
    "webshell-upload": "exploiting-file-upload-vulnerabilities",
    # ── CMS-specific testing ────────────────────────────────────────
    "cms": "performing-cms-specific-security-testing",
    "cms-testing": "performing-cms-specific-security-testing",
    "wordpress": "performing-cms-specific-security-testing",
    "wpscan": "performing-cms-specific-security-testing",
    "drupal": "performing-cms-specific-security-testing",
    "joomla": "performing-cms-specific-security-testing",
    # ── Subdomain takeover ──────────────────────────────────────────
    "subdomain-takeover": "exploiting-subdomain-takeover-vulnerabilities",
    "takeover": "exploiting-subdomain-takeover-vulnerabilities",
    "dangling-cname": "exploiting-subdomain-takeover-vulnerabilities",
    # ── Zero-day & novel vulnerability discovery ────────────────────
    "zero-day": "performing-zero-day-vulnerability-discovery",
    "0day": "performing-zero-day-vulnerability-discovery",
    "novel-vuln": "performing-zero-day-vulnerability-discovery",
    "attack-chaining": "performing-zero-day-vulnerability-discovery",
    "logic-flaw": "performing-zero-day-vulnerability-discovery",
    # ── Exploit verification ────────────────────────────────────────
    "exploit-verification": "performing-exploit-verification",
    "verify-exploit": "performing-exploit-verification",
    "false-positive": "performing-exploit-verification",
    "proof-of-concept": "performing-exploit-verification",
    "poc": "performing-exploit-verification",
    # ── Email security testing ──────────────────────────────────────
    "email-security": "performing-email-security-testing",
    "email-testing": "performing-email-security-testing",
    "smtp-relay": "performing-email-security-testing",
    "email-spoofing": "performing-email-security-testing",
    "spf-bypass": "performing-email-security-testing",
    # ── Misc ─────────────────────────────────────────────────────────
    "darkweb": "monitoring-darkweb-sources",
    "dmarc": "performing-dmarc-policy-enforcement-rollout",
}


def _command_result(
    *,
    status: SandboxAsyncJobStatus,
    output_file: str | None = None,
    output_bytes: int = 0,
    output_lines: int = 0,
    exit_code: int | None = None,
    run_id: str | None = None,
    error: str | None = None,
) -> str:
    return command_output.result_metadata(
        status=status,
        output_file=output_file,
        output_bytes=output_bytes,
        output_lines=output_lines,
        exit_code=exit_code,
        run_id=run_id,
        error=error,
    ).model_dump_json(exclude_none=True, exclude_defaults=True)


def _error_result(error: str) -> str:
    return _command_result(status=SandboxAsyncJobStatus.FAILED, error=error)


def _clamp_timeout(timeout_seconds: int | None, maximum: int) -> int:
    if timeout_seconds is None:
        return maximum
    try:
        timeout_seconds = int(timeout_seconds)
    except (TypeError, ValueError):
        return maximum
    return min(max(timeout_seconds, 1), maximum)


@function_tool
async def execute_sync_command(
    ctx: RunContextWrapper[AgentRuntimeContext],
    command: str,
    timeout_seconds: int = _SYNC_COMMAND_TIMEOUT_SECONDS,
) -> str:
    """Execute a short sandbox command and return result metadata.

    Args:
        command: str shell command to execute in the selected sandbox container.
        timeout_seconds: int command timeout in seconds, clamped to 1-30.

    Returns:
        JSON metadata with status, output_file, output_bytes, output_lines, exit_code, and optional error.
    """
    container_id = ctx.context.sandbox_container_id
    if container_id is None:
        return _error_result("No sandbox container selected.")
    if not command.strip():
        return _error_result("sandbox container command is required")
    timeout = _clamp_timeout(timeout_seconds, _SYNC_COMMAND_TIMEOUT_SECONDS)
    output_path = command_output.new_output_path()

    try:
        result = await execute_sandbox_container_command(
            id=container_id,
            command=command_output.capture_command(command, output_path),
            timeout_seconds=timeout,
        )
    except asyncio.CancelledError:
        raise
    except SandboxContainerCommandTimeoutError:
        return _error_result(COMMAND_TIMEOUT_ERROR)
    except Exception as exc:
        return _error_result(str(exc) or "Command execution failed.")

    output_bytes, output_lines = command_output.parse_capture_stats(result.output)
    return _command_result(
        status=SandboxAsyncJobStatus.COMPLETED if result.exit_code == 0 else SandboxAsyncJobStatus.FAILED,
        output_file=output_path,
        output_bytes=output_bytes,
        output_lines=output_lines,
        exit_code=result.exit_code,
    )


@function_tool
async def execute_async_command(
    ctx: RunContextWrapper[AgentRuntimeContext],
    command: str,
    timeout_seconds: int = _ASYNC_COMMAND_TIMEOUT_SECONDS,
) -> str:
    """Start a long-running sandbox command; this ends the current turn.

    Dispatching is turn-terminal: control returns to the runtime and the agent
    is resumed automatically when the command finishes, with its result and
    output file delivered as fresh context. Never poll or read a running job.

    Args:
        command: str shell command to execute in the selected sandbox container.
        timeout_seconds: int command timeout in seconds, clamped to 1-300.

    Returns:
        JSON metadata with status and run_id.
    """
    container_id = ctx.context.sandbox_container_id
    if container_id is None:
        return _error_result("No sandbox container selected.")
    if not command.strip():
        return _error_result("sandbox container command is required")
    if not ctx.context.agent_instance_id:
        return _error_result("agent instance id is required for async command execution")

    running_jobs = await sandbox_async_jobs.count_running_async_jobs_for_agent(
        session_id=ctx.context.session_id,
        agent_instance_id=ctx.context.agent_instance_id,
    )
    if running_jobs >= _ASYNC_COMMAND_CONCURRENCY_LIMIT:
        return _error_result(
            f"sandbox async command limit reached; at most {_ASYNC_COMMAND_CONCURRENCY_LIMIT} commands may run concurrently",
        )

    timeout = _clamp_timeout(timeout_seconds, _ASYNC_COMMAND_TIMEOUT_SECONDS)
    run_id = command_output.new_run_id()
    output_path = command_output.output_path_for_run(run_id)
    command_text = command.strip()

    await start_async_sandbox_command(
        run_id=run_id,
        context=replace(ctx.context),
        command=command_text,
        output_file=output_path,
        wrapped_command=command_output.async_command(command_text, output_path),
        stat_command=command_output.stat_command(output_path),
        timeout_seconds=timeout,
    )
    return _command_result(
        status=SandboxAsyncJobStatus.RUNNING,
        run_id=run_id,
    )


@function_tool
async def read_sandbox_command_output(
    ctx: RunContextWrapper[AgentRuntimeContext],
    output_file: str,
    start_line: int = 1,
    line_count: int = command_output.OUTPUT_CHUNK_LINE_COUNT,
) -> str:
    """Read a bounded line range from a sandbox command output file.

    Args:
        output_file: str output path returned by execute_sync_command or an async completion notification.
        start_line: int one-based starting line number.
        line_count: int number of lines to read, clamped by the output reader to a bounded chunk size.

    Returns:
        JSON chunk with output_file, start_line, end_line, and content.
    """
    container_id = ctx.context.sandbox_container_id
    if container_id is None:
        return _error_result("No sandbox container selected.")
    try:
        read_cmd, start, count, end = command_output.read_command(output_file, start_line, line_count)
        result = await execute_sandbox_container_command(
            id=container_id,
            command=read_cmd,
            timeout_seconds=_SYNC_COMMAND_TIMEOUT_SECONDS,
        )
    except asyncio.CancelledError:
        raise
    except ValueError as exc:
        return _error_result(str(exc))
    except SandboxContainerCommandTimeoutError:
        return _error_result(COMMAND_TIMEOUT_ERROR)
    except Exception as exc:
        return _error_result(str(exc) or "Command output read failed.")
    if result.exit_code != 0:
        return _error_result(result.output or "Command output read failed.")

    return command_output.output_chunk(
        output_file=output_file,
        start_line=start,
        line_count=count,
        content=result.output,
    ).model_dump_json(exclude_none=True)


@function_tool
async def cancel_sandbox_async_job(ctx: RunContextWrapper[AgentRuntimeContext], run_id: str) -> str:
    """Cancel a sandbox async command owned by the current session.

    Args:
        run_id: str async command run id returned by execute_async_command.

    Returns:
        JSON metadata for the latest known async command state after cancellation is requested.
    """
    snapshot = await sandbox_async_jobs.get_async_job(run_id.strip(), session_id=ctx.context.session_id)
    if snapshot is None or snapshot.agent_instance_id != ctx.context.agent_instance_id:
        return _error_result("sandbox async job not found")
    await cancel_async_sandbox_command(snapshot.run_id)
    latest = await sandbox_async_jobs.get_async_job(snapshot.run_id, session_id=ctx.context.session_id)
    return command_output.result_metadata_from_snapshot(
        latest or snapshot,
    ).model_dump_json(exclude_none=True, exclude_defaults=True)


def _skill_result(status: ToolResultStatusSchema, output: str) -> str:
    return ToolResultSchema(
        status=status, type=ToolResultTypeSchema.SKILL_DETAIL, output=output,
    ).model_dump_json()


def _skill_root(skill_name: str) -> str:
    return f"{SANDBOX_SKILLS_DIR}/{skill_name}"


def _load_skill_command(skill_name: str) -> str:
    skill_root = _skill_root(skill_name)
    return f"""
skill_root={shlex.quote(skill_root)}
skill_file="$skill_root/SKILL.md"
test -f "$skill_file" || exit 1
cat "$skill_file"
printf '\\n%s\\n' {shlex.quote(_SKILL_RESOURCE_FILES_MARKER)}
find "$skill_root" -mindepth 1 -type f | sort | awk -v prefix="$skill_root/" -v max={_MAX_SKILL_RESOURCE_FILES} -v truncated={shlex.quote(_SKILL_RESOURCE_FILES_TRUNCATED_MARKER)} '
  index($0, prefix) == 1 {{
    rel = substr($0, length(prefix) + 1)
    if (rel == "SKILL.md") next
    count += 1
    if (count <= max) print rel
    else {{ print truncated; exit }}
  }}
'
""".strip()


def _parse_loaded_skill_output(output: str) -> tuple[str, tuple[str, ...], bool]:
    markdown, separator, resources = output.rpartition(f"\n{_SKILL_RESOURCE_FILES_MARKER}\n")
    if not separator:
        return output, (), False

    files: list[str] = []
    truncated = False
    for line in resources.splitlines():
        entry = line.strip()
        if not entry:
            continue
        if entry == _SKILL_RESOURCE_FILES_TRUNCATED_MARKER:
            truncated = True
            continue
        files.append(entry)
    return markdown, tuple(files), truncated


def _loaded_skill_body(
    skill_name: str,
    markdown: str,
    resource_files: tuple[str, ...] = (),
    resource_files_truncated: bool = False,
) -> str:
    skill_root = _skill_root(skill_name)
    body = markdown_body_without_front_matter(markdown).strip()
    parts = [
        (
            "## Skill Resource Root\n\n"
            f"`{skill_root}`\n\n"
            "Use sandbox command tools for reads, inspection, execution, and other file operations under this root."
        ),
        _skill_resource_files_section(resource_files, resource_files_truncated),
    ]
    if body:
        parts.append(body)
    return "\n\n".join(parts)


def _skill_resource_files_section(files: tuple[str, ...], truncated: bool) -> str:
    if not files:
        return "## Skill Resource Files\n\nNone."
    lines = [f"- `{path}`" for path in files]
    if truncated:
        lines.append(f"- ... truncated after {_MAX_SKILL_RESOURCE_FILES} files")
    return "## Skill Resource Files\n\nPaths are relative to `Skill Resource Root`:\n\n" + "\n".join(lines)


@function_tool
async def load_skill(ctx: RunContextWrapper[AgentRuntimeContext], name: str) -> str:
    """Load the body of a named skill from the selected sandbox container.

    Args:
        name: str skill directory name under .agents/skills. Shorthand aliases are supported (e.g., "sqli", "xss", "ssrf").

    Returns:
        JSON status with the skill body, sandbox-relative skill root, and resource file list.
    """
    container_id = ctx.context.sandbox_container_id
    if container_id is None:
        return _skill_result(ToolResultStatusSchema.ERROR, "No sandbox container selected.")

    skill_name = name.strip()
    if not _SKILL_NAME_PATTERN.fullmatch(skill_name):
        return _skill_result(
            ToolResultStatusSchema.ERROR,
            "Skill name must contain only letters, numbers, dot, underscore, or dash.",
        )

    try:
        result = await execute_sandbox_container_command(
            id=container_id,
            command=_load_skill_command(skill_name),
            timeout_seconds=_SYNC_COMMAND_TIMEOUT_SECONDS,
        )
    except asyncio.CancelledError:
        raise
    except SandboxContainerCommandTimeoutError:
        return _skill_result(ToolResultStatusSchema.ERROR, COMMAND_TIMEOUT_ERROR)
    except Exception as exc:
        return _skill_result(ToolResultStatusSchema.ERROR, str(exc) or "Skill loading failed.")

    # If exact name not found, try alias resolution
    if result.exit_code != 0:
        resolved = SKILL_ALIASES.get(skill_name.lower())
        if resolved and resolved != skill_name:
            try:
                result = await execute_sandbox_container_command(
                    id=container_id,
                    command=_load_skill_command(resolved),
                    timeout_seconds=_SYNC_COMMAND_TIMEOUT_SECONDS,
                )
            except asyncio.CancelledError:
                raise
            except SandboxContainerCommandTimeoutError:
                return _skill_result(ToolResultStatusSchema.ERROR, COMMAND_TIMEOUT_ERROR)
            except Exception as exc:
                return _skill_result(ToolResultStatusSchema.ERROR, str(exc) or "Skill loading failed.")
            if result.exit_code == 0:
                skill_name = resolved  # Use resolved name for body formatting

    if result.exit_code != 0:
        return _skill_result(ToolResultStatusSchema.ERROR, f"Skill not found: {skill_name}")

    markdown, resource_files, resource_files_truncated = _parse_loaded_skill_output(result.output)
    return _skill_result(
        ToolResultStatusSchema.SUCCESS,
        _loaded_skill_body(skill_name, markdown, resource_files, resource_files_truncated),
    )


@function_tool
async def list_skills(
    ctx: RunContextWrapper[AgentRuntimeContext],
    category: str = "",
) -> str:
    """List available sandbox skills, optionally filtered by category.

    Call this to see what methodology skills are available before deciding
    which to load. Use search_skills for keyword-based discovery.

    Args:
        category: str optional category filter (e.g., "web-application-security",
                  "cloud-security", "penetration-testing"). Omit to list categories with counts.

    Returns:
        JSON status with skill names and descriptions, or category list with counts.
    """
    container_id = ctx.context.sandbox_container_id
    if container_id is None:
        return _skill_result(ToolResultStatusSchema.ERROR, "No sandbox container selected.")

    category = category.strip()
    skills_dir = shlex.quote(SANDBOX_SKILLS_DIR)

    if category:
        # Filter by category: grep for subdomain field in front matter
        category_escaped = shlex.quote(category)
        command = f"""
if [ -d {skills_dir} ]; then
  find {skills_dir} -mindepth 2 -maxdepth 2 -name SKILL.md -type f | sort | while IFS= read -r skill_file; do
    if grep -qE "subdomain: {category_escaped}" "$skill_file" 2>/dev/null; then
      skill_name=$(basename "$(dirname "$skill_file")")
      desc=$(awk -F': *' 'NR>1 && $1=="description" {{sub(/^description: */, ""); print; exit}}' "$skill_file")
      printf '%s\\t%s\\n' "$skill_name" "$desc"
    fi
  done
fi
""".strip()
    else:
        # List categories with counts
        command = f"""
if [ -d {skills_dir} ]; then
  find {skills_dir} -mindepth 2 -maxdepth 2 -name SKILL.md -type f | sort | while IFS= read -r skill_file; do
    cat_subdomain=$(awk -F': *' 'NR>1 && $1=="subdomain" {{sub(/^subdomain: */, ""); print; exit}}' "$skill_file")
    if [ -n "$cat_subdomain" ]; then
      printf '%s\\n' "$cat_subdomain"
    else
      printf '%s\\n' "_tool_reference"
    fi
  done | sort | uniq -c | sort -rn
fi
""".strip()

    try:
        result = await execute_sandbox_container_command(
            id=container_id,
            command=command,
            timeout_seconds=30,
        )
    except asyncio.CancelledError:
        raise
    except SandboxContainerCommandTimeoutError:
        return _skill_result(ToolResultStatusSchema.ERROR, COMMAND_TIMEOUT_ERROR)
    except Exception as exc:
        return _skill_result(ToolResultStatusSchema.ERROR, str(exc) or "list_skills failed.")

    if result.exit_code != 0 or not result.output.strip():
        if category:
            return _skill_result(ToolResultStatusSchema.ERROR, f"No skills found in category: {category}")
        return _skill_result(ToolResultStatusSchema.ERROR, "No skills found.")

    return _skill_result(ToolResultStatusSchema.SUCCESS, result.output.strip())


@function_tool
async def search_skills(
    ctx: RunContextWrapper[AgentRuntimeContext],
    query: str,
) -> str:
    """Search available sandbox skills by name or description keyword.

    Use this to discover methodology skills beyond the core skill index.
    Returns matching skill names and short descriptions. Then use load_skill
    to get the full methodology.

    Args:
        query: str search term (e.g., "sql injection", "xss", "cloud", "kubernetes").

    Returns:
        JSON status with matching skill names and descriptions.
    """
    container_id = ctx.context.sandbox_container_id
    if container_id is None:
        return _skill_result(ToolResultStatusSchema.ERROR, "No sandbox container selected.")

    query_stripped = query.strip()
    if not query_stripped:
        return _skill_result(ToolResultStatusSchema.ERROR, "Search query is required.")

    # Check aliases first
    alias_results: list[dict[str, str]] = []
    query_lower = query_stripped.lower()
    for alias, canonical in SKILL_ALIASES.items():
        if query_lower in alias or alias in query_lower:
            alias_results.append({"alias": alias, "skill": canonical})

    skills_dir = shlex.quote(SANDBOX_SKILLS_DIR)
    query_escaped = shlex.quote(query_stripped)

    # Search skill names and descriptions
    command = f"""
if [ -d {skills_dir} ]; then
  find {skills_dir} -mindepth 2 -maxdepth 2 -name SKILL.md -type f | sort | while IFS= read -r skill_file; do
    skill_name=$(basename "$(dirname "$skill_file")")
    if echo "$skill_name" | grep -i {query_escaped} >/dev/null 2>&1; then
      desc=$(awk -F': *' 'NR>1 && $1=="description" {{sub(/^description: */, ""); print; exit}}' "$skill_file")
      printf 'name\\t%s\\tdesc\\t%s\\n' "$skill_name" "$desc"
    elif grep -i {query_escaped} "$skill_file" >/dev/null 2>&1; then
      desc=$(awk -F': *' 'NR>1 && $1=="description" {{sub(/^description: */, ""); print; exit}}' "$skill_file")
      if echo "$desc" | grep -i {query_escaped} >/dev/null 2>&1; then
        printf 'name\\t%s\\tdesc\\t%s\\n' "$skill_name" "$desc"
      fi
    fi
  done | head -n 30
fi
""".strip()

    try:
        result = await execute_sandbox_container_command(
            id=container_id,
            command=command,
            timeout_seconds=30,
        )
    except asyncio.CancelledError:
        raise
    except SandboxContainerCommandTimeoutError:
        return _skill_result(ToolResultStatusSchema.ERROR, COMMAND_TIMEOUT_ERROR)
    except Exception as exc:
        return _skill_result(ToolResultStatusSchema.ERROR, str(exc) or "search_skills failed.")

    # Combine alias matches and search results
    parts: list[str] = []
    if alias_results:
        parts.append("## Alias Matches\n")
        for entry in alias_results[:10]:
            parts.append(f"- `{entry['alias']}` → `{entry['skill']}`")

    if result.exit_code == 0 and result.output.strip():
        if parts:
            parts.append("\n## Skill Matches\n")
        for line in result.output.strip().splitlines():
            if line.startswith("name\t"):
                fields = line.split("\t")
                if len(fields) >= 4:
                    parts.append(f"- **{fields[1]}**: {fields[3]}")

    if not parts:
        return _skill_result(ToolResultStatusSchema.ERROR, f"No skills found matching: {query_stripped}")

    return _skill_result(ToolResultStatusSchema.SUCCESS, "\n".join(parts))
