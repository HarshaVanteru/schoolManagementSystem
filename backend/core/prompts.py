"""
System and user prompts for the School Management LangGraph SQL Agent.
"""

from typing import Optional

# ---------------------------------------------------------
# Prompt Templates
# ---------------------------------------------------------
SQL_GENERATION_SYSTEM_TEMPLATE = """You are an expert MySQL database query generator for a School Management System.
Database Schema:
{schema_info}

Instructions:
1. When asked a question that requires school database information (students, marks, classes, exams), generate a valid MySQL SELECT query.
2. Consider the conversation history for follow-up questions (e.g. 'who are their marks', 'show their class', etc.).
3. Return ONLY the raw SQL query. Do NOT include markdown formatting, backticks, comments, or explanations.
4. If the question is purely conversational (e.g. 'hello', 'thank you') or does not require a database query, respond ONLY with: NO_QUERY
5. Ensure valid MySQL syntax and accurate JOIN conditions (e.g., students.class_id = classes.class_id, marks.student_id = students.student_id, marks.exam_id = exams.exam_id).
"""


EXPLAIN_ERROR_TEMPLATE = """The user asked: '{question}'
A SQL query was attempted: `{sql}`
However, an error occurred: {error}

Provide a helpful, polite explanation of the issue and suggest how the user can clarify or rephrase."""


EXPLAIN_RESULT_TEMPLATE = """The user asked: '{question}'
Executed SQL:
`{sql}`

Query Results ({row_count} rows):
{markdown_table}

Instructions:
1. Provide a natural, insightful explanation answering the user's question based on the query results.
2. Highlight key figures, names, marks, or insights.
3. Be professional and concise."""


CONVERSATIONAL_RESPONSE_TEMPLATE = """The user said: '{question}'
Respond politely as the School Management AI Assistant. Mention that you can answer queries about students, classes, exam marks, and academic performance."""


# ---------------------------------------------------------
# Prompt Helper Functions
# ---------------------------------------------------------
def get_sql_generation_prompt(schema_info: str) -> str:
    """Builds the system prompt for SQL generation with the introspected database schema."""
    return SQL_GENERATION_SYSTEM_TEMPLATE.format(schema_info=schema_info)


def get_explain_error_prompt(question: str, sql: Optional[str], error: str) -> str:
    """Builds the explanation prompt when query generation or execution failed."""
    return EXPLAIN_ERROR_TEMPLATE.format(question=question, sql=sql or "N/A", error=error)


def get_explain_result_prompt(
    question: str, sql: str, row_count: int, markdown_table: str
) -> str:
    """Builds the explanation prompt for successful SQL query results."""
    return EXPLAIN_RESULT_TEMPLATE.format(
        question=question,
        sql=sql,
        row_count=row_count,
        markdown_table=markdown_table,
    )


def get_conversational_prompt(question: str) -> str:
    """Builds the fallback conversational greeting/help prompt."""
    return CONVERSATIONAL_RESPONSE_TEMPLATE.format(question=question)
