import re
import asyncio
import logging
from typing import TypedDict, Optional, List, Dict, Any, Sequence, Annotated
from sqlalchemy import inspect, text
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_groq import ChatGroq
from core.config import settings
from core.database import engine

logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# State Definition
# ---------------------------------------------------------
class TableData(TypedDict, total=False):
    columns: List[str]
    rows: List[Dict[str, Any]]
    markdown_table: str
    row_count: int


class SQLAgentState(TypedDict, total=False):
    # Conversation history tracked via checkpointer
    messages: Annotated[Sequence[BaseMessage], add_messages]
    # Current question
    question: str
    # Generated SQL query for the current turn
    sql_query: Optional[str]
    # Formatted table data for the query result
    result_table: Optional[TableData]
    # LLM final natural language explanation
    final_explanation: Optional[str]
    # Error message if query generation or execution failed
    error: Optional[str]


# ---------------------------------------------------------
# Helpers: Schema Introspection & Table Formatting
# ---------------------------------------------------------
def get_db_schema_string() -> str:
    """Introspects MySQL database tables and columns to provide schema context."""
    try:
        insp = inspect(engine)
        schema_lines = []
        for table_name in insp.get_table_names():
            columns = insp.get_columns(table_name)
            col_desc = [f"{col['name']} ({col['type']})" for col in columns]
            schema_lines.append(f"Table: `{table_name}`\n  Columns: {', '.join(col_desc)}")
        return "\n".join(schema_lines)
    except Exception as e:
        logger.error(f"Error fetching DB schema: {e}")
        return "Schema unavailable"


def format_as_markdown_table(columns: List[str], rows: List[Dict[str, Any]]) -> str:
    """Formats list of row dictionaries into a clean GitHub Flavored Markdown table."""
    if not columns or not rows:
        return "No data returned."

    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    data_lines = []
    for row in rows:
        row_values = [str(row.get(col, "")) for col in columns]
        data_lines.append("| " + " | ".join(row_values) + " |")

    return "\n".join([header, separator] + data_lines)


def clean_sql_query(raw_query: str) -> str:
    """Strips markdown code blocks, backticks, and extra whitespace from generated SQL."""
    cleaned = re.sub(r"^```(?:sql)?", "", raw_query.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"```$", "", cleaned.strip())
    # Remove any surrounding single backticks
    cleaned = cleaned.strip("` \n\r\t")
    return cleaned


def get_llm():
    """Initializes ChatGroq instance using settings."""
    return ChatGroq(
        groq_api_key=settings.GROQ_API_KEY,
        model_name=settings.LLM_MODEL or "openai/gpt-oss-120b",
        temperature=0.0,
    )


# ---------------------------------------------------------
# Graph Nodes
# ---------------------------------------------------------
async def llm_generate_query_node(state: SQLAgentState) -> Dict[str, Any]:
    """LLM Node: Generates MySQL query based on schema, user question, and conversation history."""
    schema_info = await asyncio.to_thread(get_db_schema_string)

    system_prompt = f"""You are an expert MySQL database query generator for a School Management System.
Database Schema:
{schema_info}

Instructions:
1. When asked a question that requires school database information (students, marks, classes, exams), generate a valid MySQL SELECT query.
2. Consider the conversation history for follow-up questions (e.g. 'who are their marks', 'show their class', etc.).
3. Return ONLY the raw SQL query. Do NOT include markdown formatting, backticks, comments, or explanations.
4. If the question is purely conversational (e.g. 'hello', 'thank you') or does not require a database query, respond ONLY with: NO_QUERY
5. Ensure valid MySQL syntax and accurate JOIN conditions (e.g., students.class_id = classes.class_id, marks.student_id = students.student_id, marks.exam_id = exams.exam_id).
"""

    llm = get_llm()

    # Build prompt with conversation history so follow-ups work with checkpointer
    history = list(state.get("messages", []))
    prompt_messages = [SystemMessage(content=system_prompt)] + history

    response = await llm.ainvoke(prompt_messages)
    raw_sql = response.content.strip()
    cleaned_sql = clean_sql_query(raw_sql)

    logger.info(f"Generated SQL: {cleaned_sql}")

    if cleaned_sql.upper() == "NO_QUERY" or not cleaned_sql or "SELECT" not in cleaned_sql.upper():
        return {
            "sql_query": None,
            "result_table": None,
            "error": None,
        }

    return {
        "sql_query": cleaned_sql,
        "result_table": None,
        "error": None,
    }


