# api.py
import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from howfairis import Repo, Checker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set environment variables for API keys
github_token = os.getenv('GITHUB_TOKEN', '')
gitlab_token = os.getenv('GITLAB_TOKEN', '')
os.environ['GITHUB_TOKEN'] = github_token
os.environ['GITLAB_TOKEN'] = gitlab_token

logger.info(f"GitHub Token available: {'yes' if github_token else 'no'}")
logger.info(f"GitLab Token available: {'yes' if gitlab_token else 'no'}")

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
        logger.info(f"Checking repository: {request.url}")
        
        # Create a Repo instance
        repo = Repo(request.url, branch=request.branch)
        logger.info(f"Repository API URL: {repo.api}")
        
        # Create a Checker instance
        checker = Checker(repo, is_quiet=False)  # Set is_quiet to False for more output
        
        # Get compliance results
        logger.info("Starting compliance checks...")
        compliance = checker.check_five_recommendations()
        logger.info(f"Compliance results: repository={compliance.repository}, "
                   f"license={compliance.license}, registry={compliance.registry}, "
                   f"citation={compliance.citation}, checklist={compliance.checklist}")
        
        # Calculate score manually by counting True values
        score = sum([
            compliance.repository,
            compliance.license,
            compliance.registry,
            compliance.citation,
            compliance.checklist
        ])
        
        logger.info(f"Returning response: repository={compliance.repository}, "
                   f"license={compliance.license}, registry={compliance.registry}, "
                   f"citation={compliance.citation}, checklist={compliance.checklist}, "
                   f"score={score}, url={request.url}")
        
        return {
            "repository": compliance.repository,
            "license": compliance.license,
            "registry": compliance.registry,
            "citation": compliance.citation,
            "checklist": compliance.checklist,
            "score": score,
            "url": request.url
        }
    except Exception as e:
        logger.error(f"Error checking repository: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/")
async def root():
    return {
        "message": "Welcome to HowFAIRis API",
        "docs": "/docs",
        "openapi": "/openapi.json"
    }