from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., description="Message from the user", min_length=1)
    session_id: Optional[str] = Field(None, description="Optional conversation session ID")


class TableDataSchema(BaseModel):
    columns: List[str] = Field(default_factory=list, description="Column names")
    rows: List[Dict[str, Any]] = Field(default_factory=list, description="Row records")
    markdown_table: str = Field("", description="Pre-formatted markdown table")
    row_count: int = Field(0, description="Total number of rows returned")


class ChatResponse(BaseModel):
    response: str = Field(..., description="LLM final explanation or reply")
    session_id: Optional[str] = Field(None, description="Conversation session ID")
    sql_query: Optional[str] = Field(None, description="Generated SQL query if applicable")
    result_table: Optional[TableDataSchema] = Field(None, description="Structured query result table data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC timestamp of the response")
