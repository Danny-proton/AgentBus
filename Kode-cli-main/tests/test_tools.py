import pytest
from app.tools.bash import BashTool, LocalShellExecutor

@pytest.mark.asyncio
async def test_date_command():
    executor = LocalShellExecutor()
    tool = BashTool(executor)
    result = await tool.run("date", cwd=".")
    assert result.output is not None
    assert result.error is None or result.error == ""

@pytest.mark.asyncio
async def test_echo_command():
    executor = LocalShellExecutor()
    tool = BashTool(executor)
    result = await tool.run("echo 'hello world'", cwd=".")
    assert "hello world" in result.output

@pytest.mark.asyncio
async def test_invalid_command():
    executor = LocalShellExecutor()
    tool = BashTool(executor)
    result = await tool.run("invalid_command_xyz", cwd=".")
    # Standard shell error usually goes to stderr
    assert result.error is not None
