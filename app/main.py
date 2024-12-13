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
        
        # Step 1: Get list of main competitors
        competitors_list_prompt = (
            f"List the top 5 direct competitors of {request.company_name}" +
            (f" in the {request.industry} industry" if request.industry else "") +
            ". Return ONLY the company names separated by commas, nothing else."
        )
        
        competitors_raw = await openai_service.get_analysis(competitors_list_prompt)
        competitors = [comp.strip() for comp in competitors_raw.split(',')]

        # Step 2: Detailed analysis of each competitor
        detailed_competitors_prompt = (
            f"For each of these competitors of {request.company_name}: {', '.join(competitors)}\n\n"
            "Provide a detailed analysis for EACH competitor with this structure:\n"
            "[Company Name]\n"
            "- Market Position: (high-end, mid-market, value)\n"
            "- Target Demographics: (specific customer segments)\n"
            "- Key Differentiators: (unique selling points)\n"
            "- Market Share: (approximate if known)\n" +
            ("- Loyalty Program:\n  * Program Name\n  * Key Benefits\n  * Member Tiers\n  * Special Features\n" if request.include_loyalty_program else "") +
            "\nRepeat this structure for each competitor."
        )
        
        competitors_analysis = await openai_service.get_analysis(detailed_competitors_prompt)

        # Step 3: Comparative analysis against competitors
        comparative_prompt = (
            f"Based on this competitor analysis:\n\n{competitors_analysis}\n\n"
            f"Provide a comparative analysis of {request.company_name} against these competitors:\n"
            "1. Competitive Advantages:\n"
            "2. Market Gaps/Opportunities:\n"
            "3. Potential Threats:\n"
            "4. Recommended Positioning:\n" +
            ("5. Loyalty Program Recommendations:\n" if request.include_loyalty_program else "")
        )
        
        comparative_analysis = await openai_service.get_analysis(comparative_prompt)

        # Combine results
        result = {
            "company_name": request.company_name,
            "industry": request.industry,
            "main_competitors": competitors,
            "competitor_details": competitors_analysis,
            "comparative_analysis": comparative_analysis,
            "analysis_includes_loyalty": request.include_loyalty_program
        }
        
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
