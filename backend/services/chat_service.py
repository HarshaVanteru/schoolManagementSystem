import json
import uuid
import logging
from typing import Optional, AsyncGenerator
from langchain_core.messages import HumanMessage, AIMessageChunk
from services.sql_agent import sql_agent
from schemas.chat import ChatResponse, TableDataSchema

logger = logging.getLogger(__name__)


def _format_sse(event: str, data: dict) -> str:
    """Formats an event and dictionary into a standard SSE string."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


class ChatService:
    """Service to handle chat interactions via LangGraph SQL Agent."""

    async def stream_chat(
        self, message: str, session_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Streams LangGraph SQL Agent execution events and LLM tokens via SSE."""
        active_session_id = session_id or str(uuid.uuid4())
        config = {"configurable": {"thread_id": active_session_id}}

        initial_state = {
            "question": message,
            "messages": [HumanMessage(content=message)],
        }

        sql_query = None
        result_table = None
        accumulated_explanation = ""

        try:
            # Emit session initialization event
            yield _format_sse("session", {
                "type": "session",
                "session_id": active_session_id,
            })

            # Emit initial status
            yield _format_sse("status", {
                "type": "status",
                "stage": "generating_query",
                "message": "Analyzing question and preparing query...",
            })

            async for mode, chunk in sql_agent.astream(
                initial_state,
                config=config,
                stream_mode=["updates", "messages"],
            ):
                if mode == "messages":
                    msg_chunk, metadata = chunk
                    # Stream tokens only from the final explanation node
                    if (
                        metadata.get("langgraph_node") == "explain_result"
                        and isinstance(msg_chunk, AIMessageChunk)
                    ):
                        token = msg_chunk.content if hasattr(msg_chunk, "content") else str(msg_chunk)
                        if token:
                            accumulated_explanation += token
                            yield _format_sse("token", {
                                "type": "token",
                                "content": token,
                            })

                elif mode == "updates":
                    for node_name, update in chunk.items():
                        if node_name == "generate_query":
                            sql_query = update.get("sql_query")
                            if sql_query:
                                yield _format_sse("sql", {
                                    "type": "sql",
                                    "sql_query": sql_query,
                                })
                                yield _format_sse("status", {
                                    "type": "status",
                                    "stage": "executing_query",
                                    "message": "Executing query on database...",
                                })
                            else:
                                yield _format_sse("status", {
                                    "type": "status",
                                    "stage": "explaining",
                                    "message": "Composing response...",
                                })

                        elif node_name == "execute_query":
                            result_table = update.get("result_table")
                            error_msg = update.get("error")
                            yield _format_sse("table", {
                                "type": "table",
                                "result_table": result_table,
                                "error": error_msg,
                            })
                            yield _format_sse("status", {
                                "type": "status",
                                "stage": "explaining",
                                "message": "Generating natural language explanation...",
                            })

                        elif node_name == "explain_result":
                            final_expl = update.get("final_explanation")
                            if final_expl:
                                accumulated_explanation = final_expl

            # Emit final aggregate event
            yield _format_sse("done", {
                "type": "done",
                "session_id": active_session_id,
                "sql_query": sql_query,
                "result_table": result_table,
                "response": accumulated_explanation or "No explanation generated.",
            })

        except Exception as e:
            logger.error(f"Error in stream_chat: {e}", exc_info=True)
            yield _format_sse("error", {
                "type": "error",
                "error": str(e),
            })

    async def process_chat(self, message: str, session_id: Optional[str] = None) -> ChatResponse:
        """Invokes the LangGraph SQL Agent with in-memory checkpointer."""
        active_session_id = session_id or str(uuid.uuid4())
        config = {"configurable": {"thread_id": active_session_id}}

        initial_state = {
            "question": message,
            "messages": [HumanMessage(content=message)],
        }

        # Run the agent through LangGraph
        result_state = await sql_agent.ainvoke(initial_state, config=config)

        explanation = result_state.get("final_explanation") or "No explanation generated."
        sql_query = result_state.get("sql_query")
        raw_table = result_state.get("result_table")

        table_schema = None
        if raw_table:
            table_schema = TableDataSchema(
                columns=raw_table.get("columns", []),
                rows=raw_table.get("rows", []),
                markdown_table=raw_table.get("markdown_table", ""),
                row_count=raw_table.get("row_count", 0),
            )

        return ChatResponse(
            response=explanation,
            session_id=active_session_id,
            sql_query=sql_query,
            result_table=table_schema,
        )


chat_service = ChatService()
