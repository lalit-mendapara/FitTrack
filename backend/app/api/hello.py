from fastapi import APIRouter

# create the api router instance
router = APIRouter()

@router.get("/hello")
async def sayhello():
    return {"message": "Hello World"}

@router.get("/status")
async def status():
    return {"status": "healthy"}