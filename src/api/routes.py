# src/api/routes.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.core.matcher import get_matcher
from typing import List
from src.utils.logger import get_logger

router = APIRouter()
logger = get_logger()

# prevent duplicated import: Initialize matcher once when the module loads
matcher = get_matcher('data/hscode-data.csv')

class SearchQuery(BaseModel):
    query: str

class SearchResult(BaseModel):
    id: str
    code: str
    description: str
    similarity: float

@router.get("/health")
async def health_check():
    return {"status": "healthy"}

@router.post("/search_hscode/", response_model=List[SearchResult])
async def search_hscode(query: SearchQuery):
    try:
        # Log the incoming query
        logger.info(f"Received search query: {query.query}")
        
        # Perform the search
        results = matcher.search(query.query)
        
        # Convert results to dict format
        results_dict = [result.to_dict() for result in results]
        
        # Log the results
        logger.log_search_result(query.query, results_dict)
        
        # Log the number of results found
        logger.info(f"Found {len(results_dict)} results for query: {query.query}")
        
        return results_dict
    except Exception as e:
        # Log the error
        logger.log_error(
            error_type="SearchError",
            error_message=str(e),
            details={"query": query.query}
        )
        logger.error(f"Search failed for query '{query.query}': {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))