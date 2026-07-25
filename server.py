import sys
from mcp.server.fastmcp import FastMCP 
from engine import Game,load_scenario
scenario_path = sys.argv[1] if len(sys.argv) > 1 else "scenarios/tutorial.json"
game = Game(load_scenario(scenario_path))
mcp = FastMCP("escape-room")
@mcp.tool(description="Look at the panel and see the module you are currently on.")
def look()->str:
    return game.look()
@mcp.tool(description="Try an action on the current module, e.g. 'cut the blue wire' or 'hold'.")
def submit(action:str)->str:
    return game.submit(action)

@mcp.tool(description="Read the panel's instruction manual. Only the Expert uses this.")
def read_manual() -> str:
    return game.read_manual()


@mcp.tool(description="Radio a message to your partner.")
def send_message(agent: str, text: str) -> str:
    return game.send_message(agent, text)


@mcp.tool(description="Read the messages your partner sent you.")
def read_messages(agent: str) -> str:
    return game.read_messages(agent)


@mcp.tool(description="Write a short note in your private notebook.")
def remember(agent: str, note: str) -> str:
    return game.remember(agent, note)


@mcp.tool(description="Read back the notes in your private notebook.")
def recall(agent: str) -> str:
    return game.recall(agent)


@mcp.tool(description="Check if the game is still playing, won, or lost.")
def status() -> str:
    return game.status


if __name__ == "__main__":
    mcp.run()
