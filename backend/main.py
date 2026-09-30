 
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.chat import router as chat_router

app = FastAPI(
    title="School Management AI Backend",
    description="FastAPI service with LangGraph agent workflow for school management",
    version="1.0.0",
)

# Enable CORS for local development and frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(chat_router)


@app.get("/", tags=["General"])
async def root():
    return {
        "message": "Welcome to School Management AI API",
        "docs_url": "/docs",
        "status": "online",
    }


 


 
