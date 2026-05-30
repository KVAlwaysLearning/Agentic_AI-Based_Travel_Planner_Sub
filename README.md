# Agentic_AI-Based_Travel_Planner

The **Agentic_AI-Based_Travel_Planner** is an intelligent, agentic travel planning assistant that streamlines multi-city travel. By leveraging **LangChain** for autonomous reasoning and **Streamlit** for a responsive user interface, it transforms raw travel preferences into optimized, cost-effective, and weather-aware itineraries.

## 🚀 Key Features

* **Autonomous AI Agent**: Uses a Llama-3.1 powered agent to reason through complex multi-city constraints, ensuring logical sequencing of flights and hotels.
* **Intelligent Constraint Engine**: Automatically resolves user queries, performing sanity checks to ensure itineraries are feasible (e.g., matching the number of cities to trip duration).
* **Real-Time Data Integration**: Features live weather lookup via Open-Meteo and simulated flight/hotel booking engines to provide realistic costs and scheduling.
* **Full Observability**: Includes a custom **AgentTracerCallbackHandler** that streams the agent's internal thought process directly to the UI, offering transparency during the planning phase.
* **Dynamic Cost Visualization**: Generates professional, Markdown-formatted expense logs, budget breakdowns, and daily itineraries.

## 🏗️ Project Architecture

The project is structured into three main modules:

1. **`agent.py`**: The "Brain." Configures the LangChain `AgentExecutor`, defines system instructions for the AI, and manages the callback handlers for real-time UI logging.
2. **`tools.py`**: The "Engine." Contains the core logic for data management, SQLite interactions, weather services, and the constraint solver (BFS routing).
3. **`app.py`**: The "Interface." A Streamlit dashboard providing two modes: a free-form NLP planner for casual users and a rigorous Constraint Control Panel for power users.

## 🛠️ Tech Stack

* **Core**: Python 3.x
* **AI/Agentic Framework**: LangChain, LangGraph (or `langchain_classic`)
* **LLM Integration**: Groq (Llama-3.1-8b-instant)
* **UI Framework**: Streamlit
* **Data/State**: Pandas, SQLite, JSON
* **APIs**: Open-Meteo

## ⚡ How to Run

1. **Clone the repository**:
```bash
git clone https://github.com/your-username/indica-odyssey-planner.git

```


2. **Install dependencies**:
```bash
pip install -r requirements.txt

```


3. **Set environment variables**: Create a `.env` file and add your Groq API key:
```
GROQ_API_KEY=your_api_key_here

```


4. **Run the application**:
```bash
streamlit run app.py

```



## 📈 Decision Logic

The planner uses a **Breadth-First Search (BFS)** algorithm to traverse flight paths when direct routes are unavailable, ensuring the lowest possible cost. Hotel recommendations are dynamically weighted based on the user's selected luxury tier and verified star ratings.

---

*Developed as an Agentic AI Capstone Project.*
