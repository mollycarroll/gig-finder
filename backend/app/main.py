from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import saved, search

app = FastAPI(title="Gig Finder API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(search.router)
app.include_router(saved.router)
