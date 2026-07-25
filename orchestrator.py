import asyncio
import sys
import time


from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from rich.console import Console

from agent import Agent, MODEL, make_client
from engine import load_scenario
from tracer import Tracer

MAX_TURNS = 50
COLORS = {"operator": "cyan", "expert": "magenta"}
console = Console()



async def get_status(session):
    result = await session.call_tool("status", {})
    return result.content[0].text


def show(role, said, actions):
    color = COLORS[role]
    if said:
        console.print(f"{role.upper()}: {said}", style=color, markup=False)
    for name, args, output in actions:
        console.print(f"   -> {name} {args}", style=color, markup=False)
        console.print(f"      {output}", style="green", markup=False)


async def play(scenario_path):
    server = StdioServerParameters(command=sys.executable, args=["server.py", scenario_path])
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            mcp_tools = (await session.list_tools()).tools
            client =make_client()

            operator = Agent("operator", session, client, mcp_tools)
            expert = Agent("expert", session, client, mcp_tools)
            players = [operator, expert]
            tracer = Tracer(scenario_path, MODEL)

            console.rule("Escape room starting")
            console.print(load_scenario(scenario_path)["intro"], style="yellow", markup=False)

            for turn in range(MAX_TURNS):
                agent = players[turn % 2]
                start = time.perf_counter()
                said, actions = await agent.take_turn()
                seconds = time.perf_counter() - start
                show(agent.role, said, actions)
                status = await get_status(session)
                tracer.log(turn, agent.role, said, actions, agent.last_tokens, seconds, status)
                if status != "playing":
                    console.rule(f"Game over: {status} in {turn + 1} turns")
                    path = tracer.finish(status, turn + 1)
                    console.print(f"Trace saved to {path}", style="yellow", markup=False)
                    return

            console.rule("Turn limit reached - nobody escaped")
            
            path = tracer.finish("timeout", MAX_TURNS)
            console.print(f"Trace saved to {path}", style="yellow", markup=False)
      
if __name__ == "__main__":
    scenario = sys.argv[1] if len(sys.argv) > 1 else "scenarios/tutorial.json"
    asyncio.run(play(scenario))
            