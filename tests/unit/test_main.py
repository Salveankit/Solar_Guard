from __future__ import annotations

from fastapi.middleware.cors import CORSMiddleware

from app.main import create_app


def test_api_registers_cors_for_frontend_origins() -> None:
    app = create_app()

    cors_layers = [
        layer for layer in app.user_middleware if layer.cls is CORSMiddleware
    ]

    assert cors_layers, "CORSMiddleware must be configured for the frontend"
    assert "http://localhost:5173" in cors_layers[0].kwargs["allow_origins"]
