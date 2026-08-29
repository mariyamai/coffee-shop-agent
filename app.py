from fastapi import FastAPI

app = FastAPI(title="Coffee Shop AI Manager")

@app.get("/")
def home():
    return {
        "message": "☕ Coffee Shop AI Manager is running!"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }
