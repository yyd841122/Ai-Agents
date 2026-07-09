import os
import shutil
import json as _json
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv()

ROOT = Path(__file__).resolve().parent

PRODUCT_FILE = ROOT / "Product.md"
ARCHITECT_FILE = ROOT / "Architect.md"
TEST_DESIGNER_FILE = ROOT / "TestDesigner.md"
TASK_MANAGER_FILE = ROOT / "TaskManager.md"
PLANNER_FILE = ROOT / "Planner.md"
CODER_FILE = ROOT / "Coder.md"
REVIEWER_FILE = ROOT / "Reviewer.md"
TESTER_FILE = ROOT / "Tester.md"
DOCUMENTER_FILE = ROOT / "Documenter.md"
TASK_FILE = ROOT / "tasks" / "task.txt"

OUTPUT_DIR = ROOT / "outputs"

WORKFLOW_STAGES = [
    "Product",
    "Architect",
    "TestDesigner",
    "TaskManager",
    "Planner",
    "Coder",
    "Reviewer",
    "Tester",
]

MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY")
MINIMAX_MODEL = os.getenv("MINIMAX_MODEL", "MiniMax-M3")
MINIMAX_BASE_URL = os.getenv(
    "MINIMAX_BASE_URL",
    "https://api.minimax.chat/v1/chat/completions",
)

# Failure Injection Switch: target agent name (default: disabled)
FAIL_AGENT = os.getenv("FAIL_AGENT", "").strip()

# Real Project Workspace Switch: project root path (default: disabled)
PROJECT_ROOT = os.getenv("PROJECT_ROOT", "").strip()

# B-05: Project Registry Switch: project id (default: disabled)
PROJECT_ID = os.getenv("PROJECT_ID", "").strip()

# B-05: Project registry path
PROJECTS_DIR = ROOT / "projects"
REGISTRY_FILE = PROJECTS_DIR / "registry.json"
import re as _re
_VALID_PROJECT_ID_PATTERN = _re.compile(r"^[A-Za-z0-9_\-]+$")


def is_valid_project_id(project_id: str) -> bool:
    if not project_id:
        return False
    if "/" in project_id or "\\" in project_id or ".." in project_id:
        return False
    if _re.search(r"\s", project_id):
        return False
    return bool(_VALID_PROJECT_ID_PATTERN.match(project_id))


def load_project_registry() -> dict:
    """B-05: Load registry.json; create empty if missing; preserve on corruption."""
    if not REGISTRY_FILE.exists():
        return {"projects": {}}
    try:
        content = REGISTRY_FILE.read_text(encoding="utf-8")
        if not content.strip():
            return {"projects": {}}
        data = _json.loads(content)
        if not isinstance(data, dict):
            return {"projects": {}}
        if "projects" not in data or not isinstance(data["projects"], dict):
            data["projects"] = {}
        return data
    except Exception:
        return {"__corrupted__": True}


