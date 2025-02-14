# api.py
import os
import logging
import re
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from howfairis import Repo, Checker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check if API keys are configured
github_key = os.getenv('APIKEY_GITHUB', '')
if github_key:
    logger.info("GitHub credentials configured")
else:
    logger.warning("GitHub credentials not configured. Using anonymous access.")

app = FastAPI(
    title="HowFAIRis API",
    description="API to analyze GitHub/GitLab repositories for FAIR compliance",
    version="1.0.0"
)

class RepositoryRequest(BaseModel):
    url: str
    branch: str = "main"

class DetailedResults(BaseModel):
    passed: List[str]
    failed: List[str]

class CategoryResults(BaseModel):
    passed: bool
    details: DetailedResults
    recommendations: List[str]

class RepositoryMetadata(BaseModel):
    name: str
    description: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    language: Optional[str]
    license_name: Optional[str]
    stars: Optional[int]
    forks: Optional[int]

class ComplianceResponse(BaseModel):
    # Basic results (original)
    repository: bool
    license: bool
    registry: bool
    citation: bool
    checklist: bool
    score: int
    url: str
    
    # Detailed results
    repository_details: CategoryResults
    license_details: CategoryResults
    registry_details: CategoryResults
    citation_details: CategoryResults
    checklist_details: CategoryResults
    
    # Repository metadata
    metadata: RepositoryMetadata

def extract_repo_name(url: str) -> str:
    """Extract repository name from GitHub/GitLab URL."""
    # Remove trailing slash if present
    url = url.rstrip('/')
    # Extract the last part of the URL
    return url.split('/')[-1]

@app.post("/check", response_model=ComplianceResponse)
async def check_repository(request: RepositoryRequest):
    try:
        logger.info(f"Checking repository: {request.url}")
        
        # Create a Repo instance
        repo = Repo(request.url, branch=request.branch)
        logger.info(f"Repository API URL: {repo.api}")
        
        # Create a Checker instance
        checker = Checker(repo, is_quiet=False)
        
        # Get compliance results
        logger.info("Starting compliance checks...")
        compliance = checker.check_five_recommendations()
        
        # Get detailed check results
        repository_checks = {
            "has_open_repository": checker.has_open_repository()
        }
        
        license_checks = {
            "has_license": checker.has_license()
        }
        
        registry_checks = {
            "has_pypi_badge": checker.has_pypi_badge(),
            "has_conda_badge": checker.has_conda_badge(),
            "has_bintray_badge": checker.has_bintray_badge(),
            "is_on_github_marketplace": checker.is_on_github_marketplace()
        }
        
        citation_checks = {
            "has_citation_file": checker.has_citation_file(),
            "has_citationcff_file": checker.has_citationcff_file(),
            "has_codemeta_file": checker.has_codemeta_file(),
            "has_zenodo_badge": checker.has_zenodo_badge(),
            "has_zenodo_metadata_file": checker.has_zenodo_metadata_file()
        }
        
        checklist_checks = {
            "has_core_infrastructures_badge": checker.has_core_infrastructures_badge()
        }
        
        # Helper function to create category results
        def create_category_results(checks: Dict[str, bool], recommendations: List[str]) -> CategoryResults:
            passed_checks = [name for name, result in checks.items() if result]
            failed_checks = [name for name, result in checks.items() if not result]
            return CategoryResults(
                passed=any(checks.values()),
                details=DetailedResults(
                    passed=passed_checks,
                    failed=failed_checks
                ),
                recommendations=recommendations
            )
        
        # Get repository metadata
        try:
            repo_api_data = repo.repository_data
            metadata = RepositoryMetadata(
                name=repo_api_data.get("name", extract_repo_name(request.url)),
                description=repo_api_data.get("description"),
                created_at=repo_api_data.get("created_at"),
                updated_at=repo_api_data.get("updated_at"),
                language=repo_api_data.get("language"),
                license_name=repo_api_data.get("license", {}).get("name") if repo_api_data.get("license") else None,
                stars=repo_api_data.get("stargazers_count"),
                forks=repo_api_data.get("forks_count")
            )
        except Exception as e:
            logger.warning(f"Could not fetch repository metadata: {str(e)}")
            # Fallback to basic metadata
            metadata = RepositoryMetadata(
                name=extract_repo_name(request.url),
                description=None,
                created_at=None,
                updated_at=None,
                language=None,
                license_name=None,
                stars=None,
                forks=None
            )
        
        return {
            # Basic results
            "repository": compliance.repository,
            "license": compliance.license,
            "registry": compliance.registry,
            "citation": compliance.citation,
            "checklist": compliance.checklist,
            "score": sum([
                compliance.repository,
                compliance.license,
                compliance.registry,
                compliance.citation,
                compliance.checklist
            ]),
            "url": request.url,
            
            # Detailed results with recommendations
            "repository_details": create_category_results(
                repository_checks,
                ["Make the repository public"] if not compliance.repository else []
            ),
            "license_details": create_category_results(
                license_checks,
                ["Add a LICENSE file"] if not compliance.license else []
            ),
            "registry_details": create_category_results(
                registry_checks,
                ["Add package to PyPI and include a PyPI badge",
                 "Consider adding the package to conda-forge",
                 "List the package on GitHub Marketplace"] if not compliance.registry else []
            ),
            "citation_details": create_category_results(
                citation_checks,
                ["Add a CITATION.cff file",
                 "Add Zenodo integration and badge"] if not compliance.citation else []
            ),
            "checklist_details": create_category_results(
                checklist_checks,
                ["Add a Core Infrastructure Badge"] if not compliance.checklist else []
            ),
            
            # Repository metadata
            "metadata": metadata
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