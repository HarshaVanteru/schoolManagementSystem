import re
import asyncio
import logging
from decimal import Decimal
from datetime import date, datetime, time
from typing import TypedDict, Optional, List, Dict, Any, Sequence, Annotated
from sqlalchemy import inspect, text
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_groq import ChatGroq
from core.config import settings
from core.database import engine
from core.prompts import (
    get_sql_generation_prompt,
    get_explain_error_prompt,
    get_explain_result_prompt,
    get_conversational_prompt,
)

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
    # Number of query generation/execution attempts
    retry_count: int


# ---------------------------------------------------------
# Helpers: Schema Introspection & Table Formatting
# ---------------------------------------------------------
# def get_db_schema_string() -> str:
#     """Introspects MySQL database tables and columns to provide schema context."""
#     try:
#         insp = inspect(engine)
#         schema_lines = []
#         for table_name in insp.get_table_names():
#             columns = insp.get_columns(table_name)
#             col_desc = [f"{col['name']} ({col['type']})" for col in columns]
#             schema_lines.append(f"Table: `{table_name}`\n  Columns: {', '.join(col_desc)}")
#         return "\n".join(schema_lines)
#     except Exception as e:
#         logger.error(f"Error fetching DB schema: {e}")
#         return "Schema unavailable"


"""Database schema information provided to the LLM agent."""

DB_INFO = """DATABASE: school_management

TABLE: classes
Description: Stores the classes available in the school.

Columns:
- class_id: INT, Primary Key, Auto Increment
  Unique identifier for each class.
- class_name: VARCHAR(20), NOT NULL
  Name of the class, such as 1st, 2nd, 3rd, ..., 10th.

TABLE: students
Description: Stores student information.

Columns:
- student_id: INT, Primary Key, Auto Increment
  Unique identifier for each student.
- student_name: VARCHAR(100), NOT NULL
  Full name of the student.
- age: INT
  Age of the student.
- gender: VARCHAR(10)
  Gender of the student.
- class_id: INT, Foreign Key -> classes.class_id
  Identifies the class in which the student is enrolled.

TABLE: exams
Description: Stores examinations conducted by the school.

Columns:
- exam_id: INT, Primary Key, Auto Increment
  Unique identifier for each exam.
- exam_name: VARCHAR(50), NOT NULL
  Name of the exam, such as Unit Test 1, Mid-Term Exam, Unit Test 2, or Final Exam.
- exam_date: DATE
  Date on which the exam was conducted.

TABLE: marks
Description: Stores marks obtained by students in different exams.

Columns:
- mark_id: INT, Primary Key, Auto Increment
  Unique identifier for each marks record.
- student_id: INT, NOT NULL, Foreign Key -> students.student_id
  Identifies the student.
- exam_id: INT, NOT NULL, Foreign Key -> exams.exam_id
  Identifies the exam.
- telugu: INT
  Marks obtained in Telugu.
- hindi: INT
  Marks obtained in Hindi.
- english: INT
  Marks obtained in English.
- maths: INT
  Marks obtained in Mathematics.
- science: INT
  Marks obtained in Science.
- social: INT
  Marks obtained in Social Studies.

RELATIONSHIPS:
- One class can have many students (students.class_id -> classes.class_id).
- One student can have many marks records (marks.student_id -> students.student_id).
- One exam can have many marks records (marks.exam_id -> exams.exam_id).
- Each marks record belongs to exactly one student and one exam.

IMPORTANT:
- marks.student_id references students.student_id.
- marks.exam_id references exams.exam_id.
- students.class_id references classes.class_id.
- A marks record represents one student's marks for one exam."""


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
    # schema_info = await asyncio.to_thread(get_db_schema_string)
    system_prompt = get_sql_generation_prompt(DB_INFO)

    llm = get_llm()

    history = list(state.get("messages", []))
    prompt_messages = [SystemMessage(content=system_prompt)] + history

    # If retrying due to an error from the previous query execution, provide the error context
    if state.get("error") and state.get("sql_query"):
        error_feedback = (
            f"The previous query you generated was:\n{state.get('sql_query')}\n\n"
            f"It resulted in the following database error:\n{state.get('error')}\n\n"
            "Please fix the error and generate a corrected MySQL query. Return ONLY the raw SQL query."
        )
        prompt_messages.append(HumanMessage(content=error_feedback))

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


