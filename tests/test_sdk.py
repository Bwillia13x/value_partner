from sdk.valueinvest_sdk import ValueInvestClient

def test_client_init():
    c = ValueInvestClient(base_url="http://example.com", api_key="token", tier="pro")
    assert c.session.headers["X-API-Tier"] == "pro"