from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Optional
from app.services.openai_service import OpenAIService
from app.config import Settings, get_settings
from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI app
app = FastAPI(
    title="Competitor Analysis API",
    description="API for analyzing competitors and their loyalty programs using AI",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define input schema
class CompetitorAnalysisRequest(BaseModel):
    company_name: str
    industry: Optional[str] = None
    include_loyalty_program: bool = True

class ErrorResponse(BaseModel):
    detail: str

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}

@app.post("/api/v1/competitor-analysis",
    response_model=Dict,
    responses={
        200: {"description": "Successful analysis"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    })
async def competitor_analysis(
    request: CompetitorAnalysisRequest,
    settings: Settings = Depends(get_settings)
):
    try:
        openai_service = OpenAIService(settings.openai_api_key)
        
        # Step 1: Identify competitors
        competitors_prompt = (
            f"Identify the main competitors of {request.company_name}" +
            (f" in the {request.industry} industry" if request.industry else "") +
            ". For each competitor, describe:\n" +
            "1. Market positioning\n" +
            "2. Target audience\n" +
            "3. Key differentiators\n" +
            ("4. Loyalty program details (benefits and mechanics)\n" if request.include_loyalty_program else "")
        )
        
        competitors_analysis = await openai_service.get_analysis(competitors_prompt)

        # Step 2: Analyze company's positioning
        positioning_prompt = (
            f"Based on the analysis of {request.company_name}'s competitors:\n\n{competitors_analysis}\n\n"
            f"Provide a detailed analysis of where {request.company_name} fits in the market, including:\n"
            "1. Market positioning strengths\n"
            "2. Potential weaknesses\n"
            "3. Market opportunities\n" +
            ("4. Recommendations for loyalty program development or improvement\n" if request.include_loyalty_program else "")
        )
        
        company_positioning = await openai_service.get_analysis(positioning_prompt)

        # Combine results
        result = {
            "company_name": request.company_name,
            "industry": request.industry,
            "competitors_analysis": competitors_analysis,
            "company_positioning": company_positioning,
            "analysis_includes_loyalty": request.include_loyalty_program
        }
        
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
