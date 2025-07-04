from services.app.copilot import CopilotRetriever

def test_copilot_query():
    cop = CopilotRetriever()
    res = cop.query("What is the purpose of Information Security Policy?", k=2)
    assert len(res) >= 1