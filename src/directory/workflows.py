"""Workflow orchestration with callback-based UI updates."""

from pathlib import Path
from typing import Awaitable, Callable, Any

from .agents import QueryAgent, PlannerAgent, ExecutorAgent, SummaryAgent
from .config import settings
from .execution import (
    classify_script,
    execute_script,
    check_output_size,
    validate_script_syntax,
)
from .models import ScriptClassification


async def generate_script_with_validation(
    agent_call: Callable[[str | None], Awaitable[dict[str, Any]]],
    display: Callable[[str], None],
    display_error: Callable[[str], None],
    max_retries: int = 2,
) -> dict[str, Any] | None:
    """
    Generate a script with syntax validation and retry on syntax errors.

    This function wraps AI agent calls to ensure generated scripts have valid
    PowerShell syntax. If a syntax error is detected, it provides feedback to
    the agent and retries up to max_retries times.

    Args:
        agent_call: Async function that takes optional error feedback and returns agent response
        display: Callback for status messages
        display_error: Callback for error messages
        max_retries: Maximum number of retry attempts

    Returns:
        Agent response dict if successful, None if all retries failed
    """
    error_feedback = None

    for attempt in range(max_retries):
        response = await agent_call(error_feedback)
        script = response.get("script", "")

        # Validate syntax
        is_valid, syntax_error = validate_script_syntax(script)

        if is_valid:
            return response

        # If not valid and we have retries left, ask AI to fix it
        if attempt < max_retries - 1:
            display(f"[dim]Script has syntax error, asking AI to fix (attempt {attempt + 2}/{max_retries})...[/dim]")
            error_feedback = f"\n\nPREVIOUS ATTEMPT HAD SYNTAX ERROR:\n{syntax_error}\n\nPlease fix the syntax and regenerate the script."
        else:
            display_error(f"Failed to generate valid script after {max_retries} attempts: {syntax_error}")
            return None

    return None


async def query_flow(
    question: str,
    sandbox: Path,
    display: Callable[[str], None],
    display_error: Callable[[str], None],
    display_script: Callable[[str], None],
    update_status: Callable[[str], None],
) -> None:
    """
    Execute the query workflow with callback-based UI updates.

    Args:
        question: User's question
        sandbox: Sandbox path
        display: Callback for general messages
        display_error: Callback for error messages
        display_script: Callback for script display
        update_status: Callback for status bar updates
    """
    try:
        # Step 1: Generate read script using Query Agent with syntax validation
        update_status("Calling AI agent...")
        display("[dim]Asking AI to generate a PowerShell script...[/dim]")
        query_agent = QueryAgent()

        response = await generate_script_with_validation(
            agent_call=lambda error_feedback: query_agent.call(
                question if error_feedback is None else question + error_feedback,
                sandbox
            ),
            display=display,
            display_error=display_error,
        )

        if response is None:
            return

        script = response["script"]

        # Step 2: Validate script is read-only
        update_status("Validating script...")
        display("[dim]Checking script safety...[/dim]")
        classification = classify_script(script, sandbox)
        if classification != ScriptClassification.READ:
            display_error("Cannot access that location.")
            return

        # Step 3: Execute script
        update_status("Running script...")
        display("[dim]Executing PowerShell script...[/dim]")
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
        update_status("Summarizing results...")
        display("[dim]AI is summarizing the results...[/dim]")
        summary_agent = SummaryAgent()
        summary_response = await summary_agent.call("query", question, result.stdout)
        display(summary_response["summary"])

    except Exception as e:
        display_error(f"Query failed: {str(e)}")


async def task_flow(
    task: str,
    sandbox: Path,
    display: Callable[[str], None],
    display_error: Callable[[str], None],
    display_script: Callable[[str], None],
    request_approval: Callable[[str, str], Awaitable[bool]],
    update_status: Callable[[str], None],
) -> None:
    """
    Execute the task workflow with callback-based UI updates.

    Args:
        task: User's task description
        sandbox: Sandbox path
        display: Callback for general messages
        display_error: Callback for error messages
        display_script: Callback for script display
        request_approval: Async callback for approval flow (returns bool)
        update_status: Callback for status bar updates
    """
    try:
        # Step 1: Generate planning script using Planner Agent with syntax validation
        update_status("Calling AI planner...")
        display("[dim]Asking AI to plan the task...[/dim]")
        planner_agent = PlannerAgent()

        plan_response = await generate_script_with_validation(
            agent_call=lambda error_feedback: planner_agent.call(
                task if error_feedback is None else task + error_feedback,
                sandbox
            ),
            display=display,
            display_error=display_error,
        )

        if plan_response is None:
            return

        plan_script = plan_response["script"]

        # Step 2: Validate planning script is read-only
        update_status("Validating plan...")
        display("[dim]Checking plan safety...[/dim]")
        if classify_script(plan_script, sandbox) != ScriptClassification.READ:
            display_error("Cannot access that location.")
            return

        # Step 3: Execute planning script
        update_status("Running analysis...")
        display("[dim]Executing analysis script...[/dim]")
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

        # Step 5: Generate execution script using Executor Agent with syntax validation
        update_status("Generating execution plan...")
        display("[dim]AI is creating the execution script...[/dim]")
        executor_agent = ExecutorAgent()

        exec_response = await generate_script_with_validation(
            agent_call=lambda error_feedback: executor_agent.call(
                task,
                read_result.stdout if error_feedback is None else read_result.stdout + error_feedback,
                sandbox
            ),
            display=display,
            display_error=display_error,
        )

        if exec_response is None:
            return

        # Step 6: Validate execution script safety
        update_status("Validating execution...")
        display("[dim]Checking execution script safety...[/dim]")
        if classify_script(exec_response["script"], sandbox) == ScriptClassification.UNSAFE:
            display_error("Cannot perform that operation.")
            return

        # Step 7: Request approval (async callback)
        update_status("Awaiting approval...")
        approved = await request_approval(exec_response["explanation"], exec_response["script"])

        if not approved:
            display("Cancelled.")
            return

        # Step 8: Execute the write script
        update_status("Executing changes...")
        display("[dim]Running the execution script...[/dim]")
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
        update_status("Summarizing results...")
        display("[dim]AI is summarizing the changes...[/dim]")
        summary_agent = SummaryAgent()
        summary_response = await summary_agent.call("task", task, write_result.stdout)
        display(summary_response["summary"])

    except Exception as e:
        display_error(f"Task failed: {str(e)}")
