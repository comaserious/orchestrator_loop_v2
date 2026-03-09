from fastapi import APIRouter
from fastapi import FastAPI

class AppRegistry:
    def __init__(self):
        self.routers = []

    def register_router(self, router: APIRouter):
        self.routers.append(router)
        return router
    
    def include_routers(self, app: FastAPI):
        for router in self.routers:
            app.include_router(router)

app_register = AppRegistry()