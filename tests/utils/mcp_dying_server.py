import os

from mcp.server.mcpserver import MCPServer

server = MCPServer("dying")


@server.tool()
def ping() -> str:
    return "pong"


@server.tool()
def crash() -> str:
    os._exit(1)


if __name__ == "__main__":
    server.run(transport="stdio")
