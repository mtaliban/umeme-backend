"""Mipangilio ya pamoja ya majaribio."""

import asyncio

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Motor client ni ya module moja — majaribio yote yatumie loop moja."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    asyncio.set_event_loop(None)
    loop.close()
