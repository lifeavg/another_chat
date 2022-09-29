import uvicorn
from fastapi import FastAPI

from chat import router as chat_router

app = FastAPI()
app.include_router(chat_router.router)


# if __name__ == '__main__':
#     uvicorn.run("main:app", host='127.0.0.1', port=8005,
#                 log_level="debug", reload=True)
#     print("running")
