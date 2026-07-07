import os
import shutil
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
    agent_result, execution_record = execute_agent_with_policy(
        agent_name, role_content, prompt, model_route, fallback_policy
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


def create_run_dir() -> Path:
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


def update_latest(run_dir: Path) -> None:
    latest_dir = OUTPUT_DIR / "latest"

    if latest_dir.exists():
        shutil.rmtree(latest_dir)

    shutil.copytree(run_dir, latest_dir)


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

请你作为 Reviewer Agent，基于用户原始任务、PRD、SDD、TDD、Planner 计划和 Coder 实现进行代码审查。Reviewer 必须基于完整上下文进行代码审查，不仅检查代码结果，还需要验证实现是否符合需求、架构和测试设计。
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

请你作为 Tester Agent，根据用户任务、PRD、SDD、TDD、Planner 计划、Coder 实现和 Reviewer 结论，按你的固定输出格式设计最小测试方案并给出测试结论。Tester 必须基于完整上下文验证最终结果，不仅运行测试，还需要确认需求、架构、实现和审查意见的一致性。
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
- Error：{error_text}
"""


def main():
    task = read_text(TASK_FILE)

    run_dir = create_run_dir()
    reports_dir = run_dir / "reports"
    artifacts_dir = run_dir / "artifacts"
    docs_dir = run_dir / "docs"

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
            )
        )
        print(reviewer_result)
        save_text(reports_dir / "reviewer_result.md", reviewer_result)
        reviewer_sdd_status = "已接收"
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
        )
        save_text(run_dir / "summary.md", summary)

        update_latest(run_dir)

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
        save_text(reports_dir / "error_report.md", error_report)

        run_log = build_error_run_log(run_dir, error, current_stage)
        save_text(reports_dir / "run_log.md", run_log)

        failure_capture_status = "已启用"

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
            "跳过",
            "跳过",
            "跳过",
            "跳过",
            "跳过",
            "跳过",
            "跳过",
            "跳过",
            failure_capture_status,
            error,
        )
        save_text(run_dir / "summary.md", summary)

        update_latest(run_dir)

        print()
        print("========== 运行失败 ==========")
        print(str(error))
        print(f"错误报告：{reports_dir / 'error_report.md'}")
        print(f"运行日志：{reports_dir / 'run_log.md'}")
        print(f"运行摘要：{run_dir / 'summary.md'}")
        print(f"最新结果目录：{OUTPUT_DIR / 'latest'}")


if __name__ == "__main__":
    main()