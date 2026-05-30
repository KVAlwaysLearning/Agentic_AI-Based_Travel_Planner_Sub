import os
import json
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import StructuredTool
from langchain_core.callbacks import BaseCallbackHandler

# Use the classic paths for AgentExecutor and create_tool_calling_agent
try:
    from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
except ImportError:
    from langchain.agents import AgentExecutor, create_tool_calling_agent

import tools

class AgentTracerCallbackHandler(BaseCallbackHandler):
    """
    Custom LangChain Callback Handler to hook into agent actions 
    and bridge tool calls to the Streamlit tracing UI.
    """
    def __init__(self, callback_log=None):
        super().__init__()
        self.callback_log = callback_log
        self.traces = []
        self.step = 0
        self.current_tool_name = None
        self.current_tool_args = None

    def on_llm_start(self, serialized, prompts, **kwargs):
        if self.callback_log:
            self.callback_log("agent_thinking", "Agent reasoning loop running...", {})

    def on_agent_action(self, action, **kwargs):
        self.step += 1
        self.current_tool_name = action.tool
        self.current_tool_args = action.tool_input if isinstance(action.tool_input, dict) else {"input": action.tool_input}
        
        if self.callback_log:
            self.callback_log(
                "tool_call_start", 
                f"🤖 Agent decided to run **{self.current_tool_name}** with arguments: `{json.dumps(self.current_tool_args)}`", 
                {"tool": self.current_tool_name, "args": self.current_tool_args}
            )

    def on_tool_end(self, output, **kwargs):
        output_dict = {}
        if isinstance(output, str):
            try:
                output_dict = json.loads(output)
            except Exception:
                output_dict = {"summary": output}
        elif isinstance(output, dict):
            output_dict = output
            
        success = output_dict.get("success", True)
        status_indicator = "✅ Success" if success else "❌ Error"
        summary_text = output_dict.get("summary", output_dict.get("message", str(output)))
        
        if self.callback_log:
            self.callback_log(
                "tool_call_result", 
                f"{status_indicator} from **{self.current_tool_name}**: `{summary_text}`",
                {"tool": self.current_tool_name, "output": output_dict}
            )
            
        self.traces.append({
            "step": self.step,
            "tool": self.current_tool_name,
            "arguments": self.current_tool_args,
            "result": output_dict
        })


