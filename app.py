import streamlit as st
import os
import agent
import tools
from datetime import datetime, date, timedelta

# Set Streamlit Page Config
st.set_page_config(page_title=" AI-Based Travel Planning Assistant", layout="wide")
st.title("")

# Clear State Memory Sidebar controller
with st.sidebar:
    st.header("⚙️ State Engine status")
    if st.button("🔄 Clear State Memory", type="secondary"):
        tools.reset_memory()
        st.success("State memory cleared!")
    
    st.info(f"Stored cost logs count: {len(tools.city_data_memory)} records")

# Primary Tab Navigation 
tab1, tab2 = st.tabs(["💬 AI Prompt Planner", "📔 Constraint Control Panel (Form Inputs)"])

# Define actual master lists from database
available_cities = ["Delhi", "Mumbai", "Hyderabad", "Bangalore", "Chennai", "Goa", "Kolkata", "Jaipur"]
available_attractions = ["lake", "temple", "museum", "park", "fort", "beach", "market", "monument"]

# Helper to extract origin and dest cities from prompt for custom solved table
def extract_trip_details_from_prompt(prompt, logged_cities=None):
    prompt_lower = prompt.lower()
    cities_in_prompt = []
    for c in available_cities:
        idx = prompt_lower.find(c.lower())
        if idx != -1:
            cities_in_prompt.append((idx, c))
    # Sort by appearance in the prompt
    cities_in_prompt.sort(key=lambda x: x[0])
    
    if not cities_in_prompt:
        return "Delhi", ["Mumbai"]
        
    # Determine origin
    origin = None
    origin_words = ["from", "starting in", "starting at", "originating in", "departure", "out of"]
    
    for idx, c in cities_in_prompt:
        # Get context preceding this city
        start_idx = max(0, idx - 15)
        context = prompt_lower[start_idx:idx]
        if any(ow in context for ow in origin_words):
            origin = c
            break
            
    dest_cities = []
    if origin:
        dest_cities = [c for _, c in cities_in_prompt if c != origin]
    else:
        # No explicit origin found
        if len(cities_in_prompt) == 1:
            single_city = cities_in_prompt[0][1]
            origin = "Delhi"
            if single_city == "Delhi":
                dest_cities = ["Mumbai"]
            else:
                dest_cities = [single_city]
        else:
            first_city = cities_in_prompt[0][1]
            if first_city == "Delhi" or first_city == "Hyderabad":
                origin = first_city
                dest_cities = [c for _, c in cities_in_prompt if c != origin]
            else:
                origin = "Delhi"
                dest_cities = [c for _, c in cities_in_prompt if c != "Delhi"]
                
    if not dest_cities:
        dest_cities = ["Delhi"] if origin != "Delhi" else ["Mumbai"]
        
    return origin, dest_cities

def extract_constraints_from_prompt(prompt):
    prompt_lower = prompt.lower()
    
    # 1. Extract days
    days = None
    import re
    words = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14
    }
    for word, val in words.items():
        if re.search(rf"\b{word}\s*days?\b", prompt_lower) or re.search(rf"\b{word}\s*-\s*days?\b", prompt_lower):
            days = val
            break
    if not days:
        digit_match = re.search(r"\b(\d+)\s*-\s*days?\b", prompt_lower) or re.search(r"\b(\d+)\s*days?\b", prompt_lower)
        if digit_match:
            try:
                days = int(digit_match.group(1))
            except ValueError:
                pass
                
    # 2. Extract start date
    start_date = None
    # Check YYYY-MM-DD
    match = re.search(r"\b(202\d-\d{2}-\d{2})\b", prompt)
    if match:
        start_date = match.group(1)
    else:
        # Check DD-MM-YYYY or DD/MM/YYYY
        match = re.search(r"\b(\d{2})[-/](\d{2})[-/](202\d)\b", prompt)
        if match:
            day, month, year = match.groups()
            start_date = f"{year}-{month}-{day}"
        else:
            # Check month-day names like "June 3"
            months = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december",
                      "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
            for m_idx, m in enumerate(months):
                pattern = rf"\b{m}\s*(\d{{1,2}})(?:st|nd|rd|th)?\b"
                m_match = re.search(pattern, prompt_lower)
                if m_match:
                    day_val = int(m_match.group(1))
                    month_num = (m_idx % 12) + 1
                    start_date = f"2026-{month_num:02d}-{day_val:02d}"
                    break
                pattern_rev = rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s*of\s*{m}\b"
                m_match_rev = re.search(pattern_rev, prompt_lower)
                if m_match_rev:
                    day_val = int(m_match_rev.group(1))
                    month_num = (m_idx % 12) + 1
                    start_date = f"2026-{month_num:02d}-{day_val:02d}"
                    break
                pattern_rev_simple = rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s*{m}\b"
                m_match_rev_s = re.search(pattern_rev_simple, prompt_lower)
                if m_match_rev_s:
                    day_val = int(m_match_rev_s.group(1))
                    month_num = (m_idx % 12) + 1
                    start_date = f"2026-{month_num:02d}-{day_val:02d}"
                    break
                    
    # 3. Extract budget/lodging type
    hotel_tier = "budget"
    if "cheap" in prompt_lower or "budget" in prompt_lower:
        hotel_tier = "cheapest" if "cheapest" in prompt_lower or "very cheap" in prompt_lower else "budget"
    elif "luxury" in prompt_lower or "luxurious" in prompt_lower or "expensive" in prompt_lower or "five star" in prompt_lower:
        hotel_tier = "luxurious"
        
    # 4. Extract attractions
    attraction = None
    for attr in available_attractions:
        if attr in prompt_lower:
            attraction = attr
            break
            
    is_completed_before = False
    before_keywords = ["before", "by", "complete before", "completed before", "end by", "finish by", "return by", "completed by", "arrive by", "back by", "leave before"]
    if any(kw in prompt_lower for kw in before_keywords):
        is_completed_before = True
            
    return days, start_date, hotel_tier, attraction, is_completed_before

