# api.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from howfairis import Repo, Compliance

app = FastAPI(
    title="HowFAIRis API",
    description="API to analyze GitHub/GitLab repositories for FAIR compliance",
    version="1.0.0"
)

class RepositoryRequest(BaseModel):
    url: str
    branch: str = "main"

class ComplianceResponse(BaseModel):
    repository: bool
    license: bool
    registry: bool
    citation: bool
    checklist: bool
    score: int
    url: str

@app.post("/check", response_model=ComplianceResponse)
async def check_repository(request: RepositoryRequest):
    try:
        repo = Repo(request.url, branch=request.branch)
        compliance = Compliance(repo)
        
        return {
            "repository": compliance.repository,
            "license": compliance.license,
            "registry": compliance.registry,
            "citation": compliance.citation,
            "checklist": compliance.checklist,
            "score": compliance.get_compliance_score(),
            "url": request.url
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/")
async def root():
    return {
        "message": "Welcome to HowFAIRis API",
        "docs": "/docs",
        "openapi": "/openapi.json"
    }