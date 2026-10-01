# VoyageAI

VoyageAI is a travel-planning app. You describe a trip in plain language, and a small team of agents looks up flights, hotels, and weather, then writes a day-by-day itinerary.

The interface is a Streamlit page. Behind it, a [LangGraph](https://github.com/langchain-ai/langgraph) graph calls live data through the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) and a Groq chat model.

## Demo



https://github.com/user-attachments/assets/5ac27c08-cbfc-4f9e-9a18-d2c4bb1839d8





## What you get

A typical request looks like: “Plan a 7-day trip to Japan including flights, hotels and sightseeing under ₹2 lakhs.”

The app returns:

- **Flights** — likely airports, dates, airlines on the route, estimated fares and duration, a peak-season price warning, and booking advice
- **Hotels** — web search results for places to stay that match the request
- **Weather** — current conditions and a short forecast for the destination city (used when the itinerary is written)
- **Itinerary** — a single plan that combines the query with the flight, hotel, and weather findings

The finished plan is shown in the UI, offered as a download, and written to `mcp/travel_plans/travel_plan_<timestamp>.md`.

The home page also has a destination carousel (Italy, Paris, Switzerland, Bali, Dubai, India, Thailand). Choosing a card fills the trip box with a starter prompt for that place.

## How it works

```text
Streamlit UI (mcp/frontend.py)
        │
        ▼
LangGraph (mcp/main.py)
        │
        ├─ flight_agent
        │     Aviationstack MCP (airports + airlines)
        │     Groq writes flight recommendations
        │
        ├─ hotel_agent
        │     Tavily MCP web search
        │
        ├─ weather_agent
        │     Groq extracts the destination city
        │     Local OpenWeather MCP (current weather + forecast)
        │
        └─ itinerary_agent
              Groq writes the final plan from everything above
```

The graph is a straight line. Each node finishes before the next one starts. There is no branching or retry loop.

State is a `TravelState` dictionary:

| Field | Role |
| --- | --- |
| `user_query` | The trip description from the UI or CLI |
| `messages` | Chat messages appended as agents finish |
| `flight_results` | Flight recommendations written by the model |
| `hotel_results` | Raw Tavily search output |
| `weather_results` | Current weather plus forecast text |
| `itinerary` | Final plan |
| `llm_calls` | Count of model calls along the run |

LangGraph checkpoints each run in PostgreSQL (`PostgresSaver`) so a thread can be resumed. The UI always uses `thread_id` `"1"`.

### Agents

**Flight agent** (`flight_agent` in `mcp/main.py`)

Calls the Aviationstack MCP server for `list_airports` and `list_airlines`. Those payloads are truncated and passed to Groq with a prompt that asks for airports, dates, airlines, fares, duration, a peak-season warning, and booking advice. If the MCP call fails, flight data is left empty and the graph continues.

**Hotel agent** (`hotel_agent`)

Searches Tavily for “Best hotels in {user query}” through the hosted Tavily MCP server (`https://mcp.tavily.com`).

**Weather agent** (`weather_agent`)

Asks Groq to pull only the destination city or country out of the query, then calls the local weather MCP server for `get_current_weather` and `get_forecast`.

**Itinerary agent** (`itinerary_agent`)

Sends the original query plus flight, hotel, and weather text to Groq and stores the reply as the itinerary.

The Streamlit page streams graph updates (`app.stream(..., stream_mode="updates")`) and shows each finished agent in a live panel. The thinking checklist in the UI labels flights, hotels, itinerary, and a “final” step. Weather runs in the graph between hotels and the itinerary, and its output is included in the itinerary prompt. The saved Markdown file stores flights, hotels, and the itinerary. It does not have a separate weather section.

## Project layout

```text
VoyageAI/
├── .streamlit/config.toml      # Streamlit theme: hide sidebar, no usage stats
├── langgraph_env/              # Local Python virtualenv (do not commit)
├── travel_plans/               # Older saved plans from an earlier layout
└── mcp/
    ├── frontend.py             # Streamlit UI
    ├── main.py                 # LangGraph definition and CLI entry
    ├── mcp_client.py           # MCP clients for Tavily, Aviationstack, weather
    ├── openweather_mcp_server.py
    ├── tools/
    │   ├── flight_tool.py      # Direct Aviationstack HTTP helper (not used by the graph)
    │   └── tavily_tool.py      # Direct Tavily SDK helper (not used by the graph)
    ├── assets/                 # Hero and destination images
    ├── travel_plans/           # Plans saved by the current UI
    └── .env                    # API keys and DATABASE_URL (gitignored)
```

`mcp/tools/flight_tool.py` and `mcp/tools/tavily_tool.py` call Aviationstack and Tavily directly. The running app does not import them. Live lookups go through MCP in `mcp/mcp_client.py`.

## External services

| Service | Used for | How it is reached |
| --- | --- | --- |
| [Groq](https://groq.com/) | Destination extraction, flight write-up, itinerary | `langchain-groq` (`ChatGroq`) |
| [Tavily](https://tavily.com/) | Hotel web search | Remote MCP over streamable HTTP |
| [Aviationstack](https://aviationstack.com/) | Airport and airline lists | Local MCP server over stdio, launched with `uv` |
| [OpenWeather](https://openweathermap.org/) | Current weather and 5 forecast slots | Local FastMCP server in `openweather_mcp_server.py` |
| PostgreSQL | LangGraph checkpoints | `langgraph-checkpoint-postgres` |

The Aviationstack client in `mcp/mcp_client.py` starts a server from a fixed path:

```text
/Users/tanishka.yadav/Downloads/aviationstack-mcp-main
```

That directory must exist on this machine, and `uv` must be on `PATH`, or the flight agent will fail and continue with empty flight data. Point `args` in `aviationstack_client` at wherever you cloned [aviationstack-mcp](https://github.com/) if you move it.

Weather tools are started with the virtualenv interpreter:

```text
langgraph_env/bin/python mcp/openweather_mcp_server.py
```

The weather server exposes two tools:

- `get_current_weather(city)` — city, temperature (°C), feels-like, humidity, condition, wind speed
- `get_forecast(city)` — the next five OpenWeather 3-hour slots (time, temperature, description)

## Setup

Python 3.14 is what the checked-in virtualenv was built with. A recent 3.11+ interpreter should work if you recreate the environment.

1. Create and activate a virtualenv (or reuse `langgraph_env`):

```bash
python3 -m venv langgraph_env
source langgraph_env/bin/activate
```

2. Install the libraries the app imports:

```bash
pip install streamlit langchain-groq langchain-mcp-adapters langgraph \
  langgraph-checkpoint-postgres psycopg python-dotenv requests mcp
```

3. Run PostgreSQL and create a database the app can connect to. On first import, `PostgresSaver.setup()` creates the checkpoint tables.

4. Install [uv](https://docs.astral.sh/uv/) and clone the Aviationstack MCP server. Update the `--directory` path in `mcp/mcp_client.py` if it is not under `~/Downloads/aviationstack-mcp-main`.

5. Create `mcp/.env` (this file is gitignored):

```bash
GROQ_API_KEY=your_groq_key
GROQ_MODEL=openai/gpt-oss-20b
TAVILY_API_KEY=your_tavily_key
OPENWEATHER_API_KEY=your_openweather_key
AVIATIONSTACK_API_KEY=your_aviationstack_key
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres
```

`GROQ_MODEL` is optional. If it is missing, the code uses `openai/gpt-oss-20b`. `DATABASE_URL` is required; `mcp/main.py` exits on import without it. `langchain-groq` reads `GROQ_API_KEY` from the environment. The Aviationstack MCP process needs its own API key configured the way that server expects (often the same `AVIATIONSTACK_API_KEY`).

## Run

From the `mcp` directory, with the virtualenv active:

```bash
cd mcp
streamlit run frontend.py
```

Streamlit serves the UI locally (usually `http://localhost:8501`). Type a trip, or pick a destination card, then press **Generate My Travel Plan**.

You can also run the graph from the terminal:

```bash
cd mcp
python main.py
```

That prompts for a query, invokes the graph on thread `"1"`, and prints the result messages.

## Saved plans

Each successful UI run writes Markdown under `mcp/travel_plans/`. The file includes the query, timestamp, flight section, hotel section, itinerary, and the LLM call count. The page also offers a **Download Plan** button for the same content.

Plans already in `travel_plans/` at the repo root were produced by an earlier version of the app and are not written by the current UI.
