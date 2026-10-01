import os
from typing import TypedDict, Annotated
import operator

import psycopg
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import AnyMessage, AIMessage, HumanMessage, SystemMessage

from langchain_groq import ChatGroq
import asyncio
from mcp_client import (
    tavily_mcp_search,
    aviationstack_mcp_call,
    weather_mcp_search,
    forecast_mcp_search,
    extract_destination,
)
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Add it to .env, for example: "
        "DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres"
    )

llm = ChatGroq(model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"))

FLIGHT_AGENT_PROMPT = """

    You are a travel agent. You are given a user query and a list of flight and hotel results.
    You need to create a itinerary for the user.

    User query: {query}
    Airport data: {airport_data}
    Airline data: {airline_data}

    Generate:

    1. Likely departure and arrival airports for the user query.
    2. Likeley arrival and departure dates for the user query.
    3. Airlines serving this route.
    4. Estimated airfares.
    5. Estimated flight duration.
    5. Peak season price warning.
    6. Booking advice.
"""
class TravelState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    user_query: str
    flight_results: str
    hotel_results: str
    itinerary: str
    llm_calls: int
    weather_results: str

def flight_agent(state: TravelState):
    query = state["user_query"]

    try:
        airports = asyncio.run(aviationstack_mcp_call("list_airports"))
        airlines = asyncio.run(aviationstack_mcp_call("list_airlines"))
        prompt= FLIGHT_AGENT_PROMPT.format(
            query=query, 
            airport_data=str(airports)[:3000], 
            airline_data=str(airlines)[:3000])
        
        response = llm.invoke([SystemMessage(content=prompt), HumanMessage(content=query)])
        flight_data = response.content
    except Exception as e:
        print(f"Error fetching flight data: {str(e)}")
        flight_data = ""
    return {
        "flight_results": flight_data,
        "messages": [AIMessage(content="Flight recommendations generated")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }

def hotel_agent(state: TravelState) -> TravelState:
    query = f"Best hotels in {state['user_query']}"
    hotel_results = asyncio.run(tavily_mcp_search(query))
    return {
        "hotel_results": hotel_results,
        "messages": [AIMessage(content="Hotel data fetch")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }

def weather_agent(state: TravelState) -> TravelState:
    city = extract_destination(state['user_query'])
    weather = asyncio.run(weather_mcp_search(city))
    forecast = asyncio.run(forecast_mcp_search(city))
    return {
        "weather_results": f"""
        Current weather: {weather},
        Forecast: {forecast}
        """,
        "messages": [AIMessage(content="Weather data fetched")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }   

def itinerary_agent(state: TravelState) -> TravelState:
    prompt = f"""
    You need to create a itinerary for the user.

    User query: {state['user_query']}
    Flight results: {state['flight_results']}
    Hotel results: {state['hotel_results']}
    Weather results: {state['weather_results']}

    Create a itinerary for the user.
    """

    response = llm.invoke([SystemMessage(content=prompt), HumanMessage(content=state['user_query'])])
    return {
        "itinerary": response.content,
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }

graph = StateGraph(TravelState)
graph.add_node("flight_agent", flight_agent)
graph.add_node("hotel_agent", hotel_agent)
graph.add_node("weather_agent", weather_agent)
graph.add_node("itinerary_agent", itinerary_agent)

graph.add_edge(START, "flight_agent")
graph.add_edge("flight_agent", "hotel_agent")
graph.add_edge("hotel_agent", "weather_agent")
graph.add_edge("weather_agent", "itinerary_agent")
graph.add_edge("itinerary_agent", END)

_conn = psycopg.connect(DATABASE_URL, autocommit=True)
checkpointer = PostgresSaver(conn=_conn)
checkpointer.setup()

app = graph.compile(checkpointer=checkpointer)

if __name__ == "__main__":
    config = {"configurable": {"thread_id": "1"}}
    user_input = input("Enter your query: ")
    result = app.invoke({"messages": [HumanMessage(content=user_input)], 
    "user_query": user_input, "flight_results": "", 
    "hotel_results": "", "itinerary": "", 
    "llm_calls": 0}, 
    config=config)
    print(result)
    for message in result["messages"]:
        print(message.content)