with tab1:
    st.subheader("💬 AI Freeform Prompt Planner")
    st.markdown("Let our Specialist AI Agent plan your trip dynamically based on raw requirements!")
    
    user_query = st.text_area(
        "Where do you want to go? Include dates, cities, and budget.",
        placeholder="Example: I want a 5-day trip starting from Delhi. Visit Bangalore and Goa. Use budget hotels.",
        height=120,
        key="prompt_input"
    )

    button_clicked = st.button("🚀 Compose Travel Plan with Agent", type="primary")

    if button_clicked:
        if not user_query.strip():
            st.warning("Please type a planning query first!")
        else:
            # Check if number of cities exceeds number of days (m > n)
            origin, dest_cities = extract_trip_details_from_prompt(user_query)
            p_days, p_start_date, p_hotel_tier, p_attr, is_completed_before = extract_constraints_from_prompt(user_query)
            n_days = p_days if p_days is not None else 5
            m_cities = len(dest_cities)
            
            if m_cities > n_days:
                st.error(f"Tour not possible in {n_days} days, instead check schedule for {m_cities} days, or reduce no of destination or increase no of days.")
            else:
                # Solve completed_before vs started_on date
                if p_start_date:
                    try:
                        start_date_obj = datetime.strptime(p_start_date, "%Y-%m-%d")
                        if is_completed_before:
                            start_date_obj = start_date_obj - timedelta(days=(n_days - 1))
                        resolved_start_date_str = start_date_obj.strftime("%Y-%m-%d")
                    except Exception:
                        resolved_start_date_str = datetime.now().strftime("%Y-%m-%d")
                else:
                    resolved_start_date_str = datetime.now().strftime("%Y-%m-%d")

                end_date_obj = datetime.strptime(resolved_start_date_str, "%Y-%m-%d") + timedelta(days=n_days)
                date_range_str = f"{resolved_start_date_str} to {end_date_obj.strftime('%Y-%m-%d')}"

                payload = {
                    "origin": origin,
                    "cities": dest_cities,
                    "days": n_days,
                    "hotel_types": p_hotel_tier if p_hotel_tier else "budget",
                    "attractions": [p_attr] if p_attr else []
                }
                
                # Commit state to the constraint resolution engine
                tools.resolve_and_save_state(payload, date_range=date_range_str)

                st.subheader("🕵️‍♂️ Agent Reasoning Traces")
                trace_area = st.empty()
                log_messages = []

                def streamlit_logger(log_type, message, metadata):
                    icon = "⚙️" if log_type == "tool_call_start" else "✅"
                    log_messages.append(f"{icon} {message}")
                    trace_area.markdown("\n\n".join(log_messages))
                
                with st.spinner("Agent is planning your multi-city trip..."):
                    result = agent.run_travel_agent(user_query, callback_log=streamlit_logger)
                    
                if result.get("success"):
                    st.success("✨ Travel Plan generated successfully!")
                    st.markdown(result["itinerary"])
                else:
                    st.warning("⚠️ High demand warning: AI specialist is busy, but our Programmatic Constraint Engine solved your optimal route perfectly!")
                
                # Always render the Solved programmatically-supported tables
                costs_data = tools.run_full_itinerary_generation(tools.df_flights, tools.df_hotels)
                
                if isinstance(costs_data, dict) and "error" not in costs_data:
                    summary = costs_data.get("summary", {})
                    
                    st.markdown("---")
                    st.subheader("📊 Solved Package Cost Summary")
                    sc1, sc2, sc3, sc4 = st.columns(4)
                    sc1.metric("Flight Expense Log", f"₹{summary.get('total_flight', 0):,}")
                    sc2.metric("Hotels & Lodging", f"₹{summary.get('total_hotel', 0):,}")
                    sc3.metric("Daily Buffer Expense", f"₹{summary.get('total_misc', 0):,}")
                    sc4.metric("Grand Total Cost", f"₹{summary.get('grand_total', 0):,}")
                    
                    st.subheader("📅 Solved Day-by-Day Comprehensive Cost Schedule")
                    
                    flight_legs = costs_data.get("flight_legs", [])
                    hotel_details = costs_data.get("itinerary", [])
                    
                    rows = tools.build_cost_breakdown_table(
                        costs_data.get("itinerary", []),
                        costs_data.get("flight_legs", []),
                        costs_data.get("itinerary", []),
                        resolved_start_date_str
                    )
                
                    st.table(rows)
                    
                    # Print warning if there are no direct flights
                    no_direct_warnings = []
                    for leg in flight_legs:
                        if not leg.get("is_direct", True) and "leg" in leg:
                            try:
                                start_c, end_c = leg["leg"].split("->")
                                no_direct_warnings.append(f"⚠️ Note: There are no direct flights between {start_c} and {end_c}. Showing connecting flight route.")
                            except Exception:
                                pass
                    
                    for warn in no_direct_warnings:
                        st.warning(warn)
                        
                    # Flight Summary Table listing flight no, airline, from, to, cost
                    st.subheader("✈️ Selected Flights Summary Table")
                    flight_rows = []
                    for leg in flight_legs:
                        for segment in leg.get("segments", []):
                            flight_rows.append({
                                "Flight No": segment.get("flight_id"),
                                "Airline": segment.get("airline"),
                                "From": segment.get("from"),
                                "To": segment.get("to"),
                                "Cost": f"₹{segment.get('price'):,}"
                            })
                    if flight_rows:
                        st.table(flight_rows)
                    else:
                        st.info("No flight segment details available.")
                        
                    # Decision logic reasons
                    st.subheader("💡 Selection Intelligence & Decision Logic")
                    st.markdown("""
                    - **Flight Routing Selection**: 
                      - Cheaper and direct flight paths were prioritized.
                      - If direct flights do not exist, a custom BFS (Breadth-First Search) routing algorithm traversed alternative paths (e.g., through Kolkata) to resolve the absolute cheapest segment-by-segment chain of connections seamlessly.
                    - **Hotel Selection**: 
                      - Hotels of the requested class (e.g. Budget, Cheapest, or Luxury) with the highest verified rating scores (stars) were picked.
                    """)
                else:
                    st.error("Failed to solve optimal itinerary constraints.")
                    if not result.get("success"):
                        st.text(result.get("itinerary"))

