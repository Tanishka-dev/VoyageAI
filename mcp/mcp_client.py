import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_mcp_adapters.client import MultiServerMCPClient

_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_DIR)
load_dotenv(os.path.join(_DIR, ".env"))

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
_PYTHON = os.path.join(_ROOT, "langgraph_env", "bin", "python")
_WEATHER_SERVER = os.path.join(_DIR, "openweather_mcp_server.py")

tavily_client = MultiServerMCPClient({
    "tavily": {
        "transport": "streamable_http",
        "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}",
    },
})

aviationstack_client = MultiServerMCPClient({
    "aviationstack": {
        "transport": "stdio",
        "command": "uv",
        "args": [
            "--directory",
            "/Users/tanishka.yadav/Downloads/aviationstack-mcp-main",
            "run",
            "aviationstack-mcp",
        ],
    },
})

weather_client = MultiServerMCPClient({
    "weather": {
        "transport": "stdio",
        "command": _PYTHON,
        "args": [_WEATHER_SERVER],
    },
})

search_tool = None
weather_tool = None
forecast_tool = None
aviationstack_tools = None

llm = ChatGroq(model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"))


def extract_destination(query: str):
    prompt = f"""
    Extract only the destination city or country
    Query: {query}
    Return only destination name
    """
    response = llm.invoke(prompt)
    return response.content.strip()


async def initialize_weather_tools():
    global weather_tool, forecast_tool
    if weather_tool is not None and forecast_tool is not None:
        return
    tools = await weather_client.get_tools()
    weather_tool = next(tool for tool in tools if tool.name == "get_current_weather")
    forecast_tool = next(tool for tool in tools if tool.name == "get_forecast")
    if not weather_tool or not forecast_tool:
        raise ValueError("Weather or forecast tool not found")
    return weather_tool, forecast_tool


async def weather_mcp_search(city: str):
    await initialize_weather_tools()
    return await weather_tool.ainvoke({"city": city})


async def forecast_mcp_search(city: str):
    await initialize_weather_tools()
    return await forecast_tool.ainvoke({"city": city})


async def initialize_tavily_tools():
    global search_tool
    if search_tool is not None:
        return
    tools = await tavily_client.get_tools()
    search_tool = next(tool for tool in tools if tool.name == "tavily_search")


async def tavily_mcp_search(query: str):
    await initialize_tavily_tools()
    return await search_tool.ainvoke({"query": query})


async def aviationstack_mcp_call(tool_name: str, tool_args: dict = None):
    tools = await aviationstack_client.get_tools()
    tool = next(t for t in tools if t.name == tool_name)
    return await tool.ainvoke(tool_args or {})


async def get_airports():
    return await aviationstack_mcp_call("list_airports")


async def get_airlines():
    return await aviationstack_mcp_call("list_airlines")
