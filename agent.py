import os
import asyncio
from google.genai.errors import ClientError
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-3.1-flash-lite"

ROLE_TOOLS = {
    "operator": {"look", "submit", "send_message", "read_messages", "remember", "recall"},
    "expert": {"read_manual", "send_message", "read_messages", "remember", "recall"},
}

JSON_TO_GEMINI = {"string": "STRING", "integer": "INTEGER", "number": "NUMBER", "boolean": "BOOLEAN"}


def make_client():
    return genai.Client(api_key=API_KEY)


def build_system_prompt(role):
    shared = (
        "You are playing a two-person escape room and neither of you can escape alone. "
        "Talk with send_message and read_messages. Use remember and recall for notes. "
        "Be decisive and brief. Do NOT repeat yourself or endlessly confirm. Take ONE action per turn."
    )
    if role == "operator":
        return (
            "You are the OPERATOR. " + shared + " "
            "You can see and act on the panel with look and submit; you do NOT have the manual. "
            "Solving the current module automatically reveals the next one - there is NO 'switch' or 'next' action. "
            "The only valid actions are physical ones like cutting a wire or holding/pressing a button. "
            "Steps: look, describe exactly what you see to the Expert, wait for their instruction, "
            "then submit that exact action immediately. Once the Expert tells you an action, submit it - do not ask again."
        )
    return (
        "You are the EXPERT. " + shared + " "
        "You have the manual (read_manual) but you CANNOT see the panel. "
        "Read the manual once, ask what the Operator sees if needed, apply the matching rule, "
        "and tell them the single exact action (for example 'cut the blue wire' or 'hold the button'). "
        "Give each instruction once and clearly; do not keep re-explaining."
    )


def to_gemini_tools(mcp_tools):
    declarations = []
    needs_agent = set()
    for tool in mcp_tools:
        schema = tool.inputSchema
        props = {}
        for name, spec in schema.get("properties", {}).items():
            if name == "agent":
                needs_agent.add(tool.name)
                continue
            props[name] = types.Schema(type=JSON_TO_GEMINI.get(spec.get("type"), "STRING"))
        required = [r for r in schema.get("required", []) if r != "agent"]
        parameters = types.Schema(type="OBJECT", properties=props, required=required) if props else None
        declarations.append(types.FunctionDeclaration(name=tool.name, description=tool.description or "", parameters=parameters))
    return [types.Tool(function_declarations=declarations)], needs_agent


def tool_result_text(result):
    return "\n".join(block.text for block in result.content if hasattr(block, "text"))

async def generate_with_retry(client, **kwargs):
    for attempt in range(6):
        try:
            return await client.aio.models.generate_content(**kwargs)
        except ClientError as error:
            if error.code == 429 and attempt < 5:
                print("rate limited, waiting 20s...")
                await asyncio.sleep(20)
                continue
            raise
        
class Agent:
    def __init__(self, role, session, client, mcp_tools):
        self.role = role
        self.session = session
        self.client = client
        selected = [t for t in mcp_tools if t.name in ROLE_TOOLS[role]]
        self.tools, self.needs_agent = to_gemini_tools(selected)
        self.system = build_system_prompt(role)
        self.contents = [types.Content(role="user", parts=[types.Part(text="You are now in the room. Take your first action.")])]
        self.last_tokens = 0

    async def call_tool(self, name, arguments):
        args = dict(arguments)
        if name in self.needs_agent:
            args["agent"] = self.role
        result = await self.session.call_tool(name, args)
        return tool_result_text(result)

    async def take_turn(self):
        response = await generate_with_retry(
            self.client,
            model=MODEL,
            contents=self.contents,
            config=types.GenerateContentConfig(system_instruction=self.system, tools=self.tools),
        )
        self.last_tokens = response.usage_metadata.total_token_count
        reply = response.candidates[0].content
        self.contents.append(reply)

        said = ""
        actions = []
        responses = []
        for part in reply.parts or []:
            if part.text:
                said += part.text
            if part.function_call:
                call = part.function_call
                args = dict(call.args)
                output = await self.call_tool(call.name, args)
                responses.append(types.Part.from_function_response(name=call.name, response={"result": output}))
                actions.append((call.name, args, output))

        if responses:
            self.contents.append(types.Content(role="user", parts=responses))
        else:
            self.contents.append(types.Content(role="user", parts=[types.Part(text="Take an action using one of your tools.")]))

        return said.strip(), actions