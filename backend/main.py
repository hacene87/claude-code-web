#!/usr/bin/env python3
"""
Odoo Automation Service - Main Entry Point
==========================================

Run with:
    python main.py

Or with uvicorn:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

import argparse
import logging
import sys

import structlog
import uvicorn

from app.core.config import get_settings


def setup_logging():
    """Configure structured logging."""
    settings = get_settings()

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
            if settings.logging.format == "json"
            else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Set log level
    log_level = getattr(logging, settings.logging.level.upper(), logging.INFO)
    logging.basicConfig(
        format="%(message)s",
        level=log_level,
        stream=sys.stdout,
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Odoo Automation Service"
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Host to bind to (default: from config)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to bind to (default: from config)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to config file"
    )
    args = parser.parse_args()

    # Load configuration
    if args.config:
        from app.core.config import reload_settings
        reload_settings(args.config)

    settings = get_settings()

    # Setup logging
    setup_logging()

    # Get host and port
    host = args.host or settings.api.host
    port = args.port or settings.api.port

    # Import app here to ensure logging is configured first
    from app.api.main import app

    # Run server
    uvicorn.run(
        "app.api.main:app" if args.reload else app,
        host=host,
        port=port,
        reload=args.reload,
        log_level=settings.logging.level.lower(),
    )


if __name__ == "__main__":
    main()
