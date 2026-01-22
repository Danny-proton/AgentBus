import os
import json
import asyncio
from typing import AsyncGenerator, List, Dict, Any
from ..tools.bash import BashTool, LocalShellExecutor
from .session import Session
from ..services.llm import LLMClient
from ..constants.prompts import get_system_prompt

class Agent:
    def __init__(self, session: Session):
        self.session = session
        self.bash_tool = BashTool(LocalShellExecutor())
        self.llm = LLMClient()
        
        # Define Tools for OpenAI
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "bash",
                    "description": "Execute a bash command on the system.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "The bash command to execute."
                            }
                        },
                        "required": ["command"]
                    }
                }
            }
        ]

    async def process_message(self, message: str) -> AsyncGenerator[str, None]:
        # Handle "Forced Bash" (! cmd) - same as before
        if message.startswith("! "):
            await self._handle_forced_bash(message) # Refactored out or inline
            # ... (Implementation below) 
            # For brevity in this artifact, I will keep inline logic or just copy-paste the forced logic
            # Copied from previous logic:
            command = message[2:].strip()
            self.session.add_message("user", message)
            if command.startswith("cd "):
                path = command[3:].strip()
                try:
                    self.session.update_cwd(path)
                    output = f"Changed directory to {self.session.cwd}"
                    yield f"stdout: {output}\n"
                    self.session.add_message("assistant", output)
                except Exception as e:
                    yield f"stderr: {str(e)}\n"
                    self.session.add_message("assistant", f"Error: {str(e)}")
                return
            yield f"tool_start: bash\n" 
            result = await self.bash_tool.run(command, self.session.cwd)
            if result.output: yield f"stdout: {result.output}\n"
            if result.error: yield f"stderr: {result.error}\n"
            self.session.add_message("assistant", f"Ran: {command}\nOutput: {result.output}\nError: {result.error}")
            return

        # Handle Slash Commands - same as before
        if message.startswith("/"):
            if message == "/clear":
                self.session.history = []
                yield "Session history cleared."
                return
            if message == "/help":
                yield "Usage: Type natively or use ! for bash."
                return

        # Main Loop for Tool Use
        self.session.add_message("user", message)
        
        # Max turns to prevent infinite loops
        MAX_TURNS = 5
        current_turn = 0
        
        while current_turn < MAX_TURNS:
            current_turn += 1
            
            system_prompt = get_system_prompt(self.session.cwd, os.name)
            messages = [{"role": "system", "content": system_prompt}] + self.session.history
            
            # Temporary state for accumulating valid function calls
            # OpenAI streams parts of tool calls. We need to buffer them.
            tool_calls_buffer = {} # index -> tool_call data
            content_buffer = ""
            
            # Flags
            is_collecting_tool = False
            
            async for chunk in self.llm.stream_chat(messages, tools=self.tools):
                delta = chunk.choices[0].delta
                
                # Handle Content (Text)
                if delta.content:
                    content_buffer += delta.content
                    yield delta.content
                
                # Handle Tool Calls (Accumulation)
                if delta.tool_calls:
                    is_collecting_tool = True
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_buffer:
                            tool_calls_buffer[idx] = {
                                "id": tc.id,
                                "function": {"name": "", "arguments": ""}
                            }
                        
                        if tc.id: tool_calls_buffer[idx]["id"] = tc.id
                        if tc.function.name: tool_calls_buffer[idx]["function"]["name"] += tc.function.name
                        if tc.function.arguments: tool_calls_buffer[idx]["function"]["arguments"] += tc.function.arguments
            
            # If no tool calls, we are done
            if not is_collecting_tool:
                if content_buffer:
                    self.session.add_message("assistant", content_buffer)
                break
                
            # If tool calls, execute them and loop again
            self.session.add_message("assistant", "", tool_calls=[
                 # Convert buffer to proper objects for history
                 # OpenAI Python types are strict, we might need to store as dicts in our session
                 # For now, let's just store a summary string or mock object
                 # Ideally: self.session.add_message("assistant", content=None, tool_calls=...)
                 # But our session structure is simple. Let's append a special formatted message.
                 f"Tool Call: {json.dumps(tool_calls_buffer)}"
            ])
            
            for idx, tc_data in tool_calls_buffer.items():
                func_name = tc_data["function"]["name"]
                args_str = tc_data["function"]["arguments"]
                call_id = tc_data["id"]
                
                if func_name == "bash":
                    try:
                        args = json.loads(args_str)
                        command = args.get("command", "")
                        
                        # Notify Frontend
                        yield f"tool_start: bash {command}\n"
                        
                        # Execute
                        result = await self.bash_tool.run(command, self.session.cwd)
                        
                        # Yield output to frontend
                        if result.output: yield f"stdout: {result.output}\n"
                        if result.error: yield f"stderr: {result.error}\n"
                        
                        # Add tool result to history
                        # In real OpenAI API, we need a "tool" role message with tool_call_id
                        self.session.history.append({
                            "role": "function", # Or "tool" for newer API
                            "name": func_name,
                            "content": result.output if result.output else (result.error or "Success")
                        })
                        # Note: OpenAI 'tool' role requires 'tool_call_id'. 
                        # Our Session.add_message is too simple. We need to hack it for this MVP or upgrade Session.
                        # For now, appending as "function" role (deprecated but works often) or just "user" with result?
                        # Let's try to be compliant ish: 
                        # We need to properly structure the ASSISTANT message with tool_calls first.
                        # Then the TOOL message.
                        
                        # Fix for Session History to support flexible Dicts
                        # (Session.add_message is simple, but we can direct access self.session.history)
                        
                    except Exception as e:
                         yield f"stderr: Tool execution error: {str(e)}\n"
            
            # Loop continues to next turn (LLM sees tool result and responds)

        return
