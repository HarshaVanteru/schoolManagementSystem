import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from langchain_core.messages import AIMessage, HumanMessage

from services.sql_agent import create_sql_agent, route_after_query_gen, route_after_execute


class TestSQLAgentGraph(unittest.IsolatedAsyncioTestCase):
    def test_routing_after_query_gen(self):
        # When SQL query is present, route to execute_query
        self.assertEqual(
            route_after_query_gen({"sql_query": "SELECT * FROM students;"}),
            "execute_query",
        )
        # When SQL query is None or empty (conversational), route to explain_result
        self.assertEqual(
            route_after_query_gen({"sql_query": None}),
            "explain_result",
        )
        self.assertEqual(
            route_after_query_gen({}),
            "explain_result",
        )

    def test_routing_after_execute(self):
        # Case 1: Query execution succeeded (no error) -> go directly to explain_result
        state_success = {"error": None, "result_table": {"columns": [], "rows": []}}
        self.assertEqual(route_after_execute(state_success), "explain_result")

        # Case 2: Query failed on 1st attempt (retry_count == 1) -> retry by going to generate_query
        state_fail_1 = {"error": "Unknown column 'foo'", "retry_count": 1}
        self.assertEqual(route_after_execute(state_fail_1), "generate_query")

        # Case 3: Query failed on 2nd attempt (retry_count == 2) -> stop retrying, go to explain_result
        state_fail_2 = {"error": "Unknown column 'foo'", "retry_count": 2}
        self.assertEqual(route_after_execute(state_fail_2), "explain_result")

    @patch("services.sql_agent._run_query_sync")
    @patch("services.sql_agent.get_llm")
    async def test_full_graph_success_on_first_try(self, mock_get_llm, mock_run_query):
        # Mock LLM to return SQL on 1st call, and explanation on 2nd call
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(side_effect=[
            AIMessage(content="SELECT student_id, student_name FROM students;"),
            AIMessage(content="Here are the students from the school database."),
        ])
        mock_get_llm.return_value = mock_llm

        mock_run_query.return_value = {
            "columns": ["student_id", "student_name"],
            "rows": [{"student_id": 1, "student_name": "Alice"}],
            "markdown_table": "| student_id | student_name |\n| --- | --- |\n| 1 | Alice |",
            "row_count": 1,
        }

        agent = create_sql_agent()
        initial_state = {
            "question": "Show all students",
            "messages": [HumanMessage(content="Show all students")],
            "retry_count": 0,
            "error": None,
        }
        result = await agent.ainvoke(initial_state, config={"configurable": {"thread_id": "test-1"}})

        self.assertEqual(result.get("sql_query"), "SELECT student_id, student_name FROM students;")
        self.assertIsNone(result.get("error"))
        self.assertIsNotNone(result.get("result_table"))
        self.assertEqual(result.get("final_explanation"), "Here are the students from the school database.")
        mock_run_query.assert_called_once()
        self.assertEqual(mock_llm.ainvoke.call_count, 2)

    @patch("services.sql_agent._run_query_sync")
    @patch("services.sql_agent.get_llm")
    async def test_full_graph_retry_and_succeed(self, mock_get_llm, mock_run_query):
        # 1st LLM call: generates bad query
        # 2nd LLM call: regenerates good query with error context
        # 3rd LLM call: explains successful result
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(side_effect=[
            AIMessage(content="SELECT invalid_col FROM students;"),
            AIMessage(content="SELECT student_name FROM students;"),
            AIMessage(content="Here is the list of student names."),
        ])
        mock_get_llm.return_value = mock_llm

        # 1st query run raises exception, 2nd succeeds
        mock_run_query.side_effect = [
            Exception("Unknown column 'invalid_col' in 'field list'"),
            {
                "columns": ["student_name"],
                "rows": [{"student_name": "Bob"}],
                "markdown_table": "| student_name |\n| --- |\n| Bob |",
                "row_count": 1,
            },
        ]

        agent = create_sql_agent()
        initial_state = {
            "question": "Show student names",
            "messages": [HumanMessage(content="Show student names")],
            "retry_count": 0,
            "error": None,
        }
        result = await agent.ainvoke(initial_state, config={"configurable": {"thread_id": "test-2"}})

        self.assertEqual(result.get("sql_query"), "SELECT student_name FROM students;")
        self.assertIsNone(result.get("error"))
        self.assertIsNotNone(result.get("result_table"))
        self.assertEqual(result.get("final_explanation"), "Here is the list of student names.")
        self.assertEqual(mock_run_query.call_count, 2)
        self.assertEqual(mock_llm.ainvoke.call_count, 3)

        # Verify that the 2nd LLM prompt contained the error feedback
        second_call_args = mock_llm.ainvoke.call_args_list[1][0][0]
        error_context_in_prompt = any("Unknown column 'invalid_col'" in str(msg.content) for msg in second_call_args)
        self.assertTrue(error_context_in_prompt)

    @patch("services.sql_agent._run_query_sync")
    @patch("services.sql_agent.get_llm")
    async def test_full_graph_retry_and_fail_twice(self, mock_get_llm, mock_run_query):
        # 1st LLM call: generates bad query
        # 2nd LLM call: regenerates another bad query
        # 3rd LLM call: explains what caused the error (explanation node)
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(side_effect=[
            AIMessage(content="SELECT bad1 FROM students;"),
            AIMessage(content="SELECT bad2 FROM students;"),
            AIMessage(content="The column 'bad2' does not exist in the students table."),
        ])
        mock_get_llm.return_value = mock_llm

        # Both executions fail
        mock_run_query.side_effect = [
            Exception("Unknown column 'bad1'"),
            Exception("Unknown column 'bad2'"),
        ]

        agent = create_sql_agent()
        initial_state = {
            "question": "Show something",
            "messages": [HumanMessage(content="Show something")],
            "retry_count": 0,
            "error": None,
        }
        result = await agent.ainvoke(initial_state, config={"configurable": {"thread_id": "test-3"}})

        self.assertIsNotNone(result.get("error"))
        self.assertIn("bad2", result.get("error"))
        self.assertIsNone(result.get("result_table"))
        self.assertEqual(
            result.get("final_explanation"),
            "The column 'bad2' does not exist in the students table.",
        )
        self.assertEqual(mock_run_query.call_count, 2)
        self.assertEqual(mock_llm.ainvoke.call_count, 3)

    @patch("services.sql_agent.get_llm")
    async def test_full_graph_conversational_no_query(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(side_effect=[
            AIMessage(content="NO_QUERY"),
            AIMessage(content="Hello! How can I assist you with school data today?"),
        ])
        mock_get_llm.return_value = mock_llm

        agent = create_sql_agent()
        initial_state = {
            "question": "Hello",
            "messages": [HumanMessage(content="Hello")],
            "retry_count": 0,
            "error": None,
        }
        result = await agent.ainvoke(initial_state, config={"configurable": {"thread_id": "test-4"}})

        self.assertIsNone(result.get("sql_query"))
        self.assertIsNone(result.get("result_table"))
        self.assertIsNone(result.get("error"))
        self.assertEqual(
            result.get("final_explanation"),
            "Hello! How can I assist you with school data today?",
        )
        self.assertEqual(mock_llm.ainvoke.call_count, 2)


if __name__ == "__main__":
    unittest.main()