def run_travel_agent(user_prompt: str, callback_log=None) -> dict:
    """
    Runs the LangChain Groq Travel Agent.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return {
            "success": False,
            "itinerary": "Error: GROQ_API_KEY is not set in environment or sidebar.",
            "traces": []
        }
    
    # Initialize the LLM via ChatGroq
    llm = ChatGroq(
        model="llama-3.1-8b-instant", 
        temperature=0.2,
        api_key=api_key
    )
    
    langchain_tools = [
        StructuredTool.from_function(func=tools.search_flights, name="search_flights", description="Search flights between cities. Returns available options."),
        StructuredTool.from_function(func=tools.recommend_hotels, name="recommend_hotels", description="Search hotels in a city with filters."),
        StructuredTool.from_function(func=tools.discover_places, name="discover_places", description="Discover attractions in a city."),
        StructuredTool.from_function(func=tools.lookup_weather, name="lookup_weather", description="Lookup weather for destination."),
        StructuredTool.from_function(func=tools.estimate_budget, name="estimate_budget", description="Accepts a summary string to finalize total budget calculations."),
        StructuredTool.from_function(
            func=tools.log_city_data, 
            name="log_city_data", 
            description="Save flight or hotel costs. Args: city, category ('flight' or 'hotel'), amount."
        ),
        StructuredTool.from_function(
            func=tools.generate_itinerary_tables,
            name="generate_itinerary_tables",
            description="Takes a list of daily trip data and generates the perfectly formatted Expense Log and Budget Breakdown Markdown tables."
        ) 
    ]
    
    system_instruction = (
        "You are an Elite Travel Specialist. For multi-city trips, process every flight leg and every destination city separately.\n\n"
        "MANDATORY TOOL SEQUENCE — repeat for EVERY destination city before writing any output:\n"
        "  For city 1: call search_flights, then call recommend_hotels.\n"
        "  For city 2: call search_flights, then call recommend_hotels.\n"
        "  ... and so on for every city, no matter how short the trip.\n"
        "  Then call log_city_data for each cost, then generate_itinerary_tables.\n\n"
        "1. After all tool calls are done, compile the daily details into a JSON list of dictionaries.\n"
        "2. Call 'generate_itinerary_tables' with your JSON list.\n"
        "3. IMPORTANT: Print ONLY the Markdown returned by the tool. DO NOT manually create tables or perform math in your response.\n\n"
        "## FLIGHT SELECTION RULES:\n"
        "- Check for direct flights first. If there are no direct flights between two cities, you MUST add a line: '⚠️ Note: There are no direct flights between [Origin] and [Destination]. Showing connecting flight route.'\n"
        "- Then list EVERY single connecting flight segment with: Flight number, airline, from city, to city, its individual price, departure and arrival times.\n"
        "- For connecting routes, always add after all segments: '**Total Flight Cost: ₹[sum of all segment prices]**'. Use this total, not any individual segment price.\n"
        "- For the day-by-day table, the travel day row must show the CUMULATIVE flight cost of all connecting flights combined.\n\n"
        "## 📑 TRIP SUMMARY\n"
        "- **Origin**: [Origin City]\n"
        "- **Destination**: [Destination Cities, comma-separated]\n"
        "- **Duration**: [X] Days\n"
        "- **Dates**: [Dates, or 'Flexible']\n\n"
        "# 🗺️ TRIP PLAN & ITINERARY\n\n"
        "## ✈️ SELECTED FLIGHT OPTIONS\n"
        "(Include a line for direct / no-direct warning if applicable. List EVERY single direct or connecting flight segment clearly. Repeat for each segment:)\n"
        "- **Segment [X]**: **From**: [City] -> **To**: [City]\n"
        "- **Airline & Flight**: [Airline & Flight ID] (Selected because [Cheapest/Fastest/Balanced])\n"
        "- **Schedule**: [Departure Time] -> [Arrival Time]\n"
        "- **Price**: ₹[per-segment price]\n"
        "- **Duration**: [Duration]\n"
        "(For connecting routes only, add after all segments: **Total Flight Cost: ₹[sum]**)\n\n"
        "## 🏨 RECOMMENDED HOTELS\n"
        "You MUST show exactly one hotel per destination city using hotel_name and price_per_night from the recommend_hotels tool result.\n"
        "DO NOT copy the tool summary field into Why selected — write your own brief reason based on stars and price.\n"
        "(Repeat once per destination city:)\n"
        "- **Hotel Name**: [hotel_name from tool]\n"
        "- **Address**: [address from tool]\n"
        "- **Star Rating**: [stars from tool]/5\n"
        "- **Price**: ₹[price_per_night from tool]/night\n"
        "- **Selected Amenities**: [amenities from tool]\n"
        "- **Why selected**: [Your own one-sentence reason — do NOT paste the tool summary here]\n\n"
        "## 📅 DAY-BY-DAY ITINERARY\n"
        "(YOU MUST PROVIDE A SECTION FOR EVERY DAY. DO NOT SKIP DAYS:)\n"
        "### Day [X]: [Catchy Title]\n"
        "- **Weather**: [Min/Max Temp, Condition]\n"
        "- **Morning**: [Activity + Description]\n"
        "- **Afternoon**: [Activity + Food Recommendation]\n"
        "- **Evening**: [Relaxing stroll/Dinner neighborhood]\n"
    )
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_instruction),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])
    
    agent_runnable = create_tool_calling_agent(
        llm=llm,
        tools=langchain_tools,
        prompt=prompt_template
    )
    
    agent_executor = AgentExecutor(
        agent=agent_runnable,
        tools=langchain_tools,
        verbose=True,
        max_iterations=25,
        handle_parsing_errors=True
    )
    
    tracer = AgentTracerCallbackHandler(callback_log=callback_log)
    
    try:
        if callback_log:
            callback_log("agent_thinking", "Initializing LangChain Specialist Agent...", {})
            
        response = agent_executor.invoke(
            {"input": user_prompt},
            config={"callbacks": [tracer]}
        )
        
        if callback_log:
            callback_log("agent_complete", "✅ Agent planning complete!", {})
            
        return {
            "success": True,
            "itinerary": response["output"],
            "traces": tracer.traces
        }
    except Exception as err:
        return {
            "success": False,
            "itinerary": f"Error running agent: {str(err)}",
            "traces": tracer.traces
        }
