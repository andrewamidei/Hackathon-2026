from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from game_api import DJ

app = FastAPI(title="QuizGame API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(DJ.router)

# To add a new game:
#   1. Create src/game_api/your_game.py with a router = APIRouter(prefix="/your_game")
#   2. Import it here and call app.include_router(your_game.router)