with tab2:
    st.subheader("🎯 Flexible Constraint Selection Form")
    st.markdown("Customize precise input limits. Choose **Flexible** for any parameters you aren't certain on to auto-solve optimal allocations.")

    col1, col2 = st.columns(2)

    with col1:
        origin_input = st.selectbox(
            "1. Journey Origin City",
            options=["Flexible"] + available_cities,
            index=1 # Delhi default
        )
        
        dest_cities = st.multiselect(
            "2. Dest/Intermediate Cities to Visit (Multiple Select)",
            options=["Flexible"] + available_cities,
            default=["Mumbai"]
        )

        hotel_category = st.selectbox(
            "3. Lodging Luxury Class Budget",
            options=["Flexible", "cheapest", "budget", "luxurious"],
            index=2 # budget default
        )

    with col2:
        attraction_interest = st.selectbox(
            "4. Tourist Attraction Interest Type",
            options=["Flexible"] + available_attractions,
            index=0 # Flexible default
        )

        trip_days = st.selectbox(
            "5. Number of Days Duration limit",
            options=["Flexible"] + list(range(1, 15)),
            index=5 # 5 days standard default
        )

        date_range_selection = st.date_input(
            "6. Select Target Travel Departure Date Range (Calendar)",
            value=[date(2026, 6, 1), date(2026, 6, 6)]
        )

    st.markdown("---")
    
    if st.button("⛓️ Map Constraints & Build Structured Itinerary", type="primary"):
        start_date_str = "2026-06-01"
        formatted_dates = "2026-06-01 to 2026-06-06"
        
        if isinstance(date_range_selection, (list, tuple)) and len(date_range_selection) == 2:
            formatted_dates = " to ".join([d.strftime("%Y-%m-%d") for d in date_range_selection])
            start_date_str = date_range_selection[0].strftime("%Y-%m-%d")
        elif isinstance(date_range_selection, date):
            start_date_str = date_range_selection.strftime("%Y-%m-%d")
            formatted_dates = start_date_str
            
        # Build user inputs payload structured like resolve_and_save_state expected
        payload = {
            "origin": origin_input,
            "cities": dest_cities if len(dest_cities) > 0 else "Flexible",
            "days": trip_days,
            "hotel_types": hotel_category,
            "attractions": [attraction_interest] if attraction_interest != "Flexible" else []
        }
        
        with st.spinner("Resolving constraint domains & propagating matrices..."):
            status_msg = tools.resolve_and_save_state(payload, date_range=formatted_dates)
            
            # Fetch resolved parameters to validate m > n
            resolved_origin = tools.global_trip_state.get('origin', origin_input)
            resolved_cities = tools.global_trip_state.get('cities', dest_cities)
            resolved_category = tools.global_trip_state.get('hotel_types', hotel_category)
            try:
                resolved_days = int(tools.global_trip_state.get('days', 5))
            except Exception:
                resolved_days = 5
                
            n = resolved_days
            m = len(resolved_cities)
            
            if m > n:
                st.error(f"Tour not possible in {n} days, instead check schedule for {m} days, or reduce no of destination or increase no of days.")
            else:
                st.toast(f"⚡ Constraints updated in state database: {status_msg}")
                
                # Now run full packaging itinerary matching tools.py logic
                res_itinerary = tools.run_full_itinerary_generation(tools.df_flights, tools.df_hotels)
                
                if isinstance(res_itinerary, str) or ("error" in res_itinerary and res_itinerary["error"]):
                    st.error("Routing resolution error: " + (res_itinerary if isinstance(res_itinerary, str) else res_itinerary.get("message", "Impossible route mapping.")))
                else:
                    st.success("✅ Itinerary calculations completed successfully!")
                    
                    # Display the complete beautiful plan details matching AI layout
                    itinerary_md = tools.build_itinerary_markdown_report_from_state(
                        res_itinerary, resolved_origin, resolved_cities, formatted_dates, resolved_category
                    )
                    st.markdown(itinerary_md)
                    
                    st.markdown("---")
                    
                    # Display Summary Report
                    summary = res_itinerary.get("summary", {})
                    
                    # Use bento visual grids
                    sc1, sc2, sc3, sc4 = st.columns(4)
                    sc1.metric("Flight Expense Log", f"₹{summary.get('total_flight', 0):,}")
                    sc2.metric("Hotels & Lodging", f"₹{summary.get('total_hotel', 0):,}")
                    sc3.metric("Daily Buffer Expense", f"₹{summary.get('total_misc', 0):,}")
                    sc4.metric("Grand Total Cost", f"₹{summary.get('grand_total', 0):,}")
                    
                    # Show itinerary tabular output
                    st.subheader("📅 Solved Day-by-Day Comprehensive Cost Schedule")
                    
                    rows = tools.build_cost_breakdown_table(
                        res_itinerary.get("itinerary", []),
                        res_itinerary.get("flight_legs", []),
                        res_itinerary.get("itinerary", []), # hotel_details same as itinerary structure in tools.py
                        start_date_str
                    )
                    
                    # Render beautifully as a table
                    st.table(rows)
                    
                    # Print warning if there are no direct flights
                    no_direct_warnings = []
                    flight_legs = res_itinerary.get("flight_legs", [])
                    for leg in flight_legs:
                        if not leg.get("is_direct", True):
                            start_c, end_c = leg["leg"].split("->")
                            no_direct_warnings.append(f"⚠️ Note: There are no direct flights between {start_c} and {end_c}. Showing connecting flight route.")
                    
                    for warn in no_direct_warnings:
                        st.warning(warn)
                        
                    # Flight Summary Table listing flight no, airline, from, to, cost
                    st.subheader("✈️ Selected Flights Summary Table")
                    flight_rows = []
                    for leg in flight_legs:
                        for segment in leg.get("segments", []):
                            flight_rows.append({
                                "Flight No": segment.get("flight_id"),
                                "Airline": segment.get("airline"),
                                "From": segment.get("from"),
                                "To": segment.get("to"),
                                "Cost": f"₹{segment.get('price'):,}"
                            })
                    if flight_rows:
                        st.table(flight_rows)
                    else:
                        st.info("No flight segment details available.")
                        
                    # Decision logic reasons
                    st.subheader("💡 Selection Intelligence & Decision Logic")
                    st.markdown("""
                    - **Flight Routing Selection**: 
                      - Cheaper and direct flight paths were prioritized.
                      - If direct flights do not exist, a custom BFS (Breadth-First Search) routing algorithm traversed alternative paths (e.g., through Kolkata) to resolve the absolute cheapest segment-by-segment chain of connections seamlessly.
                    - **Hotel Selection**: 
                      - Hotels of the requested class (e.g. Budget, Cheapest, or Luxury) with the highest verified rating scores (stars) were picked.
                    """)
