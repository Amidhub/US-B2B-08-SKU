from fastapi import FastAPI
from src.api import inventory
from src.database import Base, engine
from src.exceptions import register_exception_handlers

app = FastAPI()

register_exception_handlers(app)

Base.metadata.create_all(bind=engine)

app.include_router(inventory.router)

@app.get("/")
def root():
    return {"message": "B2B Service"}