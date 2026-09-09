from fastapi import FastAPI

app = FastAPI()


@app.get("/")
@app.post("/")
async def hello():
    return "hello"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
