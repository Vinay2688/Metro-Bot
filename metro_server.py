import time
from typing import Literal, Optional

try:
    from mcp.server.mcpserver import MCPServer as _Server        # mcp 2.x
    from mcp.server.mcpserver.exceptions import ToolError
except ImportError:
    from mcp.server.fastmcp import FastMCP as _Server            # mcp 1.x
    from mcp.server.fastmcp.exceptions import ToolError

import metro

mcp = _Server("metro-bot")

@mcp.tool()
def get_next_buses(
    direction: Literal["toward_downtown", "away_from_downtown", "both"] = "both",
    route: Optional[str] = None,
    limit: int = 5,
) -> dict:
    """Get the next live Cincinnati Metro bus departures from the University of
    Cincinnati campus stop (Jefferson Ave & University Ave).

    direction: 'toward_downtown' only if the user asks about going downtown,
    'away_from_downtown' for the opposite, otherwise 'both'.
    route: optional route number such as '19', '78' or 'M+'. Use it when the user
    asks about a specific route.
    limit: how many departures to return (1-10).

    Every departure includes its route, direction, clock time and minutes away.
    Data is live and changes every minute, so call this tool again for each question.
    """
    limit = max(1, min(limit, 10))
    try:
        departures = metro.next_departures(direction, limit, route)
    except ValueError as e:
        raise ToolError(str(e))
    return {
        "as_of": time.strftime("%I:%M:%S %p"),
        "count": len(departures),
        "departures": departures,
    }

@mcp.tool()
def get_route_info(route: str) -> dict:
    """Explain where a Cincinnati Metro route goes. Returns the route's full name and
    its destinations for each of its two directions (as shown on the bus sign).

    route: the route number, such as '19', '78' or 'M+'.
    Use this whenever the user asks where a route goes or what it connects.
    """
    try:
        return metro.route_info(route)
    except ValueError as e:
        raise ToolError(str(e))


@mcp.tool()
def get_bus_locations(route: str) -> dict:
    """Show where each active bus of a Cincinnati Metro route is right now, from
    live GPS. Each bus has its destination (heading_to), the closest bus stop
    (near_stop), how far from that stop it is in meters, and how many seconds ago
    its position was last updated.

    route: the route number, such as '19', '78' or 'M+'.
    Use this when the user asks where a bus or route is right now. Describe
    positions as 'near' a stop, since the closest stop is only an approximation.
    """
    try:
        buses = metro.bus_locations(route)
    except ValueError as e:
        raise ToolError(str(e))
    return {
        "as_of": time.strftime("%I:%M:%S %p"),
        "count": len(buses),
        "buses": buses,
    }    

if __name__ == "__main__":
    mcp.run()   # talks over stdio