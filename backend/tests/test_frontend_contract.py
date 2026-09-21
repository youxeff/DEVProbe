"""The detail route also handles closed PRs independently of the open PR list."""


def test_closed_pull_detail(client, response, github_mock, pull_data):
    pull_data["state"] = "closed"
    github_mock(response(pull_data))
    result = client.post("/pull-requests/12", json={"repo_url": "https://github.com/owner/repo"})
    assert result.status_code == 200
    assert result.json()["state"] == "closed"
