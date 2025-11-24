# main.py
from fastapi import FastAPI
from app.routes import router

app = FastAPI(
    title="ABAP Performance Analyzer (Final Format)",
    version="1.0.0"
)

# Include router with /remediate and /remediate-array
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
