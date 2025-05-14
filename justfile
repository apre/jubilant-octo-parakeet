run:
    uvicorn app.main:app --reload

dev:
    fastapi dev app/main.py


test:
    pytest