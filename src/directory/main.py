"""Main workflow orchestration."""

import asyncio
from pathlib import Path

from .agents import QueryAgent, PlannerAgent, ExecutorAgent, SummaryAgent
from .config import settings

# Maximum input length (10KB) to prevent excessive API costs
MAX_INPUT_LENGTH = 10_000
from .execution import (
    classify_script,
    execute_script,
    check_output_size,
)
from .models import Mode, ScriptClassification
from .ui import (
    display,
    display_error,
    display_header,
    display_mode_switch,
    display_script,
    get_input,
    show_approval_prompt,
    user_approves,
)


async def query_flow(question: str, sandbox: Path):
    """
    Execute the query workflow.

    Args:
        question: User's question
        sandbox: Sandbox path
    """
    try:
        # Step 1: Generate read script using Query Agent
        query_agent = QueryAgent()
        response = await query_agent.call(question, sandbox)
        script = response["script"]

        # Step 2: Validate script is read-only
        classification = classify_script(script, sandbox)
        if classification != ScriptClassification.READ:
            display_error("Cannot access that location.")
            return

        # Step 3: Execute script
        display("Analyzing...")
        display_script(script)
        result = execute_script(script, timeout=settings.read_timeout, cwd=sandbox)

        if not result.success:
            display_error(f"Script execution failed: {result.stderr}")
            return

        # Step 4: Check output size
        ok, error = check_output_size(result.stdout)
        if not ok:
            display_error(error)
            return

        # Step 5: Summarize results
        summary_agent = SummaryAgent()
        summary_response = await summary_agent.call("query", question, result.stdout)
        display(summary_response["summary"])

    except Exception as e:
        display_error(f"Query failed: {str(e)}")


async def task_flow(task: str, sandbox: Path):
    """
    Execute the task workflow.

    Args:
        task: User's task description
        sandbox: Sandbox path
    """
    try:
        # Step 1: Generate planning script using Planner Agent
        planner_agent = PlannerAgent()
        plan_response = await planner_agent.call(task, sandbox)
        plan_script = plan_response["script"]

        # Step 2: Validate planning script is read-only
        if classify_script(plan_script, sandbox) != ScriptClassification.READ:
            display_error("Cannot access that location.")
            return

        # Step 3: Execute planning script
        display("Analyzing...")
        display_script(plan_script)
        read_result = execute_script(plan_script, timeout=settings.read_timeout, cwd=sandbox)

        if not read_result.success:
            display_error(f"Planning failed: {read_result.stderr}")
            return

        # Step 4: Check planning output size
        ok, error = check_output_size(read_result.stdout)
        if not ok:
            display_error(error)
            return

        # Step 5: Generate execution script using Executor Agent
        executor_agent = ExecutorAgent()
        exec_response = await executor_agent.call(task, read_result.stdout, sandbox)

        # Step 6: Validate execution script safety
        if classify_script(exec_response["script"], sandbox) == ScriptClassification.UNSAFE:
            display_error("Cannot perform that operation.")
            return

        # Step 7: Show approval prompt
        show_approval_prompt(exec_response["explanation"], exec_response["script"])
        if not user_approves():
            display("Cancelled.")
            return

        # Step 8: Execute the write script
        write_result = execute_script(
            exec_response["script"],
            timeout=settings.write_timeout,
            cwd=sandbox
        )

        if not write_result.success:
            display_error(f"Execution failed: {write_result.stderr}")
            return

        # Step 9: Check execution output size
        ok, error = check_output_size(write_result.stdout)
        if not ok:
            display_error(error)
            return

        # Step 10: Summarize results
        summary_agent = SummaryAgent()
        summary_response = await summary_agent.call("task", task, write_result.stdout)
        display(summary_response["summary"])

    except Exception as e:
        display_error(f"Task failed: {str(e)}")


def run_main_loop(sandbox: Path):
    """
    Run the main application loop.

    Args:
        sandbox: Validated sandbox path
    """
    mode = Mode.QUERY
    workflow_running = False

    display_header(sandbox, mode)

    while True:
        user_input, key = get_input()

        # Handle TAB for mode switching (only when idle)
        if key == "TAB" and not workflow_running:
            mode = Mode.TASK if mode == Mode.QUERY else Mode.QUERY
            display_mode_switch(mode)
            continue

        # Handle Ctrl+C
        if key == "CTRL+C":
            display("Cancelled.")
            continue

        # Handle exit commands
        if user_input.strip() in ["/quit", "/exit"]:
            display("Goodbye!")
            break

        # Skip empty input
        if not user_input.strip():
            continue

        # Validate input length
        if len(user_input) > MAX_INPUT_LENGTH:
            display_error(f"Input too long ({len(user_input)} characters). Maximum is {MAX_INPUT_LENGTH} characters.")
            continue

        try:
            workflow_running = True
            if mode == Mode.QUERY:
                asyncio.run(query_flow(user_input, sandbox))
            else:
                asyncio.run(task_flow(user_input, sandbox))
        except KeyboardInterrupt:
            display("Cancelled.")
        except Exception as e:
            display_error(f"An error occurred: {str(e)}")
        finally:
            workflow_running = False
