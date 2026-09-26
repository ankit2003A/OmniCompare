from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.api.images import router as images_router
from app.config import get_settings

app = FastAPI(title="OmniCompare API", version="0.1.0",
              description="AI-powered cross-marketplace product comparison (demo data).")
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_origin_list,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(router)
app.include_router(images_router)


@app.get("/health")
def health():
    return {"status": "ok", "data": "demo", "delivery": "seeded"}