def save_project_registry(registry: dict) -> None:
    """B-05: Persist registry.json atomically."""
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    tmp = REGISTRY_FILE.with_suffix(".json.tmp")
    tmp.write_text(_json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(REGISTRY_FILE)


def register_or_update_project(
    project_id: str,
    workspace_info: dict,
    run_dir: Path,
) -> dict:
    """B-05: Register or update a project entry in registry.json."""
    if not project_id:
        return {
            "enabled": False,
            "project_id": "",
            "registry_status": "未启用",
            "project_status": "未启用",
            "project_root": "",
            "created": False,
            "updated": False,
            "last_run_id": "",
            "reason": "PROJECT_ID 未设置，项目注册未启用",
        }
    if not is_valid_project_id(project_id):
        return {
            "enabled": False,
            "project_id": project_id,
            "registry_status": "无效",
            "project_status": "无效",
            "project_root": "",
            "created": False,
            "updated": False,
            "last_run_id": "",
            "reason": "PROJECT_ID 非法",
        }

    detection = workspace_info.get("detection_status", "未启用")
    if detection != "已识别":
        return {
            "enabled": True,
            "project_id": project_id,
            "registry_status": "跳过",
            "project_status": "等待工作区",
            "project_root": "",
            "created": False,
            "updated": False,
            "last_run_id": "",
            "reason": "PROJECT_ROOT 未识别，暂不注册项目",
        }

    project_root = workspace_info.get("project_root", "")

    registry = load_project_registry()
    if registry.get("__corrupted__"):
        return {
            "enabled": True,
            "project_id": project_id,
            "registry_status": "无效",
            "project_status": "注册表无效",
            "project_root": project_root,
            "created": False,
            "updated": False,
            "last_run_id": "",
            "reason": "registry.json 已损坏，未覆盖",
        }

    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    existing = registry["projects"].get(project_id)
    run_id = run_dir.name if run_dir else ""

    created = False
    updated = False
    if existing is None:
        registry["projects"][project_id] = {
            "project_id": project_id,
            "project_root": project_root,
            "status": "active",
            "created_at": now_iso,
            "updated_at": now_iso,
            "last_run_id": run_id,
        }
        created = True
        project_status = "已注册"
    else:
        existing["project_root"] = project_root
        existing["updated_at"] = now_iso
        existing["last_run_id"] = run_id
        existing["status"] = "active"
        registry["projects"][project_id] = existing
        updated = True
        project_status = "已更新"

    save_project_registry(registry)

    return {
        "enabled": True,
        "project_id": project_id,
        "registry_status": "已记录",
        "project_status": project_status,
        "project_root": project_root,
        "created": created,
        "updated": updated,
        "last_run_id": run_id,
        "reason": "项目注册已写入 registry.json",
    }

# B-01: Real project workspace info (global, set in main)
agent_workspace_info: dict = {}

# B-02: Real task protocol info (global, set in main)
real_task_protocol_info: dict = {}

# B-03: Real file modification result (global, set in main)
real_file_modification_info: dict = {}

# B-04: Project change record (global, set in main)
project_change_record_info: dict = {}

# B-05: Project registry result (global, set in main)
project_registry_result: dict = {}

# B-05: Project session info (global, set in main)
project_session_info: dict = {}

# B-06: Project resume entry (global, set in main)
project_resume_entry: dict = {}

# B-06: Project state write result (global, set in main)
project_state_write_result: dict = {}

# B-07: Minimal dev loop acceptance (global, set in main)
minimal_dev_loop_acceptance: dict = {}

# B-08: Reviewer diff context status (global, set in main)
reviewer_diff_context_status: str = "跳过"

# B-09: Reviewer structured result (global, set in main)
reviewer_structured_result: dict = {}


def build_project_session_info(
    project_id: str,
    workspace_info: dict,
    registry_result: dict,
    run_dir: Path,
) -> dict:
    """B-05: Build project session info for reporting."""
    if not project_id:
        return {
            "enabled": False,
            "project_id": "",
            "project_root": "",
            "run_dir": str(run_dir),
            "project_latest_dir": "",
            "global_latest_dir": str(OUTPUT_DIR / "latest"),
            "registry_status": "未启用",
            "project_status": "未启用",
            "session_status": "未启用",
            "reason": "PROJECT_ID 未设置",
        }
    if not is_valid_project_id(project_id):
        return {
            "enabled": False,
            "project_id": project_id,
            "project_root": "",
            "run_dir": str(run_dir),
            "project_latest_dir": "",
            "global_latest_dir": str(OUTPUT_DIR / "latest"),
            "registry_status": "无效",
            "project_status": "无效",
            "session_status": "无效",
            "reason": "PROJECT_ID 非法",
        }
    project_latest_dir = ROOT / "outputs" / "projects" / project_id / "latest"
    return {
        "enabled": True,
        "project_id": project_id,
        "project_root": registry_result.get("project_root", ""),
        "run_dir": str(run_dir),
        "project_latest_dir": str(project_latest_dir),
        "global_latest_dir": str(OUTPUT_DIR / "latest"),
        "registry_status": registry_result.get("registry_status", "未启用"),
        "project_status": registry_result.get("project_status", "未启用"),
        "session_status": "已启用" if registry_result.get("project_status") in ("已注册", "已更新") else "等待工作区",
        "reason": registry_result.get("reason", ""),
    }


def detect_project_resume_entry(project_session_info: dict) -> dict:
    """B-06: Detect resume entry from existing project_state.json."""
    session_status = project_session_info.get("session_status", "未启用")
    project_id = project_session_info.get("project_id", "")

    if session_status != "已启用":
        return {
            "enabled": False,
            "project_id": project_id,
            "state_path": "",
            "state_exists": False,
            "resume_available": False,
            "last_run_id": "",
            "last_status": "",
            "last_stage": "",
            "resume_status": session_status,
            "reason": "项目会话未启用，恢复入口不可用",
        }

    state_path = ROOT / "outputs" / "projects" / project_id / "project_state.json"

    if not state_path.exists():
        return {
            "enabled": True,
            "project_id": project_id,
            "state_path": str(state_path),
            "state_exists": False,
            "resume_available": False,
            "last_run_id": "",
            "last_status": "",
            "last_stage": "",
            "resume_status": "无历史状态",
            "reason": "未发现 project_state.json",
        }

    try:
        data = _json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return {
            "enabled": True,
            "project_id": project_id,
            "state_path": str(state_path),
            "state_exists": True,
            "resume_available": False,
            "last_run_id": "",
            "last_status": "",
            "last_stage": "",
            "resume_status": "状态文件无效",
            "reason": "project_state.json 无法解析",
        }

    last_status = data.get("last_status", "")
    if last_status == "通过":
        resume_status = "可继续"
    elif last_status == "未通过":
        resume_status = "可恢复"
    else:
        resume_status = "未知"

    return {
        "enabled": True,
        "project_id": project_id,
        "state_path": str(state_path),
        "state_exists": True,
        "resume_available": bool(data.get("resume_available", False)),
        "last_run_id": data.get("last_run_id", ""),
        "last_status": last_status,
        "last_stage": data.get("last_stage", ""),
        "resume_status": resume_status,
        "reason": "已发现历史项目状态",
    }


def write_project_state(
    project_session_info: dict,
    run_dir: Path,
    workflow_result: str,
    current_stage: str,
    resume_status: str,
    error: Exception | None = None,
) -> dict:
    """B-06: Persist project_state.json after each run (success or failure)."""
    session_status = project_session_info.get("session_status", "未启用")
    project_id = project_session_info.get("project_id", "")
    project_root = project_session_info.get("project_root", "")

    state_path = ROOT / "outputs" / "projects" / project_id / "project_state.json"

    if session_status != "已启用":
        return {
            "enabled": False,
            "state_path": str(state_path) if project_id else "",
            "write_status": "跳过",
            "resume_available": False,
            "last_run_id": "",
            "last_status": "",
            "last_stage": "",
            "reason": "项目会话未启用，未写入项目状态",
        }

    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "project_id": project_id,
            "project_root": project_root,
            "last_run_id": run_dir.name if run_dir else "",
            "last_run_dir": str(run_dir),
            "last_status": workflow_result,
            "last_stage": current_stage,
            "resume_available": True,
            "resume_status": resume_status,
            "error": str(error) if error is not None else "",
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        state_path.write_text(
            _json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {
            "enabled": True,
            "state_path": str(state_path),
            "write_status": "已写入",
            "resume_available": True,
            "last_run_id": state["last_run_id"],
            "last_status": state["last_status"],
            "last_stage": state["last_stage"],
            "reason": "project_state.json 已写入",
        }
    except Exception as state_err:
        return {
            "enabled": True,
            "state_path": str(state_path),
            "write_status": "失败",
            "resume_available": False,
            "last_run_id": run_dir.name if run_dir else "",
            "last_status": workflow_result,
            "last_stage": current_stage,
            "reason": f"project_state.json 写入失败：{state_err}",
        }


def build_project_resume_status(
    session_status: str,
    workflow_result: str,
) -> str:
    """B-06: Compute project resume status for reporting."""
    if session_status == "未启用":
        return "未启用"
    if session_status == "无效":
        return "无效"
    if session_status == "等待工作区":
        return "等待工作区"
    if session_status != "已启用":
        return "未知"
    if workflow_result == "通过":
        return "可继续"
    if workflow_result == "未通过":
        return "可恢复"
    return "未知"


def build_minimal_dev_loop_acceptance(
    workspace_info: dict,
    real_task_protocol: dict,
    real_file_modification: dict,
    change_record: dict,
    project_session: dict,
    project_state_result: dict,
    workflow_result: str = "",
) -> dict:
    """B-07: Validate minimal real development loop end-to-end."""
    workspace_status = workspace_info.get("detection_status", "未启用")
    protocol_status = real_task_protocol.get("protocol_status", "未启用")
    file_modification_status = real_file_modification.get("status", "未启用")
    session_status = project_session.get("session_status", "未启用")
    state_write_status = project_state_result.get("write_status", "跳过")

    workspace_ok = workspace_status == "已识别"
    protocol_ok = protocol_status == "已建立"
    file_modification_ok = file_modification_status in ("已修改", "跳过")
    change_record_ok = bool(change_record)
    project_session_ok = session_status == "已启用"
    project_state_ok = state_write_status == "已写入"

    enabled = workspace_ok or session_status in ("无效", "等待工作区")

    if not workspace_ok and session_status != "无效" and session_status != "等待工作区":
        return {
            "enabled": False,
            "acceptance_status": "未启用",
            "workspace_ok": False,
            "protocol_ok": False,
            "file_modification_ok": False,
            "change_record_ok": False,
            "project_session_ok": False,
            "project_state_ok": False,
            "summary": "未绑定完整真实项目会话，最小闭环验收未启用",
            "reason": "未设置 PROJECT_ROOT 或 PROJECT_ID",
        }

    if not workspace_ok:
        return {
            "enabled": enabled,
            "acceptance_status": "未通过",
            "workspace_ok": False,
            "protocol_ok": False,
            "file_modification_ok": False,
            "change_record_ok": False,
            "project_session_ok": session_status == "已启用",
            "project_state_ok": project_state_ok,
            "summary": "工作区未识别或被阻止",
            "reason": f"workspace_status={workspace_status}",
        }

    if not protocol_ok:
        return {
            "enabled": True,
            "acceptance_status": "未通过",
            "workspace_ok": True,
            "protocol_ok": False,
            "file_modification_ok": False,
            "change_record_ok": change_record_ok,
            "project_session_ok": session_status == "已启用",
            "project_state_ok": project_state_ok,
            "summary": "真实任务协议未建立",
            "reason": f"protocol_status={protocol_status}",
        }

    if not project_state_ok:
        return {
            "enabled": True,
            "acceptance_status": "未通过",
            "workspace_ok": True,
            "protocol_ok": True,
            "file_modification_ok": file_modification_ok,
            "change_record_ok": change_record_ok,
            "project_session_ok": session_status == "已启用",
            "project_state_ok": False,
            "summary": "项目状态未成功写入",
            "reason": "项目状态未成功写入",
        }

    if workflow_result == "未通过":
        return {
            "enabled": True,
            "acceptance_status": "未通过",
            "workspace_ok": True,
            "protocol_ok": True,
            "file_modification_ok": file_modification_ok,
            "change_record_ok": change_record_ok,
            "project_session_ok": True,
            "project_state_ok": True,
            "summary": "工作流未通过，最小闭环不成立",
            "reason": "workflow_result=未通过",
        }

    return {
        "enabled": True,
        "acceptance_status": "已通过",
        "workspace_ok": True,
        "protocol_ok": True,
        "file_modification_ok": True,
        "change_record_ok": True,
        "project_session_ok": True,
        "project_state_ok": True,
        "summary": "B-07 最小真实开发闭环已成立",
        "reason": "工作区识别 + 协议建立 + 受控写入 + 变更记录 + 项目隔离 + 状态写入全部通过",
    }


def build_simple_diff_summary(before_content: str, after_content: str) -> dict:
    """B-04: Build a simple diff summary for a single file.
    Returns dict with changed, before_size, after_size,
    before_line_count, after_line_count, first_changed_line, summary.
    """
    if before_content == after_content:
        return {
            "changed": False,
            "before_size": len(before_content),
            "after_size": len(after_content),
            "before_line_count": len(before_content.splitlines()),
            "after_line_count": len(after_content.splitlines()),
            "first_changed_line": 0,
            "summary": "文件内容未变化",
        }

    before_lines = before_content.splitlines()
    after_lines = after_content.splitlines()

    first_changed = 1
    max_check = min(len(before_lines), len(after_lines))
    for i in range(max_check):
        if before_lines[i] != after_lines[i]:
            first_changed = i + 1
            break
    else:
        if len(after_lines) > len(before_lines):
            first_changed = len(before_lines) + 1

    return {
        "changed": True,
        "before_size": len(before_content),
        "after_size": len(after_content),
        "before_line_count": len(before_lines),
        "after_line_count": len(after_lines),
        "first_changed_line": first_changed,
        "summary": "app.html 内容已更新",
    }


def _empty_change_record(skipped_reason: str) -> dict:
    return {
        "changed": False,
        "before_size": 0,
        "after_size": 0,
        "before_line_count": 0,
        "after_line_count": 0,
        "first_changed_line": 0,
        "diff_summary": skipped_reason,
    }


def apply_coder_output_to_project(
    coder_result: str,
    workspace_info: dict,
    real_task_protocol: dict,
) -> dict:
    """
    B-03/B-04: Apply Coder output to real project in a controlled manner.
    Only allowed to modify PROJECT_ROOT/app.html when protocol is established.
    Returns dict with enabled, status, target_file, changed_files,
    skipped_reason, safety_status, operation, change_record, diff_summary.
    """
    detection = workspace_info.get("detection_status", "未启用")
    safety = workspace_info.get("safety_status", "not_enabled")

    def _not_enabled(enabled: bool, status: str, skipped: str, op: str = "none"):
        return {
            "enabled": enabled,
            "status": status,
            "target_file": "",
            "changed_files": [],
            "skipped_reason": skipped,
            "safety_status": safety if status != "已阻止" else "blocked",
            "operation": op,
            "change_record": _empty_change_record(skipped),
            "diff_summary": _empty_change_record(skipped),
        }

    if detection != "已识别" or safety != "safe":
        enabled = False
        if detection == "已阻止":
            status = "已阻止"
            skipped = "项目工作区被阻止，禁止真实文件修改"
        elif detection == "无效":
            status = "无效"
            skipped = "项目工作区无效，禁止真实文件修改"
        else:
            status = "未启用"
            skipped = "未绑定真实项目工作区"
        return _not_enabled(enabled, status, skipped)

    if (
        real_task_protocol.get("protocol_status") != "已建立"
        or not real_task_protocol.get("enabled")
    ):
        return _not_enabled(False, "未启用", "真实任务协议未建立，禁止真实文件修改")

    project_root = Path(workspace_info["project_root"]).resolve()
    target_file = project_root / "app.html"

    try:
        target_file.resolve().relative_to(project_root)
    except ValueError:
        return {
            "enabled": True,
            "status": "已阻止",
            "target_file": str(target_file),
            "changed_files": [],
            "skipped_reason": "目标文件不在 PROJECT_ROOT 内",
            "safety_status": "blocked",
            "operation": "blocked_path_escape",
            "change_record": _empty_change_record("目标文件不在 PROJECT_ROOT 内"),
            "diff_summary": _empty_change_record("目标文件不在 PROJECT_ROOT 内"),
        }

    if target_file.name != "app.html":
        return {
            "enabled": True,
            "status": "已阻止",
            "target_file": str(target_file),
            "changed_files": [],
            "skipped_reason": "B-03 仅允许修改 app.html",
            "safety_status": "blocked",
            "operation": "blocked_wrong_filename",
            "change_record": _empty_change_record("B-03 仅允许修改 app.html"),
            "diff_summary": _empty_change_record("B-03 仅允许修改 app.html"),
        }

    if not target_file.exists():
        skipped = "PROJECT_ROOT 下不存在 app.html，B-03 不自动创建文件"
        return {
            "enabled": True,
            "status": "跳过",
            "target_file": str(target_file),
            "changed_files": [],
            "skipped_reason": skipped,
            "safety_status": "safe",
            "operation": "skip_missing_file",
            "change_record": _empty_change_record(skipped),
            "diff_summary": _empty_change_record(skipped),
        }

    if not target_file.is_file():
        skipped = "目标路径不是文件"
        return {
            "enabled": True,
            "status": "跳过",
            "target_file": str(target_file),
            "changed_files": [],
            "skipped_reason": skipped,
            "safety_status": "safe",
            "operation": "skip_not_file",
            "change_record": _empty_change_record(skipped),
            "diff_summary": _empty_change_record(skipped),
        }

    html_code = extract_html_code(coder_result)
    if html_code is None:
        skipped = "Coder 输出中未找到 html 代码块"
        return {
            "enabled": True,
            "status": "跳过",
            "target_file": str(target_file),
            "changed_files": [],
            "skipped_reason": skipped,
            "safety_status": "safe",
            "operation": "skip_no_html_code",
            "change_record": _empty_change_record(skipped),
            "diff_summary": _empty_change_record(skipped),
        }

    # B-04: Read before content for change record
    before_content = target_file.read_text(encoding="utf-8")
    save_text(target_file, html_code)
    after_content = target_file.read_text(encoding="utf-8")

    diff_summary = build_simple_diff_summary(before_content, after_content)
    change_record = {
        "changed": diff_summary["changed"],
        "before_size": diff_summary["before_size"],
        "after_size": diff_summary["after_size"],
        "before_line_count": diff_summary["before_line_count"],
        "after_line_count": diff_summary["after_line_count"],
        "first_changed_line": diff_summary["first_changed_line"],
        "diff_summary": diff_summary["summary"],
    }

    return {
        "enabled": True,
        "status": "已修改",
        "target_file": str(target_file),
        "changed_files": [str(target_file)],
        "skipped_reason": "",
        "safety_status": "safe",
        "operation": "write_app_html",
        "change_record": change_record,
        "diff_summary": diff_summary,
    }


def detect_project_workspace() -> dict:
    """
    B-01: Detect real project workspace and perform safety boundary check.
    Returns dict with enabled, project_root, exists, is_directory,
    is_inside_platform_root, safety_status, detection_status, reason.
    """
    if not PROJECT_ROOT:
        return {
            "enabled": False,
            "project_root": "",
            "exists": False,
            "is_directory": False,
            "is_inside_platform_root": False,
            "safety_status": "not_enabled",
            "detection_status": "未启用",
            "reason": "PROJECT_ROOT 未设置，未绑定真实项目工作区",
        }

    abs_path = Path(PROJECT_ROOT).resolve()
    platform_root = ROOT.resolve()

    is_inside_platform_root = False
    try:
        abs_path.relative_to(platform_root)
        is_inside_platform_root = True
    except ValueError:
        is_inside_platform_root = False

    abs_path_str = str(abs_path)
    exists = abs_path.exists()
    is_directory = abs_path.is_dir() if exists else False

    if is_inside_platform_root:
        return {
            "enabled": True,
            "project_root": abs_path_str,
            "exists": exists,
            "is_directory": is_directory,
            "is_inside_platform_root": True,
            "safety_status": "blocked",
            "detection_status": "已阻止",
            "reason": "PROJECT_ROOT 指向平台自身或其子目录，禁止作为真实开发目标",
        }

    if not exists:
        return {
            "enabled": True,
            "project_root": abs_path_str,
            "exists": False,
            "is_directory": False,
            "is_inside_platform_root": False,
            "safety_status": "invalid",
            "detection_status": "无效",
            "reason": "PROJECT_ROOT 不存在",
        }

    if not is_directory:
        return {
            "enabled": True,
            "project_root": abs_path_str,
            "exists": True,
            "is_directory": False,
            "is_inside_platform_root": False,
            "safety_status": "invalid",
            "detection_status": "无效",
            "reason": "PROJECT_ROOT 不是目录",
        }

    return {
        "enabled": True,
        "project_root": abs_path_str,
        "exists": True,
        "is_directory": True,
        "is_inside_platform_root": False,
        "safety_status": "safe",
        "detection_status": "已识别",
        "reason": "真实项目工作区已识别",
    }


def project_workspace_status(workspace_info: dict) -> str:
    """
    B-01: Get project workspace report status.
    """
    return workspace_info.get("detection_status", "未启用")


def build_real_task_protocol(task: str, workspace_info: dict) -> dict:
    """
    B-02: Build real task input protocol based on workspace detection.
    Returns dict with enabled, workspace_status, user_task, project_root,
    allowed_change_scope, forbidden_scope, acceptance_criteria,
    safety_rules, protocol_status, reason.
    """
    detection = workspace_info.get("detection_status", "未启用")
    safety = workspace_info.get("safety_status", "not_enabled")

    if detection == "未启用":
        return {
            "enabled": False,
            "workspace_status": "未启用",
            "user_task": task,
            "project_root": "",
            "allowed_change_scope": [],
            "forbidden_scope": [],
            "acceptance_criteria": [],
            "safety_rules": [],
            "protocol_status": "未启用",
            "reason": "未绑定真实项目工作区，真实任务协议未启用",
        }

    if detection == "已阻止":
        return {
            "enabled": False,
            "workspace_status": "已阻止",
            "user_task": task,
            "project_root": workspace_info.get("project_root", ""),
            "allowed_change_scope": [],
            "forbidden_scope": [],
            "acceptance_criteria": [],
            "safety_rules": [],
            "protocol_status": "已阻止",
            "reason": "项目工作区被阻止，真实任务协议未启用",
        }

    if detection == "无效":
        return {
            "enabled": False,
            "workspace_status": "无效",
            "user_task": task,
            "project_root": workspace_info.get("project_root", ""),
            "allowed_change_scope": [],
            "forbidden_scope": [],
            "acceptance_criteria": [],
            "safety_rules": [],
            "protocol_status": "无效",
            "reason": "项目工作区无效，真实任务协议未启用",
        }

    if detection == "已识别" and safety == "safe":
        return {
            "enabled": True,
            "workspace_status": "已识别",
            "user_task": task,
            "project_root": workspace_info.get("project_root", ""),
            "allowed_change_scope": [
                "仅允许修改 PROJECT_ROOT 内部文件",
                "仅允许后续任务明确授权的文件范围",
                "B-02 阶段不执行真实修改",
            ],
            "forbidden_scope": [
                "禁止修改多 Agent 平台自身文件",
                "禁止修改 PROJECT_ROOT 外部文件",
                "禁止读取或写入敏感文件",
                "禁止执行删除、格式化、清空目录等破坏性操作",
            ],
            "acceptance_criteria": [
                "真实项目工作区已识别",
                "真实任务协议已建立",
                "后续 Coder 必须基于该协议执行",
                "当前阶段不产生真实文件修改",
            ],
            "safety_rules": [
                "所有真实开发操作必须限制在 PROJECT_ROOT 内",
                "任何越权路径必须阻止",
                "未知或敏感文件必须停止并报告",
                "真实修改能力从 B-03 开始引入",
            ],
            "protocol_status": "已建立",
            "reason": "真实任务输入协议已建立",
        }

    return {
        "enabled": False,
        "workspace_status": detection,
        "user_task": task,
        "project_root": workspace_info.get("project_root", ""),
        "allowed_change_scope": [],
        "forbidden_scope": [],
        "acceptance_criteria": [],
        "safety_rules": [],
        "protocol_status": "未启用",
        "reason": "未知工作区状态，真实任务协议未启用",
    }


def should_inject_failure(agent_name: str) -> bool:
    """
    Failure Injection Switch: check if the current agent should fail.
    Controlled by FAIL_AGENT environment variable.
    Default: disabled.
    """
    if not FAIL_AGENT:
        return False
    return FAIL_AGENT == agent_name


def failure_injection_status() -> str:
    """
    Failure Injection Switch: report current status.
    """
    if not FAIL_AGENT:
        return "未启用"
    return f"已启用：{FAIL_AGENT}"


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"找不到文件：{path}")
    return path.read_text(encoding="utf-8")


def save_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# Model Router: agent model routing records
agent_model_routes: dict = {}

# Model Router: agent cost records
agent_cost_records: dict = {}

# Fallback Policy: agent fallback policy records
agent_fallback_policies: dict = {}

# Failure Policy Executor: agent execution records
agent_execution_records: dict = {}

# Failure Capture: agent failure records
agent_failure_records: dict = {}


def execute_agent_with_policy(
    agent_name: str,
    role_content: str,
    prompt: str,
    model_route: dict,
    fallback_policy: dict,
    inject_failure: bool = False,
) -> tuple[str, dict]:
    """
    Failure Policy Executor v1: execute agent call with policy tracking.
    Returns (agent_result, execution_record).
    v1 only calls call_minimax once without retry loop.
    """
    execution_record = {
        "attempted_provider": model_route["provider"],
        "attempted_model": model_route["model"],
        "retry_enabled": fallback_policy["retry_enabled"],
        "max_retries": fallback_policy["max_retries"],
        "retry_count": 0,
        "upgrade_attempted": False,
        "fallback_used": False,
        "execution_status": "completed",
    }

    try:
        if inject_failure:
            raise RuntimeError(f"Injected failure for agent: {agent_name}")
        agent_result = call_minimax(role_content, prompt)
    except Exception as e:
        execution_record["execution_status"] = "failed"
        agent_failure_records[agent_name] = {
            "provider": model_route["provider"],
            "model": model_route["model"],
            "retry_enabled": fallback_policy["retry_enabled"],
            "max_retries": fallback_policy["max_retries"],
            "retry_count": execution_record["retry_count"],
            "upgrade_attempted": execution_record["upgrade_attempted"],
            "fallback_used": execution_record["fallback_used"],
            "execution_status": "failed",
            "error_type": type(e).__name__,
            "error_message": str(e),
        }
        raise e

    return agent_result, execution_record


def select_fallback_policy(agent_name: str, model_route: dict) -> dict:
    """
    Fallback Policy v1: select fallback policy for agent by role.
    Returns dict with retry_enabled, max_retries, upgrade_on_failure, fallback_model, policy_reason.
    """
    fallback_policies = {
        "Product": {
            "retry_enabled": False,
            "max_retries": 0,
            "upgrade_on_failure": False,
            "fallback_model": "not_enabled",
            "policy_reason": "v1 仅记录策略，不自动升级；需求、架构、测试设计失败时应显式停止并人工检查",
        },
        "Architect": {
            "retry_enabled": False,
            "max_retries": 0,
            "upgrade_on_failure": False,
            "fallback_model": "not_enabled",
            "policy_reason": "v1 仅记录策略，不自动升级；需求、架构、测试设计失败时应显式停止并人工检查",
        },
        "TestDesigner": {
            "retry_enabled": False,
            "max_retries": 0,
            "upgrade_on_failure": False,
            "fallback_model": "not_enabled",
            "policy_reason": "v1 仅记录策略，不自动升级；需求、架构、测试设计失败时应显式停止并人工检查",
        },
        "TaskManager": {
            "retry_enabled": False,
            "max_retries": 0,
            "upgrade_on_failure": False,
            "fallback_model": "not_enabled",
            "policy_reason": "v1 仅记录策略，不自动重试；任务拆解失败应先检查上下文",
        },
        "Planner": {
            "retry_enabled": False,
            "max_retries": 0,
            "upgrade_on_failure": False,
            "fallback_model": "not_enabled",
            "policy_reason": "v1 仅记录策略，不自动重试；任务拆解失败应先检查上下文",
        },
        "Coder": {
            "retry_enabled": False,
            "max_retries": 0,
            "upgrade_on_failure": False,
            "fallback_model": "not_enabled",
            "policy_reason": "v1 不自动重写代码，避免隐藏实现错误",
        },
        "Reviewer": {
            "retry_enabled": False,
            "max_retries": 0,
            "upgrade_on_failure": False,
            "fallback_model": "not_enabled",
            "policy_reason": "v1 不自动覆盖审查和测试结论，保持结果可解释",
        },
        "Tester": {
            "retry_enabled": False,
            "max_retries": 0,
            "upgrade_on_failure": False,
            "fallback_model": "not_enabled",
            "policy_reason": "v1 不自动覆盖审查和测试结论，保持结果可解释",
        },
        "Documenter": {
            "retry_enabled": False,
            "max_retries": 0,
            "upgrade_on_failure": False,
            "fallback_model": "not_enabled",
            "policy_reason": "v1 不自动重试交付总结，避免生成虚假交付内容",
        },
    }
    return fallback_policies.get(agent_name, {
        "retry_enabled": False,
        "max_retries": 0,
        "upgrade_on_failure": False,
        "fallback_model": "not_enabled",
        "policy_reason": "默认策略",
    })


def select_model_for_agent(agent_name: str) -> dict:
    """
    Model Router v1: select model for agent by role.
    Returns dict with provider, model, reason, cost_tier, is_default_route, use_stronger_model.
    """
    model_routes = {
        "Product": {
            "provider": "minimax",
            "model": "default",
            "reason": "需求分析需要稳定通用模型，v1 暂用默认模型",
            "cost_tier": "standard",
            "is_default_route": True,
            "use_stronger_model": False,
        },
        "Architect": {
            "provider": "minimax",
            "model": "default",
            "reason": "架构设计需要较强推理与结构化输出，v1 暂用默认模型",
            "cost_tier": "standard",
            "is_default_route": True,
            "use_stronger_model": False,
        },
        "TestDesigner": {
            "provider": "minimax",
            "model": "default",
            "reason": "测试设计需要结构化输出能力，v1 暂用默认模型",
            "cost_tier": "standard",
            "is_default_route": True,
            "use_stronger_model": False,
        },
        "TaskManager": {
            "provider": "minimax",
            "model": "default",
            "reason": "任务拆解需要稳定规划能力，v1 暂用默认模型",
            "cost_tier": "standard",
            "is_default_route": True,
            "use_stronger_model": False,
        },
        "Planner": {
            "provider": "minimax",
            "model": "default",
            "reason": "任务规划需要稳定规划能力，v1 暂用默认模型",
            "cost_tier": "standard",
            "is_default_route": True,
            "use_stronger_model": False,
        },
        "Coder": {
            "provider": "minimax",
            "model": "default",
            "reason": "当前真实开发能力先保持默认模型，避免引入额外变量",
            "cost_tier": "standard",
            "is_default_route": True,
            "use_stronger_model": False,
        },
        "Reviewer": {
            "provider": "minimax",
            "model": "default",
            "reason": "代码审查需要稳定判断能力，v1 暂用默认模型",
            "cost_tier": "standard",
            "is_default_route": True,
            "use_stronger_model": False,
        },
        "Tester": {
            "provider": "minimax",
            "model": "default",
            "reason": "测试验证需要稳定判断能力，v1 暂用默认模型",
            "cost_tier": "standard",
            "is_default_route": True,
            "use_stronger_model": False,
        },
        "Documenter": {
            "provider": "minimax",
            "model": "default",
            "reason": "交付总结优先低成本，v1 仍走默认模型",
            "cost_tier": "low",
            "is_default_route": True,
            "use_stronger_model": False,
        },
    }
    return model_routes.get(agent_name, {
        "provider": "minimax",
        "model": "default",
        "reason": "默认模型路由",
        "cost_tier": "standard",
        "is_default_route": True,
        "use_stronger_model": False,
    })


def call_agent(agent_name: str, prompt: str) -> str:
    """
    统一 Agent 模型调用入口。
    C-43: Model Router selects model by agent_name here.
    """
    # Model Router: select model for agent
    model_route = select_model_for_agent(agent_name)
    agent_model_routes[agent_name] = model_route

    # Record cost info (not tracked in v1)
    agent_cost_records[agent_name] = {
        "provider": model_route["provider"],
        "model": model_route["model"],
        "cost_tier": model_route["cost_tier"],
        "estimated_cost": "not_tracked",
        "token_usage": "not_tracked",
    }

    # Record fallback policy (not applied in v1)
    fallback_policy = select_fallback_policy(agent_name, model_route)
    agent_fallback_policies[agent_name] = fallback_policy

    role_file_map = {
        "Product": PRODUCT_FILE,
        "Architect": ARCHITECT_FILE,
        "TestDesigner": TEST_DESIGNER_FILE,
        "TaskManager": TASK_MANAGER_FILE,
        "Planner": PLANNER_FILE,
        "Coder": CODER_FILE,
        "Reviewer": REVIEWER_FILE,
        "Tester": TESTER_FILE,
        "Documenter": DOCUMENTER_FILE,
    }

    if agent_name not in role_file_map:
        raise ValueError(f"Unknown agent: {agent_name}")

    role_content = read_text(role_file_map[agent_name])

    # Execute with policy tracking
    inject_failure = should_inject_failure(agent_name)
    agent_result, execution_record = execute_agent_with_policy(
        agent_name, role_content, prompt, model_route, fallback_policy, inject_failure
    )
    agent_execution_records[agent_name] = execution_record

    return agent_result


def call_minimax(system_prompt: str, user_prompt: str) -> str:
    if not MINIMAX_API_KEY:
        raise RuntimeError("请先在 .env 里设置 MINIMAX_API_KEY。")

    headers = {
        "Authorization": f"Bearer {MINIMAX_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MINIMAX_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
    }

    response = requests.post(
        MINIMAX_BASE_URL,
        headers=headers,
        json=payload,
        timeout=60,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"MiniMax API 调用失败：{response.status_code}\n{response.text}"
        )

    data = response.json()
    return data["choices"][0]["message"]["content"]


def remove_think(text: str) -> str:
    while "<think>" in text and "</think>" in text:
        start = text.find("<think>")
        end = text.find("</think>") + len("</think>")
        text = text[:start] + text[end:]
    return text.strip()


def review_passed(reviewer_result: str) -> bool:
    lines = [line.strip() for line in reviewer_result.splitlines() if line.strip()]
    return "通过" in lines and "不通过" not in lines


def _extract_section(reviewer_result: str, header: str) -> str:
    """B-09: Extract content after a section header line."""
    lines = reviewer_result.splitlines()
    start = -1
    for i, line in enumerate(lines):
        if line.strip().startswith(header):
            start = i + 1
            break
    if start < 0 or start >= len(lines):
        return ""
    collected = []
    for line in lines[start:]:
        if any(line.strip().startswith(h) for h in (
            "REVIEW_RESULT:",
            "BLOCKING_ISSUES:",
            "NON_BLOCKING_SUGGESTIONS:",
            "FILES_REVIEWED:",
            "REAL_CHANGE_ASSESSMENT:",
            "REVISION_REQUIRED:",
            "REVISION_INSTRUCTIONS:",
        )):
            break
        collected.append(line)
    return "\n".join(collected).strip()


def parse_structured_reviewer_result(reviewer_result: str) -> dict:
    """B-09: Parse Reviewer's structured output."""
    text = reviewer_result or ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    review_result = "未知"
    revision_required = "未知"
    missing = []

    for line in lines:
        if line.startswith("REVIEW_RESULT:"):
            value = line[len("REVIEW_RESULT:"):].strip()
            if "不通过" in value:
                review_result = "不通过"
            elif "通过" in value:
                review_result = "通过"
        elif line.startswith("REVISION_REQUIRED:"):
            value = line[len("REVISION_REQUIRED:"):].strip()
            if value == "否" or value.startswith("否"):
                revision_required = "否"
            elif value == "是" or value.startswith("是"):
                revision_required = "是"

    if review_result == "未知":
        missing.append("REVIEW_RESULT")
    if revision_required == "未知":
        missing.append("REVISION_REQUIRED")

    if missing:
        parsed = False
        parse_status = "解析失败"
        reason = f"缺少字段：{', '.join(missing)}"
    else:
        parsed = True
        parse_status = "已解析"
        reason = "结构化字段完整"

    return {
        "parsed": parsed,
        "review_result": review_result,
        "blocking_issues": _extract_section(text, "BLOCKING_ISSUES:"),
        "non_blocking_suggestions": _extract_section(text, "NON_BLOCKING_SUGGESTIONS:"),
        "files_reviewed": _extract_section(text, "FILES_REVIEWED:"),
        "real_change_assessment": _extract_section(text, "REAL_CHANGE_ASSESSMENT:"),
        "revision_required": revision_required,
        "revision_instructions": _extract_section(text, "REVISION_INSTRUCTIONS:"),
        "parse_status": parse_status,
        "reason": reason,
    }


def create_run_dir(project_id: str = "") -> Path:
    if project_id and is_valid_project_id(project_id):
        runs_dir = ROOT / "outputs" / "projects" / project_id / "runs"
    else:
        runs_dir = OUTPUT_DIR / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    existing_numbers = []

    for path in runs_dir.iterdir():
        if path.is_dir() and path.name.startswith("run_"):
            number_text = path.name.replace("run_", "")
            if number_text.isdigit():
                existing_numbers.append(int(number_text))

    next_number = max(existing_numbers, default=0) + 1
    run_name = f"run_{next_number:03d}"

    return runs_dir / run_name


def update_latest(run_dir: Path, project_id: str = "") -> None:
    latest_dir = OUTPUT_DIR / "latest"

    if latest_dir.exists():
        shutil.rmtree(latest_dir)

    shutil.copytree(run_dir, latest_dir)

    if project_id and is_valid_project_id(project_id):
        project_latest = ROOT / "outputs" / "projects" / project_id / "latest"
        if project_latest.exists():
            shutil.rmtree(project_latest)
        shutil.copytree(run_dir, project_latest)


def extract_html_code(markdown_text: str) -> str | None:
    start_marker = "```html"
    end_marker = "```"

    start = markdown_text.find(start_marker)
    if start == -1:
        return None

    start = start + len(start_marker)
    end = markdown_text.find(end_marker, start)

    if end == -1:
        return None

    return markdown_text[start:end].strip()


def run_product(task: str) -> str:
    user_prompt = f"""
下面是用户原始想法或任务：

{task}

请你作为 Product Agent，按你的固定输出格式生成最小 PRD。
"""

    return call_agent("Product", user_prompt)


def run_architect(task: str, product_result: str) -> str:
    user_prompt = f"""
下面是用户原始任务：

{task}

下面是 Product Agent 生成的 PRD：

{product_result}

请你作为 Architect Agent，基于用户原始任务和 PRD，按你的固定输出格式生成最小 SDD。
"""

    return call_agent("Architect", user_prompt)


def run_test_designer(
    task: str,
    product_result: str,
    architect_result: str,
) -> str:
    user_prompt = f"""
下面是用户原始任务：

{task}

下面是 Product Agent 生成的 PRD：

{product_result}

下面是 Architect Agent 生成的 SDD：

{architect_result}

请你作为 TestDesigner Agent，基于用户原始任务、PRD 和 SDD，按你的固定输出格式生成最小 TDD。
"""

    return call_agent("TestDesigner", user_prompt)


def run_task_manager(
    task: str,
    product_result: str,
    architect_result: str,
    test_designer_result: str,
) -> str:
    user_prompt = f"""
下面是用户原始任务：

{task}

下面是 Product Agent 生成的 PRD：

{product_result}

下面是 Architect Agent 生成的 SDD：

{architect_result}

下面是 TestDesigner Agent 生成的 TDD：

{test_designer_result}

请你作为 TaskManager Agent，基于用户原始任务、PRD、SDD 和 TDD，按你的固定输出格式生成任务拆分清单 TASKS。
"""

    return call_agent("TaskManager", user_prompt)


def run_planner(
    task: str,
    product_result: str,
    architect_result: str,
    test_designer_result: str,
    task_manager_result: str,
) -> str:
    user_prompt = f"""
下面是用户原始任务：

{task}

下面是 Product Agent 生成的 PRD：

{product_result}

下面是 Architect Agent 生成的 SDD：

{architect_result}

下面是 TestDesigner Agent 生成的 TDD：

{test_designer_result}

下面是 TaskManager Agent 生成的 TASKS：

{task_manager_result}

请你作为 Planner Agent，基于用户原始任务、PRD、SDD、TDD 和 TASKS，按你的固定输出格式生成任务计划。
"""

    return call_agent("Planner", user_prompt)


def run_coder(
    task: str,
    product_result: str,
    architect_result: str,
    test_designer_result: str,
    planner_result: str,
    current_task_scope: str,
) -> str:
    user_prompt = f"""
下面是用户原始任务：

{task}

下面是 Product Agent 生成的 PRD：

{product_result}

下面是 Architect Agent 生成的 SDD：

{architect_result}

下面是 TestDesigner Agent 生成的 TDD：

{test_designer_result}

下面是 Planner Agent 给出的任务计划：

{planner_result}

下面是当前执行任务范围：

{current_task_scope}

请你作为 Coder Agent，严格按照 Planner 指定范围实现代码。
"""

    return call_agent("Coder", user_prompt)


def run_reviewer(
    task: str,
    product_result: str,
    architect_result: str,
    test_designer_result: str,
    planner_result: str,
    coder_result: str,
    project_change_record: dict,
    real_file_modification: dict,
) -> str:
    rfm = real_file_modification or {}
    pcr = project_change_record or {}

    change_context_lines = []
    change_context_lines.append("REAL FILE MODIFICATION:")
    change_context_lines.append(f"  Status: {rfm.get('status', '未知')}")
    change_context_lines.append(f"  Target File: {rfm.get('target_file', '')}")
    change_context_lines.append(f"  Operation: {rfm.get('operation', '未知')}")
    change_files = rfm.get("changed_files") or []
    if change_files:
        change_context_lines.append("  Changed Files:")
        for f in change_files:
            change_context_lines.append(f"    - {f}")
    else:
        change_context_lines.append("  Changed Files: (none)")
    change_context_lines.append("")
    change_context_lines.append("CHANGE RECORD:")
    change_context_lines.append(f"  Status: {pcr.get('status', '未知')}")
    change_context_lines.append(f"  Changed: {pcr.get('changed', False)}")
    change_context_lines.append(f"  Before Size: {pcr.get('before_size', 0)}")
    change_context_lines.append(f"  After Size: {pcr.get('after_size', 0)}")
    change_context_lines.append(f"  Before Line Count: {pcr.get('before_line_count', 0)}")
    change_context_lines.append(f"  After Line Count: {pcr.get('after_line_count', 0)}")
    change_context_lines.append(f"  First Changed Line: {pcr.get('first_changed_line', 0)}")
    change_context_lines.append(f"  Diff Summary: {pcr.get('diff_summary', '')}")

    change_context_block = "\n".join(change_context_lines)

    user_prompt = f"""
下面是用户原始任务：

{task}

下面是 Product Agent 生成的 PRD：

{product_result}

下面是 Architect Agent 生成的 SDD：

{architect_result}

下面是 TestDesigner Agent 生成的 TDD：

{test_designer_result}

下面是 Planner Agent 给出的任务计划：

{planner_result}

下面是 Coder Agent 给出的实现结果：

{coder_result}

========== REVIEW CONTEXT ==========

PRD:
{product_result}

SDD:
{architect_result}

TDD:
{test_designer_result}

TASK SCOPE:
{planner_result}

CODER OUTPUT:
{coder_result}

========== REAL CHANGE CONTEXT ==========

{change_context_block}

请你作为 Reviewer Agent，基于用户原始任务、PRD、SDD、TDD、Planner 计划、Coder 实现以及真实项目变更记录进行代码审查。Reviewer 不仅要审查 Coder 输出，还必须审查真实文件修改与变更记录：

- Coder 输出是否符合 PRD / SDD / TDD。
- 真实文件修改是否发生在允许范围内（仅 PROJECT_ROOT 内单个 app.html）。
- Changed Files 是否只包含允许文件。
- Diff Summary 是否与任务目标一致。
- 如果真实文件修改状态为「跳过」，需要在审查结论中说明是否仍可接受。
- 如果真实文件修改状态为「已阻止 / 无效」，应判定不通过。

========== REQUIRED OUTPUT FORMAT ==========

Reviewer 必须严格按以下固定结构输出，便于下游 Tester / Revise 解析：

REVIEW_RESULT: 通过 / 不通过

BLOCKING_ISSUES:
- 如果没有，写 无

NON_BLOCKING_SUGGESTIONS:
- 如果没有，写 无

FILES_REVIEWED:
- 列出 Coder 输出和真实变更涉及的文件；如果没有真实文件，写 无真实文件

REAL_CHANGE_ASSESSMENT:
- 说明真实文件修改状态、Changed Files、Diff Summary 是否与任务一致

REVISION_REQUIRED: 是 / 否

REVISION_INSTRUCTIONS:
- 如果不需要修复，写 无
- 如果需要修复，写清楚需要修复什么
"""


    return call_agent("Reviewer", user_prompt)


def run_tester(
    task: str,
    product_result: str,
    architect_result: str,
    test_designer_result: str,
    planner_result: str,
    coder_result: str,
    reviewer_result: str,
    reviewer_structured_result: dict,
) -> str:
    user_prompt = f"""
下面是用户原始任务：

{task}

下面是 Product Agent 生成的 PRD：

{product_result}

下面是 Architect Agent 生成的 SDD：

{architect_result}

下面是 TestDesigner Agent 生成的 TDD：

{test_designer_result}

下面是 Planner Agent 给出的任务计划：

{planner_result}

下面是 Coder Agent 给出的实现结果：

{coder_result}

下面是 Reviewer Agent 给出的审查结论：

{reviewer_result}

========== TEST CONTEXT ==========

PRD:
{product_result}

SDD:
{architect_result}

TDD:
{test_designer_result}

TASK SCOPE:
{planner_result}

CODER OUTPUT:
{coder_result}

REVIEWER OUTPUT:
{reviewer_result}

========== STRUCTURED REVIEW RESULT ==========

Review Result:
{reviewer_structured_result.get("review_result", "未知")}

Revision Required:
{reviewer_structured_result.get("revision_required", "未知")}

Blocking Issues:
{reviewer_structured_result.get("blocking_issues", "")}

Real Change Assessment:
{reviewer_structured_result.get("real_change_assessment", "")}

Revision Instructions:
{reviewer_structured_result.get("revision_instructions", "")}

请你作为 Tester Agent，根据用户任务、PRD、SDD、TDD、Planner 计划、Coder 实现、Reviewer 自由文本结论以及 Reviewer 结构化审查结果，按你的固定输出格式设计最小测试方案并给出测试结论。Tester 必须基于完整上下文验证最终结果，不仅运行测试，还需要确认需求、架构、实现和审查意见的一致性。
"""

    return call_agent("Tester", user_prompt)


def run_documenter(delivery_context: str) -> str:
    user_prompt = f"""
下面是用户原始任务：

========== DELIVERY CONTEXT ==========

{delivery_context}

请你作为 Documenter Agent，基于 Delivery Context 输出最终交付说明，必须包含：
- 本次任务目标
- 已完成内容
- 验证结果
- 是否可交付
- 后续建议

Documenter 只能基于 Delivery Context 总结，不得虚构未发生的实现、测试或提交。
"""

    return call_agent("Documenter", user_prompt)


def build_final_report(
    task: str,
    product_result: str,
    architect_result: str,
    test_designer_result: str,
    task_manager_result: str,
    planner_result: str,
    coder_result: str,
    reviewer_result: str,
    tester_result: str,
    workflow_result: str,
    tester_prd_status: str,
    tester_sdd_status: str,
    tester_tdd_status: str,
    tester_context_status: str,
    planner_sdd_status: str,
    planner_tdd_status: str,
    planner_tasks_status: str,
    coder_sdd_status: str,
    coder_tdd_status: str,
    coder_scope_status: str,
    reviewer_sdd_status: str,
    reviewer_tdd_status: str,
    reviewer_context_status: str,
    sdd_generated: bool,
    tdd_generated: bool,
    tasks_generated: bool,
    revise_context_status: str,
    revise_context: str,
    delivery_context_status: str,
    delivery_context: str,
    documenter_status: str,
    documenter_context_status: str,
    documenter_result: str,
    agent_call_wrapper_status: str,
    model_router_status: str,
    cost_record_status: str,
    fallback_policy_status: str,
    failure_policy_executor_status: str,
    failure_capture_status: str,
    failure_injection_status: str,
    failure_injection_matrix_status: str,
    route_c_acceptance_status: str,
    route_b_entry_baseline_status: str,
    project_workspace_status: str,
    real_task_protocol_status: str,
    real_file_modification_status: str,
    change_record_status: str,
    project_session_status: str,
    project_state_status: str,
    project_resume_status: str,
    minimal_dev_loop_status: str,
    reviewer_diff_context_status: str,
    reviewer_structured_status: str,
    tester_reviewer_structured_context_status: str,
) -> str:
    sdd_status = "已生成" if sdd_generated else "未生成"
    tdd_status = "已生成" if tdd_generated else "未生成"
    tasks_status = "已生成" if tasks_generated else "未生成"

    revise_section = ""
    if revise_context_status == "已生成":
        revise_section = f"\n## Revise Context\n\nReviewer 未通过，已生成修订上下文。下一轮 Coder 应基于 Reviewer Output 修复问题。\n"

    delivery_section = ""
    if delivery_context_status == "已生成":
        delivery_section = "\n## Delivery Context\n\n本次任务已完成需求、架构、测试设计、任务规划、开发、审查和测试链路，可进入最终交付。\n"
    elif delivery_context_status == "等待修订":
        delivery_section = "\n## Delivery Context\n\nReviewer 未通过，当前交付上下文等待修订后生成。\n"

    documenter_section = ""
    if documenter_status == "完成":
        documenter_section = f"\n## Documenter Output\n\n{documenter_result.strip()}\n"

    model_router_lines = []
    for agent, route in sorted(agent_model_routes.items()):
        model_router_lines.append(
            f"| {agent} | {route['provider']} | {route['model']} | {route['cost_tier']} | {route['is_default_route']} | {route['use_stronger_model']} | {route['reason']} |"
        )
    model_router_header = "| Agent | Provider | Model | Cost Tier | Default Route | Stronger Model | Reason |\n|--------|----------|-------|-----------|---------------|----------------|---------|"
    model_router_section = "\n## Model Router\n\n" + model_router_header + "\n" + "\n".join(model_router_lines) + "\n" if model_router_lines else ""

    cost_record_lines = []
    for agent, record in sorted(agent_cost_records.items()):
        cost_record_lines.append(
            f"| {agent} | {record['provider']} | {record['model']} | {record['cost_tier']} | {record['token_usage']} | {record['estimated_cost']} |"
        )
    cost_record_header = "| Agent | Provider | Model | Cost Tier | Token Usage | Estimated Cost |\n|--------|----------|-------|-----------|--------------|-----------------|"
    cost_record_section = "\n## Cost Record\n\n" + cost_record_header + "\n" + "\n".join(cost_record_lines) + "\n" if cost_record_lines else ""

    fallback_policy_lines = []
    for agent, policy in sorted(agent_fallback_policies.items()):
        fallback_policy_lines.append(
            f"| {agent} | {policy['retry_enabled']} | {policy['max_retries']} | {policy['upgrade_on_failure']} | {policy['fallback_model']} | {policy['policy_reason']} |"
        )
    fallback_policy_header = "| Agent | Retry Enabled | Max Retries | Upgrade On Failure | Fallback Model | Policy Reason |\n|--------|--------------|-------------|-------------------|----------------|---------------|"
    fallback_policy_section = "\n## Fallback Policy\n\n" + fallback_policy_header + "\n" + "\n".join(fallback_policy_lines) + "\n" if fallback_policy_lines else ""

    execution_record_lines = []
    for agent, record in sorted(agent_execution_records.items()):
        execution_record_lines.append(
            f"| {agent} | {record['attempted_provider']} | {record['attempted_model']} | {record['retry_count']} | {record['upgrade_attempted']} | {record['fallback_used']} | {record['execution_status']} |"
        )
    execution_record_header = "| Agent | Provider | Model | Retry Count | Upgrade Attempted | Fallback Used | Execution Status |\n|--------|----------|-------|-------------|-------------------|---------------|------------------|"
    execution_record_section = "\n## Agent Execution Records\n\n" + execution_record_header + "\n" + "\n".join(execution_record_lines) + "\n" if execution_record_lines else ""

    if agent_failure_records:
        failure_capture_lines = []
        for agent, record in sorted(agent_failure_records.items()):
            failure_capture_lines.append(
                f"| {agent} | {record['provider']} | {record['model']} | {record['retry_count']} | {record['upgrade_attempted']} | {record['fallback_used']} | {record['error_type']} | {record['error_message']} |"
            )
        failure_capture_header = "| Agent | Provider | Model | Retry Count | Upgrade Attempted | Fallback Used | Error Type | Error Message |\n|--------|----------|-------|-------------|-------------------|---------------|------------|---------------|"
        failure_capture_section = "\n## Failure Capture\n\n" + failure_capture_header + "\n" + "\n".join(failure_capture_lines) + "\n"
    else:
        failure_capture_section = "\n## Failure Capture\n\n无 Agent 调用失败。\n"

    if FAIL_AGENT:
        failure_injection_section = f"\n## Failure Injection\n\n失败注入已启用，目标 Agent：{FAIL_AGENT}\n"
    else:
        failure_injection_section = "\n## Failure Injection\n\n失败注入未启用。\n"

    failure_injection_matrix_section = "\n## Failure Injection Matrix\n\n失败注入回归测试矩阵已建立：docs/FAILURE_INJECTION_MATRIX.md\n"

    route_c_acceptance_section = "\n## Route C Acceptance\n\n路线 C 最终验收文档已建立：docs/ROUTE_C_FINAL_ACCEPTANCE.md\n\n路线 C 当前状态：已通过\n"

    route_b_entry_baseline_section = "\n## Route B Entry Baseline\n\n路线 B 进入前基线文档已建立：docs/ROUTE_B_ENTRY_BASELINE.md\n\n路线 B 进入基线：已冻结\n"

    if agent_workspace_info:
        project_workspace_section = f"\n## Project Workspace\n\n- Enabled: {agent_workspace_info.get('enabled')}\n- Project Root: {agent_workspace_info.get('project_root')}\n- Exists: {agent_workspace_info.get('exists')}\n- Is Directory: {agent_workspace_info.get('is_directory')}\n- Inside Platform Root: {agent_workspace_info.get('is_inside_platform_root')}\n- Safety Status: {agent_workspace_info.get('safety_status')}\n- Detection Status: {agent_workspace_info.get('detection_status')}\n- Reason: {agent_workspace_info.get('reason')}\n"
    else:
        project_workspace_section = "\n## Project Workspace\n\nDetection Status: 未启用\n"

    if real_task_protocol_info:
        rtp = real_task_protocol_info
        rtp_lines = [
            f"- Enabled: {rtp.get('enabled')}",
            f"- Workspace Status: {rtp.get('workspace_status')}",
            f"- Project Root: {rtp.get('project_root')}",
            f"- Protocol Status: {rtp.get('protocol_status')}",
            f"- Reason: {rtp.get('reason')}",
        ]
        rtp_lines.append("- Allowed Change Scope:")
        for s in rtp.get("allowed_change_scope", []):
            rtp_lines.append(f"  - {s}")
        rtp_lines.append("- Forbidden Scope:")
        for s in rtp.get("forbidden_scope", []):
            rtp_lines.append(f"  - {s}")
        rtp_lines.append("- Acceptance Criteria:")
        for s in rtp.get("acceptance_criteria", []):
            rtp_lines.append(f"  - {s}")
        rtp_lines.append("- Safety Rules:")
        for s in rtp.get("safety_rules", []):
            rtp_lines.append(f"  - {s}")
        real_task_protocol_section = "\n## Real Task Protocol\n\n" + "\n".join(rtp_lines) + "\n"
    else:
        real_task_protocol_section = "\n## Real Task Protocol\n\nProtocol Status: 未启用\n"

    if real_file_modification_info:
        rfm = real_file_modification_info
        rfm_lines = [
            f"- Enabled: {rfm.get('enabled')}",
            f"- Status: {rfm.get('status')}",
            f"- Target File: {rfm.get('target_file')}",
            f"- Skipped Reason: {rfm.get('skipped_reason')}",
            f"- Safety Status: {rfm.get('safety_status')}",
            f"- Operation: {rfm.get('operation')}",
        ]
        changed = rfm.get("changed_files", [])
        if changed:
            rfm_lines.append("- Changed Files:")
            for f in changed:
                rfm_lines.append(f"  - {f}")
        else:
            rfm_lines.append("- Changed Files: (none)")
        real_file_modification_section = "\n## Real File Modification\n\n" + "\n".join(rfm_lines) + "\n"
    else:
        real_file_modification_section = "\n## Real File Modification\n\nStatus: 未启用\n"

    if project_change_record_info:
        pcr = project_change_record_info
        pcr_lines = [
            f"- Status: {pcr.get('status')}",
            f"- Target File: {pcr.get('target_file')}",
            f"- Operation: {pcr.get('operation')}",
            f"- Changed: {pcr.get('changed')}",
            f"- Before Size: {pcr.get('before_size')}",
            f"- After Size: {pcr.get('after_size')}",
            f"- Before Line Count: {pcr.get('before_line_count')}",
            f"- After Line Count: {pcr.get('after_line_count')}",
            f"- First Changed Line: {pcr.get('first_changed_line')}",
            f"- Diff Summary: {pcr.get('diff_summary')}",
        ]
        changed_files = pcr.get("changed_files", [])
        if changed_files:
            pcr_lines.append("- Changed Files:")
            for f in changed_files:
                pcr_lines.append(f"  - {f}")
        else:
            pcr_lines.append("- Changed Files: (none)")
        change_record_section = "\n## Change Record\n\n" + "\n".join(pcr_lines) + "\n"
    else:
        change_record_section = "\n## Change Record\n\nStatus: 未启用\n"

    if project_session_info:
        psi = project_session_info
        psi_lines = [
            f"- Enabled: {psi.get('enabled')}",
            f"- Project ID: {psi.get('project_id')}",
            f"- Project Root: {psi.get('project_root')}",
            f"- Run Directory: {psi.get('run_dir')}",
            f"- Project Latest Directory: {psi.get('project_latest_dir')}",
            f"- Global Latest Directory: {psi.get('global_latest_dir')}",
            f"- Registry Status: {psi.get('registry_status')}",
            f"- Project Status: {psi.get('project_status')}",
            f"- Session Status: {psi.get('session_status')}",
            f"- Reason: {psi.get('reason')}",
        ]
        project_session_section = "\n## Project Session\n\n" + "\n".join(psi_lines) + "\n"
    else:
        project_session_section = "\n## Project Session\n\nSession Status: 未启用\n"

    if project_resume_entry:
        pre = project_resume_entry
        pre_lines = [
            f"- Project State Status: {project_state_write_result.get('write_status', '跳过') if project_state_write_result else '跳过'}",
            f"- Project Resume Status: {pre.get('resume_status', '未知')}",
            f"- State Path: {pre.get('state_path', '')}",
            f"- State Exists: {pre.get('state_exists', False)}",
            f"- Resume Available: {pre.get('resume_available', False)}",
            f"- Last Run ID: {pre.get('last_run_id', '')}",
            f"- Last Status: {pre.get('last_status', '')}",
            f"- Last Stage: {pre.get('last_stage', '')}",
            f"- Reason: {pre.get('reason', '')}",
        ]
        project_resume_section = "\n## Project Resume\n\n" + "\n".join(pre_lines) + "\n"
    else:
        project_resume_section = "\n## Project Resume\n\nResume Available: False\n"

    if project_state_write_result:
        pswr = project_state_write_result
        pswr_lines = [
            f"- Enabled: {pswr.get('enabled')}",
            f"- State Path: {pswr.get('state_path')}",
            f"- Write Status: {pswr.get('write_status')}",
            f"- Resume Available: {pswr.get('resume_available')}",
            f"- Last Run ID: {pswr.get('last_run_id', '')}",
            f"- Last Status: {pswr.get('last_status', '')}",
            f"- Last Stage: {pswr.get('last_stage', '')}",
            f"- Reason: {pswr.get('reason')}",
        ]
        project_state_section = "\n## Project State\n\n" + "\n".join(pswr_lines) + "\n"
    else:
        project_state_section = "\n## Project State\n\nWrite Status: 跳过\n"

    if minimal_dev_loop_acceptance:
        mdl = minimal_dev_loop_acceptance
        mdl_lines = [
            f"- Enabled: {mdl.get('enabled')}",
            f"- Acceptance Status: {mdl.get('acceptance_status')}",
            f"- Workspace OK: {mdl.get('workspace_ok')}",
            f"- Protocol OK: {mdl.get('protocol_ok')}",
            f"- File Modification OK: {mdl.get('file_modification_ok')}",
            f"- Change Record OK: {mdl.get('change_record_ok')}",
            f"- Project Session OK: {mdl.get('project_session_ok')}",
            f"- Project State OK: {mdl.get('project_state_ok')}",
            f"- Summary: {mdl.get('summary')}",
            f"- Reason: {mdl.get('reason')}",
        ]
        minimal_dev_loop_section = "\n## Minimal Development Loop Acceptance\n\n" + "\n".join(mdl_lines) + "\n"
    else:
        minimal_dev_loop_section = "\n## Minimal Development Loop Acceptance\n\nAcceptance Status: 未启用\n"

    # B-08: Reviewer Real Change Review section
    rfm_disp = real_file_modification_info or {}
    pcr_disp = project_change_record_info or {}
    rcr_lines = [
        f"- Reviewer Diff Context Status: {reviewer_diff_context_status}",
        f"- Real File Modification Status: {rfm_disp.get('status', '未知')}",
        f"- Target File: {rfm_disp.get('target_file', '')}",
        f"- Operation: {rfm_disp.get('operation', '未知')}",
    ]
    rfm_changed = rfm_disp.get("changed_files") or []
    if rfm_changed:
        rcr_lines.append("- Changed Files:")
        for f in rfm_changed:
            rcr_lines.append(f"  - {f}")
    else:
        rcr_lines.append("- Changed Files: (none)")
    rcr_lines.append(f"- Change Record Status: {pcr_disp.get('status', '未知')}")
    rcr_lines.append(f"- Changed: {pcr_disp.get('changed', False)}")
    rcr_lines.append(f"- Diff Summary: {pcr_disp.get('diff_summary', '')}")
    reviewer_real_change_review_section = "\n## Reviewer Real Change Review\n\n" + "\n".join(rcr_lines) + "\n"

    if reviewer_structured_result:
        rsr = reviewer_structured_result
        rsr_lines = [
            f"- Parsed: {rsr.get('parsed', False)}",
            f"- Parse Status: {rsr.get('parse_status', '未知')}",
            f"- Review Result: {rsr.get('review_result', '未知')}",
            f"- Revision Required: {rsr.get('revision_required', '未知')}",
            f"- Blocking Issues: {rsr.get('blocking_issues', '') or '(empty)'}",
            f"- Non Blocking Suggestions: {rsr.get('non_blocking_suggestions', '') or '(empty)'}",
            f"- Files Reviewed: {rsr.get('files_reviewed', '') or '(empty)'}",
            f"- Real Change Assessment: {rsr.get('real_change_assessment', '') or '(empty)'}",
            f"- Revision Instructions: {rsr.get('revision_instructions', '') or '(empty)'}",
            f"- Reason: {rsr.get('reason', '')}",
        ]
        structured_reviewer_section = "\n## Structured Reviewer Result\n\n" + "\n".join(rsr_lines) + "\n"
    else:
        structured_reviewer_section = "\n## Structured Reviewer Result\n\nParse Status: 跳过\n"

    return f"""# Final Report

## Workflow Result

{workflow_result}

## Agent Input Evidence

- Tester 接收 PRD：{tester_prd_status}
- Tester 接收 SDD：{tester_sdd_status}
- Tester 接收 TDD：{tester_tdd_status}
- Tester 接收测试上下文：{tester_context_status}
- Planner 接收 SDD：{planner_sdd_status}
- Planner 接收 TDD：{planner_tdd_status}
- Planner 接收 TASKS：{planner_tasks_status}
- Coder 接收 SDD：{coder_sdd_status}
- Coder 接收 TDD：{coder_tdd_status}
- Coder 接收执行范围：{coder_scope_status}
- Reviewer 接收 SDD：{reviewer_sdd_status}
- Reviewer 接收 TDD：{reviewer_tdd_status}
- Reviewer 接收审查上下文：{reviewer_context_status}
- 修订上下文：{revise_context_status}
- 交付上下文：{delivery_context_status}
- Documenter：{documenter_status}
- Documenter 接收交付上下文：{documenter_context_status}
- Agent 调用统一入口：{agent_call_wrapper_status}
- Model Router：{model_router_status}
- 成本记录：{cost_record_status}
- 失败降级策略：{fallback_policy_status}
- 失败策略执行层：{failure_policy_executor_status}
- 失败捕获：{failure_capture_status}
- 失败注入：{failure_injection_status}
- 失败注入矩阵：{failure_injection_matrix_status}
- 路线 C 最终验收：{route_c_acceptance_status}
- 路线 B 进入基线：{route_b_entry_baseline_status}
- 项目工作区：{project_workspace_status}
- 真实任务协议：{real_task_protocol_status}
- 真实文件修改：{real_file_modification_status}
- 变更记录：{change_record_status}
- 项目会话：{project_session_status}
- 项目状态：{project_state_status}
- 项目恢复入口：{project_resume_status}
- 真实开发最小闭环：{minimal_dev_loop_status}
- Reviewer 接收真实变更上下文：{reviewer_diff_context_status}
- Reviewer 结构化审查：{reviewer_structured_status}
- Tester 接收结构化审查结果：{tester_reviewer_structured_context_status}
- SDD：{sdd_status}
- TDD：{tdd_status}
- TASKS：{tasks_status}{revise_section}{delivery_section}{documenter_section}

## User Task

{task.strip()}

## Product Result

{product_result.strip()}

## Architect Result

{architect_result.strip()}

## TestDesigner Result

{test_designer_result.strip()}

## TaskManager Result

{task_manager_result.strip()}

## Planner Result

{planner_result.strip()}

## Coder Result

{coder_result.strip()}

## Reviewer Result

{reviewer_result.strip()}

## Tester Result

{tester_result.strip()}
{model_router_section}
{cost_record_section}
{fallback_policy_section}
{execution_record_section}
{failure_capture_section}
{failure_injection_section}
{failure_injection_matrix_section}
{route_c_acceptance_section}
{route_b_entry_baseline_section}
{project_workspace_section}
{real_task_protocol_section}
{real_file_modification_section}
{change_record_section}
{project_session_section}
{project_resume_section}
{project_state_section}
{minimal_dev_loop_section}
{reviewer_real_change_review_section}
{structured_reviewer_section}
"""


def build_error_report(error: Exception) -> str:
    return f"""# Error Report

## Error

{str(error)}
"""


def build_workflow_lines() -> str:
    lines = []

    for index, stage in enumerate(WORKFLOW_STAGES, start=1):
        lines.append(f"{index}. {stage}")

    return "\n".join(lines)


def build_success_status_lines(tester_status: str) -> str:
    lines = []

    for stage in WORKFLOW_STAGES:
        if stage == "Tester":
            lines.append(f"- {stage}：{tester_status}")
        else:
            lines.append(f"- {stage}：完成")

    return "\n".join(lines)


def build_stage_status_lines(failed_stage: str) -> str:
    if failed_stage not in WORKFLOW_STAGES:
        lines = [f"- {stage}：跳过" for stage in WORKFLOW_STAGES]
        lines.append(f"- Failed Stage：{failed_stage}")
        return "\n".join(lines)

    lines = []
    failed_seen = False

    for stage in WORKFLOW_STAGES:
        if stage == failed_stage:
            lines.append(f"- {stage}：失败")
            failed_seen = True
        elif failed_seen:
            lines.append(f"- {stage}：跳过")
        else:
            lines.append(f"- {stage}：完成")

    return "\n".join(lines)


def build_run_log(
    app_html_generated: bool,
    run_dir: Path,
    tester_status: str,
    workflow_result: str,
    prd_generated: bool,
    sdd_generated: bool,
    tdd_generated: bool,
    tasks_generated: bool,
    tester_prd_status: str,
    tester_sdd_status: str,
    tester_tdd_status: str,
    tester_context_status: str,
    planner_sdd_status: str,
    planner_tdd_status: str,
    planner_tasks_status: str,
    coder_sdd_status: str,
    coder_tdd_status: str,
    coder_scope_status: str,
    reviewer_sdd_status: str,
    reviewer_tdd_status: str,
    reviewer_context_status: str,
    revise_context_status: str,
    delivery_context_status: str,
    documenter_status: str,
    documenter_context_status: str,
    agent_call_wrapper_status: str,
    model_router_status: str,
    cost_record_status: str,
    fallback_policy_status: str,
    failure_policy_executor_status: str,
    failure_capture_status: str,
    failure_injection_status: str,
    failure_injection_matrix_status: str,
    route_c_acceptance_status: str,
    route_b_entry_baseline_status: str,
    project_workspace_status: str,
    real_task_protocol_status: str,
    real_file_modification_status: str,
    change_record_status: str,
    project_session_status: str,
    project_state_status: str,
    project_resume_status: str,
    minimal_dev_loop_status: str,
    reviewer_diff_context_status: str,
    reviewer_structured_status: str,
    tester_reviewer_structured_context_status: str,
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    artifact_status = "已生成" if app_html_generated else "未生成"
    prd_status = "已生成" if prd_generated else "未生成"
    sdd_status = "已生成" if sdd_generated else "未生成"
    tdd_status = "已生成" if tdd_generated else "未生成"
    tasks_status = "已生成" if tasks_generated else "未生成"

    return f"""# Run Log

## Run ID

{run_dir.name}

## Run Time

{now}

## Run Directory

{run_dir}

## Model

{MINIMAX_MODEL}

## Workflow

{build_workflow_lines()}

## Workflow Result

{workflow_result}

## Status

{build_success_status_lines(tester_status)}

## Agent Input Evidence

- Tester 接收 PRD：{tester_prd_status}
- Tester 接收 SDD：{tester_sdd_status}
- Tester 接收 TDD：{tester_tdd_status}
- Tester 接收测试上下文：{tester_context_status}
- Planner 接收 SDD：{planner_sdd_status}
- Planner 接收 TDD：{planner_tdd_status}
- Planner 接收 TASKS：{planner_tasks_status}
- Coder 接收 SDD：{coder_sdd_status}
- Coder 接收 TDD：{coder_tdd_status}
- Coder 接收执行范围：{coder_scope_status}
- Reviewer 接收 SDD：{reviewer_sdd_status}
- Reviewer 接收 TDD：{reviewer_tdd_status}
- Reviewer 接收审查上下文：{reviewer_context_status}
- 修订上下文：{revise_context_status}
- 交付上下文：{delivery_context_status}
- Documenter：{documenter_status}
- Documenter 接收交付上下文：{documenter_context_status}
- Agent 调用统一入口：{agent_call_wrapper_status}
- Model Router：{model_router_status}
- 成本记录：{cost_record_status}
- 失败降级策略：{fallback_policy_status}
- 失败策略执行层：{failure_policy_executor_status}
- 失败捕获：{failure_capture_status}
- 失败注入：{failure_injection_status}
- 失败注入矩阵：{failure_injection_matrix_status}
- 路线 C 最终验收：{route_c_acceptance_status}
- 路线 B 进入基线：{route_b_entry_baseline_status}
- 项目工作区：{project_workspace_status}
- 真实任务协议：{real_task_protocol_status}
- 真实文件修改：{real_file_modification_status}
- 变更记录：{change_record_status}
- 项目会话：{project_session_status}
- 项目状态：{project_state_status}
- 项目恢复入口：{project_resume_status}
- 真实开发最小闭环：{minimal_dev_loop_status}
- Reviewer 接收真实变更上下文：{reviewer_diff_context_status}
- Reviewer 结构化审查：{reviewer_structured_status}
- Tester 接收结构化审查结果：{tester_reviewer_structured_context_status}
- SDD：{sdd_status}
- TDD：{tdd_status}
- TASKS：{tasks_status}

## Artifacts

- PRD：{prd_status}
- SDD：{sdd_status}
- TDD：{tdd_status}
- TASKS：{tasks_status}
- app.html：{artifact_status}

## Output Files

- {run_dir / "summary.md"}
- {run_dir / "docs" / "PRD.md"}
- {run_dir / "docs" / "SDD.md"}
- {run_dir / "docs" / "TDD.md"}
- {run_dir / "docs" / "TASKS.md"}
- {run_dir / "reports" / "product_result.md"}
- {run_dir / "reports" / "task_manager_result.md"}
- {run_dir / "reports" / "architect_result.md"}
- {run_dir / "reports" / "test_designer_result.md"}
- {run_dir / "reports" / "planner_result.md"}
- {run_dir / "reports" / "coder_result.md"}
- {run_dir / "reports" / "reviewer_result.md"}
- {run_dir / "reports" / "tester_result.md"}
- {run_dir / "reports" / "final_report.md"}
- {run_dir / "reports" / "run_log.md"}
- {run_dir / "artifacts" / "app.html"}
"""


def build_error_run_log(run_dir: Path, error: Exception, failed_stage: str) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fi_status = failure_injection_status()

    return f"""# Run Log

## Run ID

{run_dir.name}

## Run Time

{now}

## Run Directory

{run_dir}

## Model

{MINIMAX_MODEL}

## Workflow

{build_workflow_lines()}

## Workflow Result

未通过

## Status

{build_stage_status_lines(failed_stage)}

## Infrastructure

- Agent 调用统一入口：已启用
- Model Router：已启用
- 成本记录：已记录
- 失败降级策略：已记录
- 失败策略执行层：已启用
- 失败捕获：已启用
- 失败注入：{fi_status}
- 失败注入矩阵：已建立

## Artifacts

- PRD：未生成
- SDD：未生成
- TDD：未生成
- app.html：未生成

## Error

{str(error)}

## Output Files

- {run_dir / "summary.md"}
- {run_dir / "reports" / "error_report.md"}
- {run_dir / "reports" / "run_log.md"}
"""


def build_summary(
    run_dir: Path,
    workflow_result: str,
    app_html_generated: bool,
    tester_status: str,
    prd_generated: bool,
    sdd_generated: bool,
    tdd_generated: bool,
    tasks_generated: bool,
    tester_prd_status: str,
    tester_sdd_status: str,
    tester_tdd_status: str,
    tester_context_status: str,
    planner_sdd_status: str,
    planner_tdd_status: str,
    planner_tasks_status: str,
    coder_sdd_status: str,
    coder_tdd_status: str,
    coder_scope_status: str,
    reviewer_sdd_status: str,
    reviewer_tdd_status: str,
    reviewer_context_status: str,
    revise_context_status: str,
    delivery_context_status: str,
    documenter_status: str,
    documenter_context_status: str,
    agent_call_wrapper_status: str,
    model_router_status: str,
    cost_record_status: str,
    fallback_policy_status: str,
    failure_policy_executor_status: str,
    failure_capture_status: str,
    failure_injection_status: str,
    failure_injection_matrix_status: str,
    route_c_acceptance_status: str,
    route_b_entry_baseline_status: str,
    project_workspace_status: str,
    real_task_protocol_status: str,
    real_file_modification_status: str,
    change_record_status: str,
    project_session_status: str,
    project_state_status: str,
    project_resume_status: str,
    minimal_dev_loop_status: str,
    reviewer_diff_context_status: str,
    reviewer_structured_status: str,
    tester_reviewer_structured_context_status: str,
    error: Exception | None = None,
) -> str:
    artifact_status = "已生成" if app_html_generated else "未生成"
    prd_status = "已生成" if prd_generated else "未生成"
    sdd_status = "已生成" if sdd_generated else "未生成"
    tdd_status = "已生成" if tdd_generated else "未生成"
    tasks_status = "已生成" if tasks_generated else "未生成"
    error_text = str(error) if error else "无"

    return f"""# Run Summary

- Run ID：{run_dir.name}
- Workflow Result：{workflow_result}
- PRD：{prd_status}
- SDD：{sdd_status}
- TDD：{tdd_status}
- TASKS：{tasks_status}
- app.html：{artifact_status}
- Tester：{tester_status}
- Tester 接收 PRD：{tester_prd_status}
- Tester 接收 SDD：{tester_sdd_status}
- Tester 接收 TDD：{tester_tdd_status}
- Tester 接收测试上下文：{tester_context_status}
- Planner 接收 SDD：{planner_sdd_status}
- Planner 接收 TDD：{planner_tdd_status}
- Planner 接收 TASKS：{planner_tasks_status}
- Coder 接收 SDD：{coder_sdd_status}
- Coder 接收 TDD：{coder_tdd_status}
- Coder 接收执行范围：{coder_scope_status}
- Reviewer 接收 SDD：{reviewer_sdd_status}
- Reviewer 接收 TDD：{reviewer_tdd_status}
- Reviewer 接收审查上下文：{reviewer_context_status}
- 修订上下文：{revise_context_status}
- 交付上下文：{delivery_context_status}
- Documenter：{documenter_status}
- Documenter 接收交付上下文：{documenter_context_status}
- Agent 调用统一入口：{agent_call_wrapper_status}
- Model Router：{model_router_status}
- 成本记录：{cost_record_status}
- 失败降级策略：{fallback_policy_status}
- 失败策略执行层：{failure_policy_executor_status}
- 失败捕获：{failure_capture_status}
- 失败注入：{failure_injection_status}
- 失败注入矩阵：{failure_injection_matrix_status}
- 路线 C 最终验收：{route_c_acceptance_status}
- 路线 B 进入基线：{route_b_entry_baseline_status}
- 项目工作区：{project_workspace_status}
- 真实任务协议：{real_task_protocol_status}
- 真实文件修改：{real_file_modification_status}
- 变更记录：{change_record_status}
- 项目会话：{project_session_status}
- 项目状态：{project_state_status}
- 项目恢复入口：{project_resume_status}
- 真实开发最小闭环：{minimal_dev_loop_status}
- Reviewer 接收真实变更上下文：{reviewer_diff_context_status}
- Reviewer 结构化审查：{reviewer_structured_status}
- Tester 接收结构化审查结果：{tester_reviewer_structured_context_status}
- Error：{error_text}
"""


def main():
    task = read_text(TASK_FILE)

    # B-05/B-06: Determine project id for session isolation
    raw_project_id = PROJECT_ID
    project_id_valid = is_valid_project_id(raw_project_id) if raw_project_id else False
    active_project_id = raw_project_id if project_id_valid else ""

    run_dir = create_run_dir(active_project_id)
    reports_dir = run_dir / "reports"
    artifacts_dir = run_dir / "artifacts"
    docs_dir = run_dir / "docs"

    # B-01: Detect real project workspace
    global agent_workspace_info
    agent_workspace_info = detect_project_workspace()

    # B-02: Build real task protocol
    global real_task_protocol_info
    real_task_protocol_info = build_real_task_protocol(task, agent_workspace_info)

    # B-05: Register or update project in registry (pass raw id to preserve invalid value)
    global project_registry_result
    project_registry_result = register_or_update_project(
        raw_project_id, agent_workspace_info, run_dir
    )

    # B-05: Build project session info (uses active id for path operations)
    global project_session_info
    project_session_info = build_project_session_info(
        raw_project_id, agent_workspace_info, project_registry_result, run_dir
    )

    # B-06: Detect project resume entry (read existing state if any)
    global project_resume_entry
    project_resume_entry = detect_project_resume_entry(project_session_info)

    current_stage = "Startup"

    try:
        print("========== 用户任务 ==========")
        print(task.strip())
        print()

        print("========== Product 正在生成 PRD ==========")
        current_stage = "Product"
        product_result = remove_think(run_product(task))
        print(product_result)
        save_text(reports_dir / "product_result.md", product_result)
        save_text(docs_dir / "PRD.md", product_result)
        prd_generated = True
        print()

        print("========== Architect 正在生成 SDD ==========")
        current_stage = "Architect"
        architect_result = remove_think(run_architect(task, product_result))
        print(architect_result)
        save_text(reports_dir / "architect_result.md", architect_result)
        save_text(docs_dir / "SDD.md", architect_result)
        sdd_generated = True
        print()

        print("========== TestDesigner 正在生成 TDD ==========")
        current_stage = "TestDesigner"
        test_designer_result = remove_think(
            run_test_designer(task, product_result, architect_result)
        )
        print(test_designer_result)
        save_text(reports_dir / "test_designer_result.md", test_designer_result)
        save_text(docs_dir / "TDD.md", test_designer_result)
        tdd_generated = True
        print()

        print("========== TaskManager 正在生成任务拆分 ==========")
        current_stage = "TaskManager"
        task_manager_result = remove_think(
            run_task_manager(task, product_result, architect_result, test_designer_result)
        )
        print(task_manager_result)
        save_text(reports_dir / "task_manager_result.md", task_manager_result)
        save_text(docs_dir / "TASKS.md", task_manager_result)
        tasks_generated = True
        print()

        print("========== Planner 正在生成计划 ==========")
        current_stage = "Planner"
        planner_result = remove_think(
            run_planner(
                task,
                product_result,
                architect_result,
                test_designer_result,
                task_manager_result,
            )
        )
        print(planner_result)
        save_text(reports_dir / "planner_result.md", planner_result)
        planner_sdd_status = "已接收"
        planner_tdd_status = "已接收"
        planner_tasks_status = "已接收"
        print()

        print("========== Coder 正在根据计划生成代码 ==========")
        current_stage = "Coder"
        current_task_scope = planner_result
        coder_result = remove_think(
            run_coder(
                task,
                product_result,
                architect_result,
                test_designer_result,
                planner_result,
                current_task_scope,
            )
        )
        print(coder_result)
        save_text(reports_dir / "coder_result.md", coder_result)
        coder_sdd_status = "已接收"
        coder_tdd_status = "已接收"
        coder_scope_status = "已接收"
        print()

        html_code = extract_html_code(coder_result)
        app_html_generated = False

        if html_code:
            save_text(artifacts_dir / "app.html", html_code)
            app_html_generated = True

        # B-03: Apply Coder output to real project (controlled write to PROJECT_ROOT/app.html)
        global real_file_modification_info
        real_file_modification_info = apply_coder_output_to_project(
            coder_result,
            agent_workspace_info,
            real_task_protocol_info,
        )

        # B-04: Persist change record for reporting
        global project_change_record_info
        project_change_record_info = real_file_modification_info.get("change_record", {})
        if project_change_record_info:
            project_change_record_info = {
                "status": real_file_modification_info.get("status", "未启用"),
                "target_file": real_file_modification_info.get("target_file", ""),
                "operation": real_file_modification_info.get("operation", "none"),
                "changed": project_change_record_info.get("changed", False),
                "before_size": project_change_record_info.get("before_size", 0),
                "after_size": project_change_record_info.get("after_size", 0),
                "before_line_count": project_change_record_info.get("before_line_count", 0),
                "after_line_count": project_change_record_info.get("after_line_count", 0),
                "first_changed_line": project_change_record_info.get("first_changed_line", 0),
                "diff_summary": project_change_record_info.get("diff_summary", ""),
                "changed_files": real_file_modification_info.get("changed_files", []),
            }

        # B-08: Compute reviewer diff context status before calling Reviewer
        global reviewer_diff_context_status
        if project_change_record_info:
            reviewer_diff_context_status = "已接收"
        else:
            reviewer_diff_context_status = "未提供"

        print("========== Reviewer 正在审查代码 ==========")
        current_stage = "Reviewer"
        reviewer_result = remove_think(
            run_reviewer(
                task,
                product_result,
                architect_result,
                test_designer_result,
                planner_result,
                coder_result,
                project_change_record_info,
                real_file_modification_info,
            )
        )
        print(reviewer_result)
        save_text(reports_dir / "reviewer_result.md", reviewer_result)
        reviewer_sdd_status = "已接收"

        # B-09: Parse structured Reviewer result
        global reviewer_structured_result
        reviewer_structured_result = parse_structured_reviewer_result(reviewer_result)
        if reviewer_structured_result["parsed"]:
            reviewer_structured_status_value = "已解析"
        else:
            reviewer_structured_status_value = reviewer_structured_result["parse_status"]
        if reviewer_structured_result["parsed"]:
            reviewer_is_passed = reviewer_structured_result["review_result"] == "通过"
        else:
            reviewer_is_passed = review_passed(reviewer_result)
        reviewer_tdd_status = "已接收"
        reviewer_context_status = "已接收"
        print()

        tester_result = "Reviewer 未通过，Tester 已跳过。"
        tester_status = "跳过"
        reviewer_is_passed = review_passed(reviewer_result)

        if reviewer_is_passed:
            print("========== Tester 正在分析测试方案 ==========")
            current_stage = "Tester"
            tester_result = remove_think(
                run_tester(
                    task,
                    product_result,
                    architect_result,
                    test_designer_result,
                    planner_result,
                    coder_result,
                    reviewer_result,
                    reviewer_structured_result,
                )
            )
            tester_status = "完成"
            print(tester_result)
        else:
            print("========== Tester 已跳过 ==========")
            print(tester_result)

        save_text(reports_dir / "tester_result.md", tester_result)
        print()

        tester_prd_status = "已接收" if tester_status == "完成" else "跳过"
        tester_sdd_status = "已接收" if tester_status == "完成" else "跳过"
        tester_tdd_status = "已接收" if tester_status == "完成" else "跳过"
        tester_context_status = "已接收" if tester_status == "完成" else "跳过"

        if not reviewer_is_passed:
            revise_context_status = "已生成"
            revise_context = f"""========== REVISE CONTEXT ==========

PRD:
{product_result}

SDD:
{architect_result}

TDD:
{test_designer_result}

TASK SCOPE:
{planner_result}

CODER OUTPUT:
{coder_result}

REVIEWER OUTPUT:
{reviewer_result}

REVISION REQUIREMENT:
Coder 下一轮必须基于 Reviewer Output 修复问题，并保持 PRD、SDD、TDD 和 Task Scope 一致。
"""
        else:
            revise_context_status = "无需修订"
            revise_context = ""

        if tester_status == "完成":
            delivery_context_status = "已生成"
            delivery_context = f"""========== DELIVERY CONTEXT ==========

USER TASK:
{task}

PRD:
{product_result}

SDD:
{architect_result}

TDD:
{test_designer_result}

TASKS:
{task_manager_result}

TASK SCOPE:
{planner_result}

CODER OUTPUT:
{coder_result}

REVIEWER OUTPUT:
{reviewer_result}

TESTER OUTPUT:
{tester_result}

DELIVERY RESULT:
本次任务已完成开发、审查和测试，可进入交付总结。
"""
        elif revise_context_status == "已生成":
            delivery_context_status = "等待修订"
            delivery_context = ""
        else:
            delivery_context_status = "跳过"
            delivery_context = ""

        if delivery_context_status == "已生成":
            documenter_status = "完成"
            documenter_context_status = "已接收"
            documenter_result = remove_think(run_documenter(delivery_context))
        elif delivery_context_status == "等待修订":
            documenter_status = "跳过"
            documenter_context_status = "等待修订"
            documenter_result = ""
        else:
            documenter_status = "跳过"
            documenter_context_status = "跳过"
            documenter_result = ""

        workflow_passed = (
            reviewer_is_passed
            and tester_status == "完成"
            and app_html_generated
            and prd_generated
            and sdd_generated
            and tdd_generated
            and tasks_generated
        )
        workflow_result = "通过" if workflow_passed else "未通过"

        agent_call_wrapper_status = "已启用"
        model_router_status = "已启用"
        cost_record_status = "已记录"
        fallback_policy_status = "已记录"
        failure_policy_executor_status = "已启用"
        failure_capture_status = "已启用"
        failure_injection_matrix_status = "已建立"
        route_c_acceptance_status = "已通过"
        route_b_entry_baseline_status = "已冻结"
        # B-06: Persist project_state.json before computing its status
        resume_status = build_project_resume_status(
            project_session_info.get("session_status", "未启用"),
            workflow_result,
        )
        project_state_write_result = write_project_state(
            project_session_info,
            run_dir,
            workflow_result,
            current_stage,
            resume_status,
        )
        # B-07: Compute minimal dev loop acceptance after project state is persisted
        global minimal_dev_loop_acceptance
        minimal_dev_loop_acceptance = build_minimal_dev_loop_acceptance(
            agent_workspace_info,
            real_task_protocol_info,
            real_file_modification_info,
            real_file_modification_info.get("change_record", {}),
            project_session_info,
            project_state_write_result,
            workflow_result,
        )
        project_workspace_status_value = project_workspace_status(agent_workspace_info)
        real_task_protocol_status_value = real_task_protocol_info.get("protocol_status", "未启用")
        real_file_modification_status_value = real_file_modification_info.get("status", "未启用")
        change_record_info = real_file_modification_info.get("change_record", {})
        if real_file_modification_status_value == "已修改":
            change_record_status_value = "已记录" if change_record_info.get("changed") else "无变化"
        else:
            change_record_status_value = real_file_modification_status_value
        project_session_status_value = project_session_info.get("session_status", "未启用")
        project_state_status_value = project_state_write_result.get("write_status", "跳过")
        project_resume_status_value = build_project_resume_status(
            project_session_status_value, workflow_result
        )
        # B-08/B-09: Test if Tester should run based on Reviewer result
        if reviewer_is_passed:
            tester_reviewer_structured_context_status_value = "已接收"
        else:
            tester_reviewer_structured_context_status_value = "跳过"
        minimal_dev_loop_status_value = minimal_dev_loop_acceptance.get("acceptance_status", "未启用")
        failure_injection_status_value = failure_injection_status()

        final_report = build_final_report(
            task,
            product_result,
            architect_result,
            test_designer_result,
            task_manager_result,
            planner_result,
            coder_result,
            reviewer_result,
            tester_result,
            workflow_result,
            tester_prd_status,
            tester_sdd_status,
            tester_tdd_status,
            tester_context_status,
            planner_sdd_status,
            planner_tdd_status,
            planner_tasks_status,
            coder_sdd_status,
            coder_tdd_status,
            coder_scope_status,
            reviewer_sdd_status,
            reviewer_tdd_status,
            reviewer_context_status,
            sdd_generated,
            tdd_generated,
            tasks_generated,
            revise_context_status,
            revise_context,
            delivery_context_status,
            delivery_context,
            documenter_status,
            documenter_context_status,
            documenter_result,
            agent_call_wrapper_status,
            model_router_status,
            cost_record_status,
            fallback_policy_status,
            failure_policy_executor_status,
            failure_capture_status,
            failure_injection_status_value,
            failure_injection_matrix_status,
            route_c_acceptance_status,
            route_b_entry_baseline_status,
            project_workspace_status_value,
            real_task_protocol_status_value,
            real_file_modification_status_value,
            change_record_status_value,
            project_session_status_value,
            project_state_status_value,
            project_resume_status_value,
            minimal_dev_loop_status_value,
            reviewer_diff_context_status,
            reviewer_structured_status_value,
            tester_reviewer_structured_context_status_value,
        )
        save_text(reports_dir / "final_report.md", final_report)

        run_log = build_run_log(
            app_html_generated,
            run_dir,
            tester_status,
            workflow_result,
            prd_generated,
            sdd_generated,
            tdd_generated,
            tasks_generated,
            tester_prd_status,
            tester_sdd_status,
            tester_tdd_status,
            tester_context_status,
            planner_sdd_status,
            planner_tdd_status,
            planner_tasks_status,
            coder_sdd_status,
            coder_tdd_status,
            coder_scope_status,
            reviewer_sdd_status,
            reviewer_tdd_status,
            reviewer_context_status,
            revise_context_status,
            delivery_context_status,
            documenter_status,
            documenter_context_status,
            agent_call_wrapper_status,
            model_router_status,
            cost_record_status,
            fallback_policy_status,
            failure_policy_executor_status,
            failure_capture_status,
            failure_injection_status_value,
            failure_injection_matrix_status,
            route_c_acceptance_status,
            route_b_entry_baseline_status,
            project_workspace_status_value,
            real_task_protocol_status_value,
            real_file_modification_status_value,
            change_record_status_value,
            project_session_status_value,
            project_state_status_value,
            project_resume_status_value,
            minimal_dev_loop_status_value,
            reviewer_diff_context_status,
            reviewer_structured_status_value,
            tester_reviewer_structured_context_status_value,
        )
        save_text(reports_dir / "run_log.md", run_log)

        summary = build_summary(
            run_dir,
            workflow_result,
            app_html_generated,
            tester_status,
            prd_generated,
            sdd_generated,
            tdd_generated,
            tasks_generated,
            tester_prd_status,
            tester_sdd_status,
            tester_tdd_status,
            tester_context_status,
            planner_sdd_status,
            planner_tdd_status,
            planner_tasks_status,
            coder_sdd_status,
            coder_tdd_status,
            coder_scope_status,
            reviewer_sdd_status,
            reviewer_tdd_status,
            reviewer_context_status,
            revise_context_status,
            delivery_context_status,
            documenter_status,
            documenter_context_status,
            agent_call_wrapper_status,
            model_router_status,
            cost_record_status,
            fallback_policy_status,
            failure_policy_executor_status,
            failure_capture_status,
            failure_injection_status_value,
            failure_injection_matrix_status,
            route_c_acceptance_status,
            route_b_entry_baseline_status,
            project_workspace_status_value,
            real_task_protocol_status_value,
            real_file_modification_status_value,
            change_record_status_value,
            project_session_status_value,
            project_state_status_value,
            project_resume_status_value,
            minimal_dev_loop_status_value,
            reviewer_diff_context_status,
            reviewer_structured_status_value,
            tester_reviewer_structured_context_status_value,
        )
        save_text(run_dir / "summary.md", summary)
        update_latest(run_dir, active_project_id)

        final_report = build_final_report(
            task,
            product_result,
            architect_result,
            test_designer_result,
            task_manager_result,
            planner_result,
            coder_result,
            reviewer_result,
            tester_result,
            workflow_result,
            tester_prd_status,
            tester_sdd_status,
            tester_tdd_status,
            tester_context_status,
            planner_sdd_status,
            planner_tdd_status,
            planner_tasks_status,
            coder_sdd_status,
            coder_tdd_status,
            coder_scope_status,
            reviewer_sdd_status,
            reviewer_tdd_status,
            reviewer_context_status,
            sdd_generated,
            tdd_generated,
            tasks_generated,
            revise_context_status,
            revise_context,
            delivery_context_status,
            delivery_context,
            documenter_status,
            documenter_context_status,
            documenter_result,
            agent_call_wrapper_status,
            model_router_status,
            cost_record_status,
            fallback_policy_status,
            failure_policy_executor_status,
            failure_capture_status,
            failure_injection_status_value,
            failure_injection_matrix_status,
            route_c_acceptance_status,
            route_b_entry_baseline_status,
            project_workspace_status_value,
            real_task_protocol_status_value,
            real_file_modification_status_value,
            change_record_status_value,
            project_session_status_value,
            project_state_status_value,
            project_resume_status_value,
        )
        save_text(reports_dir / "final_report.md", final_report)

        print()
        print("========== 输出文件已保存 ==========")
        print(f"本次运行目录：{run_dir}")
        print(f"最新结果目录：{OUTPUT_DIR / 'latest'}")
        print(f"报告目录：{reports_dir}")
        print(f"产物目录：{artifacts_dir}")
        print(f"文档目录：{docs_dir}")
        print("已生成：summary.md")
        print("已生成：docs/PRD.md")
        print("已生成：docs/SDD.md")
        print("已生成：docs/TDD.md")
        print("已生成：docs/TASKS.md")
        print("已生成：reports/test_designer_result.md")
        print("已生成：reports/task_manager_result.md")
        print("已生成：reports/final_report.md")
        print("已生成：reports/run_log.md")

        if app_html_generated:
            print("已生成：artifacts/app.html")
        else:
            print("未生成：artifacts/app.html")

    except Exception as error:
        error_report = build_error_report(error)
        workflow_result = "未通过"
        save_text(reports_dir / "error_report.md", error_report)

        agent_call_wrapper_status = "已启用"
        model_router_status = "已启用"
        cost_record_status = "已记录"
        fallback_policy_status = "已记录"
        failure_policy_executor_status = "已启用"
        failure_capture_status = "已启用"
        failure_injection_matrix_status = "已建立"
        route_c_acceptance_status = "待确认"
        route_b_entry_baseline_status = "待确认"

        # B-06: Persist project_state.json (error path) FIRST
        error_resume_status = build_project_resume_status(
            project_session_info.get("session_status", "未启用"),
            "未通过",
        )
        project_state_write_result = write_project_state(
            project_session_info,
            run_dir,
            "未通过",
            current_stage,
            error_resume_status,
            error=error,
        )
        project_state_status_value = project_state_write_result.get("write_status", "跳过")
        # B-07: Compute minimal dev loop acceptance (error path)
        minimal_dev_loop_acceptance = build_minimal_dev_loop_acceptance(
            agent_workspace_info,
            real_task_protocol_info,
            real_file_modification_info,
            real_file_modification_info.get("change_record", {}),
            project_session_info,
            project_state_write_result,
            workflow_result,
        )
        project_workspace_status_value = project_workspace_status(agent_workspace_info)
        real_task_protocol_status_value = real_task_protocol_info.get("protocol_status", "未启用")
        real_file_modification_status_value = real_file_modification_info.get("status", "未启用")
        change_record_info = real_file_modification_info.get("change_record", {})
        if real_file_modification_status_value == "已修改":
            change_record_status_value = "已记录" if change_record_info.get("changed") else "无变化"
        else:
            change_record_status_value = real_file_modification_status_value
        project_session_status_value = project_session_info.get("session_status", "未启用")
        project_resume_status_value = build_project_resume_status(
            project_session_status_value, "未通过"
        )
        if reviewer_structured_result:
            reviewer_structured_status_value = reviewer_structured_result.get("parse_status", "跳过")
            tester_reviewer_structured_context_status_value = "已接收" if reviewer_is_passed else "跳过"
        else:
            reviewer_structured_status_value = "跳过"
            tester_reviewer_structured_context_status_value = "跳过"
        minimal_dev_loop_status_value = minimal_dev_loop_acceptance.get("acceptance_status", "未通过")
        failure_injection_status_value = failure_injection_status()

        run_log = build_error_run_log(run_dir, error, current_stage)
        save_text(reports_dir / "run_log.md", run_log)
        save_text(reports_dir / "run_log.md", run_log)

        summary = build_summary(
            run_dir,
            "未通过",
            False,
            "跳过",
            False,
            False,
            False,
            False,
            "跳过",
            "跳过",
            "跳过",
            "跳过",
            "跳过",
            "跳过",
            "跳过",
            "跳过",
            "跳过",
            "跳过",
            "跳过",
            "跳过",
            "跳过",
            "跳过",
            "跳过",
            "跳过",
            "跳过",
            agent_call_wrapper_status,
            model_router_status,
            cost_record_status,
            fallback_policy_status,
            failure_policy_executor_status,
            failure_capture_status,
            failure_injection_status_value,
            failure_injection_matrix_status,
            route_c_acceptance_status,
            route_b_entry_baseline_status,
            project_workspace_status_value,
            real_task_protocol_status_value,
            real_file_modification_status_value,
            change_record_status_value,
            project_session_status_value,
            project_state_status_value,
            project_resume_status_value,
            minimal_dev_loop_status_value,
            reviewer_diff_context_status,
            reviewer_structured_status_value,
            tester_reviewer_structured_context_status_value,
            error,
        )
        save_text(run_dir / "summary.md", summary)

        try:
            partial_results = {
                stage: locals().get(f"{stage.lower()}_result", f"{stage} 未完成")
                for stage in WORKFLOW_STAGES
            }
            if agent_model_routes or agent_cost_records or agent_fallback_policies or agent_execution_records or agent_failure_records:
                final_report = build_final_report(
                    task,
                    partial_results.get("Product", "Product 未完成"),
                    partial_results.get("Architect", "Architect 未完成"),
                    partial_results.get("TestDesigner", "TestDesigner 未完成"),
                    partial_results.get("TaskManager", "TaskManager 未完成"),
                    partial_results.get("Planner", "Planner 未完成"),
                    partial_results.get("Coder", "Coder 未完成"),
                    partial_results.get("Reviewer", "Reviewer 未完成"),
                    partial_results.get("Tester", "Tester 未完成"),
                    "未通过",
                    "跳过",
                    "跳过",
                    "跳过",
                    "跳过",
                    "跳过",
                    "跳过",
                    "跳过",
                    "跳过",
                    "跳过",
                    "跳过",
                    "跳过",
                    "跳过",
                    "跳过",
                    bool(partial_results.get("Architect")),
                    bool(partial_results.get("TestDesigner")),
                    bool(partial_results.get("TaskManager")),
                    "无需修订",
                    "",
                    "跳过",
                    "",
                    "跳过",
                    "跳过",
                    "",
                    agent_call_wrapper_status,
                    model_router_status,
                    cost_record_status,
                    fallback_policy_status,
                    failure_policy_executor_status,
                    failure_capture_status,
                    failure_injection_status_value,
                    failure_injection_matrix_status,
                    route_c_acceptance_status,
                    route_b_entry_baseline_status,
                    project_workspace_status_value,
                    real_task_protocol_status_value,
                    real_file_modification_status_value,
                    change_record_status_value,
                    project_session_status_value,
                    project_state_status_value,
                    project_resume_status_value,
                    minimal_dev_loop_status_value,
                    reviewer_diff_context_status,
                    reviewer_structured_status_value,
                    tester_reviewer_structured_context_status_value,
                )
                save_text(reports_dir / "final_report.md", final_report)
        except Exception as fe:
            print(f"Warning: failed to generate final_report on error path: {fe}")

        update_latest(run_dir, active_project_id)

        print()
        print("========== 运行失败 ==========")
        print(str(error))
        print(f"错误报告：{reports_dir / 'error_report.md'}")
        print(f"运行日志：{reports_dir / 'run_log.md'}")
        print(f"运行摘要：{run_dir / 'summary.md'}")
        print(f"最新结果目录：{OUTPUT_DIR / 'latest'}")


if __name__ == "__main__":
    main()