def _clean_cell(val: Any) -> Any:
    """Converts Decimal and date/datetime objects to JSON-serializable types."""
    if isinstance(val, Decimal):
        return float(val) if val % 1 else int(val)
    if isinstance(val, (date, datetime, time)):
        return val.isoformat()
    return val


def _run_query_sync(sql: str) -> TableData:
    """Synchronous helper executed in thread to query MySQL database."""
    with engine.connect() as connection:
        result = connection.execute(text(sql))
        columns = list(result.keys())
        records = [
            {col: _clean_cell(val) for col, val in zip(columns, row)}
            for row in result.fetchall()
        ]
        markdown_table = format_as_markdown_table(columns, records)
        return {
            "columns": columns,
            "rows": records,
            "markdown_table": markdown_table,
            "row_count": len(records),
        }


async def execute_query_node(state: SQLAgentState) -> Dict[str, Any]:
    """Execute Query Node: Runs generated SQL on MySQL database and formats result table."""
    current_retry = state.get("retry_count", 0)
    sql = state.get("sql_query")
    if not sql:
        return {
            "result_table": None,
            "error": "No SQL query generated to execute.",
            "retry_count": current_retry + 1,
        }

    safe_prefixes = ("SELECT", "SHOW", "DESCRIBE", "EXPLAIN", "WITH")
    if not sql.strip().upper().startswith(safe_prefixes):
        return {
            "result_table": None,
            "error": "Only read-only SELECT queries are allowed for safety.",
            "retry_count": current_retry + 1,
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
            "retry_count": current_retry + 1,
        }


async def llm_explain_result_node(state: SQLAgentState) -> Dict[str, Any]:
    """LLM Node: Explains query results or provides conversational reply."""
    question = state.get("question", "")
    sql = state.get("sql_query")
    result_table = state.get("result_table")
    error = state.get("error")

    llm = get_llm()

    if error:
        prompt = get_explain_error_prompt(question=question, sql=sql, error=error)
    elif sql and result_table is not None:
        prompt = get_explain_result_prompt(
            question=question,
            sql=sql,
            row_count=result_table.get("row_count", 0),
            markdown_table=result_table.get("markdown_table", ""),
        )
    else:
        prompt = get_conversational_prompt(question=question)

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


def route_after_execute(state: SQLAgentState) -> str:
    """Decide whether to retry query generation on error (up to 1 retry) or proceed to explanation."""
    if state.get("error"):
        if state.get("retry_count", 0) <= 1:
            return "generate_query"
        return "explain_result"
    return "explain_result"


# ---------------------------------------------------------
# Build StateGraph with InMemory Checkpointer
# ---------------------------------------------------------
def create_sql_agent():
    """Builds and compiles the SQL Agent graph with InMemory Checkpointer."""
    workflow = StateGraph(SQLAgentState)

    workflow.add_node("generate_query", llm_generate_query_node)
    workflow.add_node("execute_query", execute_query_node)
    workflow.add_node("explain_result", llm_explain_result_node)

    workflow.add_edge(START, "generate_query")
    workflow.add_conditional_edges(
        "generate_query",
        route_after_query_gen,
        {
            "execute_query": "execute_query",
            "explain_result": "explain_result",
        },
    )
    workflow.add_conditional_edges(
        "execute_query",
        route_after_execute,
        {
            "generate_query": "generate_query",
            "explain_result": "explain_result",
        },
    )
    workflow.add_edge("explain_result", END)

    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)


sql_agent = create_sql_agent()
