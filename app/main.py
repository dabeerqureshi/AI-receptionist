from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
import os
from dotenv import load_dotenv
from app.db.database import engine, Base
from app.api.routes import router

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="AI Receptionist Booking API",
    description="Multi-tenant appointment booking system for clinics - Vapi compatible",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API Key configuration - Add your clinic keys here
API_KEYS = {
    os.getenv("CLINIC_1_KEY", "demo-clinic-key-123"): 1,
    os.getenv("CLINIC_2_KEY", "clinic-key-456"): 2,
    os.getenv("CLINIC_3_KEY", "clinic-key-789"): 3,
}


# Multi-tenant API Key Validation Middleware
@app.middleware("http")
async def validate_api_key(request: Request, call_next):
    # Skip public endpoints
    public_paths = ["/", "/health", "/docs", "/openapi.json", "/redoc"]
    if request.url.path in public_paths or request.url.path.startswith("/docs"):
        return await call_next(request)

    # Get API Key from header
    api_key = request.headers.get("X-API-Key")
    
    if not api_key or api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")

    # Get authorized tenant id for this API key
    authorized_tenant_id = f"clinic_{API_KEYS[api_key]}"
    
    # ✅ STRICT VALIDATION: BOTH API KEY AND TENANT MUST MATCH
    if request.method == "POST":
        try:
            body = await request.json()
            request_tenant_id = body.get("tenant_id")
            
            if not request_tenant_id:
                raise HTTPException(
                    status_code=400,
                    detail="tenant_id is required in request body"
                )
            
            if request_tenant_id != authorized_tenant_id:
                raise HTTPException(
                    status_code=403,
                    detail=f"ACCESS DENIED: This API Key is only authorized for tenant '{authorized_tenant_id}'"
                )
                
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid request body")

    # ✅ Only if validation passes, attach tenant id
    request.state.tenant_id = authorized_tenant_id
    
    # Reset request body so it can be read again by endpoints
    await request.body()
    
    response = await call_next(request)
    return response


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    tenant_id = getattr(request.state, 'tenant_id', 'public')
    logger.info(f"Tenant:{tenant_id} {request.method} {request.url.path} - {response.status_code} - {process_time:.2f}ms")
    return response


# Include API routes
app.include_router(router)


@app.get("/")
async def root():
    return {
        "message": "AI Receptionist Booking API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)