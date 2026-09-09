from fastapi import FastAPI, Response

app = FastAPI()


@app.get("/")
@app.post("/")
async def hello():
    return Response(content="hello", media_type="text/plain")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
