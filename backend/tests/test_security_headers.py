def test_security_headers_present(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200

    headers = response.headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "same-origin" in headers.get("Cross-Origin-Opener-Policy", "")
    assert "camera=()" in headers.get("Permissions-Policy", "")

    csp = headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    assert "script-src 'self'" in csp
    assert "unsafe-inline" not in csp
    assert "frame-ancestors 'none'" in csp


def test_hsts_only_over_https(client) -> None:
    response = client.get("/health")
    assert "Strict-Transport-Security" not in response.headers
