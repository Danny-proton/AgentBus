import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_session_creation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/session", json={})
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "cwd" in data

@pytest.mark.asyncio
async def test_chat_flow_mock():
    # Helper to create session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/session", json={})
        session_id = resp.json()["session_id"]
        
        # Test Chat (Requires Mocking LLM usually, but here we test the endpoint response structure)
        # Note: Without mocking OpenAI, this might fail or try to hit API. 
        # For this test, we assume we might hit an error or need mock.
        # But we can test the Bash injection which DOES bypass LLM!
        
        # Test Bash Mode Injection
        chat_payload = {
            "message": "! echo integration_test",
            "session_id": session_id
        }
        
        # SSE testing is tricky with simple httpx, usually requires streaming read.
        # We will just check if we get a successful initiatian of stream 
        # or use a library that handles SSE, but here we just check the status code for now.
        async with ac.stream("POST", "/api/chat", json=chat_payload) as response:
            assert response.status_code == 200
            # Read first chunk
            async for chunk in response.aiter_text():
                # We expect "tool_start: bash" or output
                if "stdout: integration_test" in chunk:
                    break
