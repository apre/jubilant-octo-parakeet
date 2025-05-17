run:
    uvicorn app.main:app --reload

dev:
    fastapi dev app/main.py


test:
    pytest

cov:
    pytest tests/test_github_fetcher_aioresponses.py --cov=app --cov-report=html