def _run_query_sync(sql: str) -> TableData:
    """Synchronous helper executed in thread to query MySQL database."""
    with engine.connect() as connection:
        result = connection.execute(text(sql))
        columns = list(result.keys())
        records = [dict(zip(columns, row)) for row in result.fetchall()]
        markdown_table = format_as_markdown_table(columns, records)
        return {
            "columns": columns,
            "rows": records,
            "markdown_table": markdown_table,
            "row_count": len(records),
        }


async def execute_query_node(state: SQLAgentState) -> Dict[str, Any]:
    """Execute Query Node: Runs generated SQL on MySQL database and formats result table."""
    sql = state.get("sql_query")
    if not sql:
        return {
            "result_table": None,
            "error": "No SQL query generated to execute.",
        }

    # Safety guard: only allow read-only statements
    safe_prefixes = ("SELECT", "SHOW", "DESCRIBE", "EXPLAIN", "WITH")
    if not sql.strip().upper().startswith(safe_prefixes):
        return {
            "result_table": None,
            "error": "Only read-only SELECT queries are allowed for safety.",
        }

    try:
        result_table = await asyncio.to_thread(_run_query_sync, sql)
        return {
            "result_table": result_table,
            "error": None,
        }
    except Exception as e:
        logger.error(f"SQL execution failed: {e}")
        return {
            "result_table": None,
            "error": f"SQL Execution Error: {str(e)}",
        }


async def llm_explain_result_node(state: SQLAgentState) -> Dict[str, Any]:
    """LLM Node: Explains query results or provides conversational reply."""
    question = state.get("question", "")
    sql = state.get("sql_query")
    result_table = state.get("result_table")
    error = state.get("error")

    llm = get_llm()

    if error:
        prompt = f"""The user asked: '{question}'
A SQL query was attempted: `{sql}`
However, an error occurred: {error}

Provide a helpful, polite explanation of the issue and suggest how the user can clarify or rephrase."""
    elif sql and result_table is not None:
        prompt = f"""The user asked: '{question}'
Executed SQL:
`{sql}`

Query Results ({result_table['row_count']} rows):
{result_table['markdown_table']}

Instructions:
1. Provide a natural, insightful explanation answering the user's question based on the query results.
2. Highlight key figures, names, marks, or insights.
3. Be professional and concise."""
    else:
        # Conversational / general query
        prompt = f"""The user said: '{question}'
Respond politely as the School Management AI Assistant. Mention that you can answer queries about students, classes, exam marks, and academic performance."""

    response = await llm.ainvoke([HumanMessage(content=prompt)])
    final_explanation = response.content.strip()

    return {
        "final_explanation": final_explanation,
        "messages": [AIMessage(content=final_explanation)],
    }


# ---------------------------------------------------------
# Routing Logic
# ---------------------------------------------------------
def route_after_query_gen(state: SQLAgentState) -> str:
    """Decide whether to execute query or go directly to explanation."""
    if state.get("sql_query"):
        return "execute_query"
    return "explain_result"


# ---------------------------------------------------------
# Build StateGraph with InMemory Checkpointer
# ---------------------------------------------------------
def create_sql_agent():
    """Builds and compiles the SQL Agent graph with InMemory Checkpointer."""
    workflow = StateGraph(SQLAgentState)

    # Add Nodes
    workflow.add_node("generate_query", llm_generate_query_node)
    workflow.add_node("execute_query", execute_query_node)
    workflow.add_node("explain_result", llm_explain_result_node)

    # Add Edges
    workflow.add_edge(START, "generate_query")
    workflow.add_conditional_edges(
        "generate_query",
        route_after_query_gen,
        {
            "execute_query": "execute_query",
            "explain_result": "explain_result",
        },
    )
    workflow.add_edge("execute_query", "explain_result")
    workflow.add_edge("explain_result", END)

    # In-memory checkpointer for thread-level state persistence
    checkpointer = MemorySaver()

    return workflow.compile(checkpointer=checkpointer)


# Singleton instance of compiled SQL agent
sql_agent = create_sql_agent()
