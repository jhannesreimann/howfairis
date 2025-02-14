# api.py
import os
import logging
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from howfairis import Repo, Checker
from howfairis.requesting.get_from_github import get_from_github

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set environment variables for API keys
github_token = os.getenv('GITHUB_TOKEN', '')
github_user = os.getenv('GITHUB_USER', '')

if github_token and github_user:
    # Format: <user>:<token>
    os.environ['APIKEY_GITHUB'] = f"{github_user}:{github_token}"
    logger.info("GitHub credentials configured")
else:
    logger.warning("GitHub credentials not fully configured. Using anonymous access.")

gitlab_token = os.getenv('GITLAB_TOKEN', '')
gitlab_user = os.getenv('GITLAB_USER', '')

if gitlab_token and gitlab_user:
    # Format: <user>:<token>
    os.environ['APIKEY_GITLAB'] = f"{gitlab_user}:{gitlab_token}"
    logger.info("GitLab credentials configured")
else:
    logger.warning("GitLab credentials not fully configured. Using anonymous access.")

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

def get_repository_metadata(repo: Repo) -> RepositoryMetadata:
    """Get repository metadata using the repository's API endpoint."""
    try:
        # Get repository data using howfairis's API request mechanism
        response = get_from_github(repo.api, "api", repo._apikeys)
        
        if response.status_code == 200:
            data = response.json()
            return RepositoryMetadata(
                name=data.get("name", repo.repo),
                description=data.get("description"),
                created_at=data.get("created_at"),
                updated_at=data.get("updated_at"),
                language=data.get("language"),
                license_name=data.get("license", {}).get("name") if data.get("license") else None,
                stars=data.get("stargazers_count"),
                forks=data.get("forks_count")
            )
    except Exception as e:
        logger.warning(f"Could not fetch repository metadata: {str(e)}")
    
    # Fallback to basic metadata
    return RepositoryMetadata(name=repo.repo)

def filter_none(lst: List[Any]) -> List[Any]:
    """Remove None values from a list."""
    return [item for item in lst if item is not None]

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
                recommendations=filter_none(recommendations)
            )
        
        # Get repository metadata
        metadata = get_repository_metadata(repo)
        
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
                ["Make the repository public"] if not checker.has_open_repository() else []
            ),
            "license_details": create_category_results(
                license_checks,
                ["Add a LICENSE file"] if not checker.has_license() else []
            ),
            "registry_details": create_category_results(
                registry_checks,
                [
                    "Add package to PyPI and include a PyPI badge" if not checker.has_pypi_badge() else None,
                    "Add package to conda-forge and include a conda badge" if not checker.has_conda_badge() else None,
                    "List the package on GitHub Marketplace" if not checker.is_on_github_marketplace() else None
                ] + (["Consider removing Bintray badge as Bintray is deprecated"] if checker.has_bintray_badge() else [])
            ),
            "citation_details": create_category_results(
                citation_checks,
                [
                    "Add a CITATION.cff file for software citation" if not checker.has_citationcff_file() else None,
                    "Add a CITATION file" if not checker.has_citation_file() else None,
                    "Add a codemeta.json file" if not checker.has_codemeta_file() else None,
                    "Add Zenodo integration and badge" if not checker.has_zenodo_badge() else None,
                    "Add .zenodo.json metadata file" if not checker.has_zenodo_metadata_file() else None
                ]
            ),
            "checklist_details": create_category_results(
                checklist_checks,
                ["Add a Core Infrastructure Badge"] if not checker.has_core_infrastructures_badge() else []
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