from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from pydantic import BaseModel
from datetime import datetime

from .database import get_db
from .tax_loss_harvesting import (
    TaxLossHarvestingEngine, 
    TaxLotMethod
)

router = APIRouter(prefix="/tax", tags=["tax"])


class TaxLotResponse(BaseModel):
    """Tax lot response model"""
    symbol: str
    purchase_date: datetime
    quantity: float
    cost_basis: float
    current_price: float
    market_value: float
    unrealized_gain_loss: float
    holding_period_days: int
    is_long_term: bool
    cost_per_share: float
    unrealized_gain_loss_percent: float


class TaxLossHarvestingCandidateResponse(BaseModel):
    """Tax-loss harvesting candidate response model"""
    symbol: str
    total_unrealized_loss: float
    potential_tax_savings: float
    replacement_candidates: List[str]
    last_sale_date: Optional[datetime] = None
    wash_sale_period_active: bool = False
    num_tax_lots: int = 0


class TaxLossHarvestingRecommendationResponse(BaseModel):
    """Tax-loss harvesting recommendation response model"""
    symbol: str
    estimated_tax_savings: float
    replacement_security: Optional[str] = None
    reasoning: str
    urgency: str
    lots_to_sell_count: int
    total_quantity_to_sell: float
    total_loss_to_realize: float


class TaxLossSummaryResponse(BaseModel):
    """Tax loss summary response model"""
    total_unrealized_losses: float
    total_potential_tax_savings: float
    num_candidates: int
    num_recommendations: int
    wash_sale_blocked: int
    candidates: List[Dict]
    recommendations: List[Dict]


class ExecuteTaxHarvestingRequest(BaseModel):
    """Request to execute tax-loss harvesting"""
    symbol: str
    method: str = "hifo"  # fifo, lifo, hifo, specific_id
    execute_replacement: bool = True
    replacement_symbol: Optional[str] = None


@router.get("/lots/{user_id}", response_model=List[TaxLotResponse])
async def get_tax_lots(
    user_id: int,
    symbol: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all tax lots for a user"""
    
    engine = TaxLossHarvestingEngine(db)
    tax_lots = engine.get_tax_lots(user_id, symbol)
    
    return [
        TaxLotResponse(
            symbol=lot.symbol,
            purchase_date=lot.purchase_date,
            quantity=lot.quantity,
            cost_basis=lot.cost_basis,
            current_price=lot.current_price,
            market_value=lot.market_value,
            unrealized_gain_loss=lot.unrealized_gain_loss,
            holding_period_days=lot.holding_period_days,
            is_long_term=lot.is_long_term,
            cost_per_share=lot.cost_per_share,
            unrealized_gain_loss_percent=lot.unrealized_gain_loss_percent
        )
        for lot in tax_lots
    ]


@router.get("/candidates/{user_id}", response_model=List[TaxLossHarvestingCandidateResponse])
async def get_harvesting_candidates(
    user_id: int,
    min_loss_threshold: float = 100.0,
    db: Session = Depends(get_db)
):
    """Get tax-loss harvesting candidates"""
    
    engine = TaxLossHarvestingEngine(db)
    candidates = engine.identify_harvesting_candidates(user_id, min_loss_threshold)
    
    return [
        TaxLossHarvestingCandidateResponse(
            symbol=candidate.symbol,
            total_unrealized_loss=candidate.total_unrealized_loss,
            potential_tax_savings=candidate.potential_tax_savings,
            replacement_candidates=candidate.replacement_candidates,
            last_sale_date=candidate.last_sale_date,
            wash_sale_period_active=candidate.wash_sale_period_active,
            num_tax_lots=len(candidate.tax_lots)
        )
        for candidate in candidates
    ]


@router.get("/recommendations/{user_id}", response_model=List[TaxLossHarvestingRecommendationResponse])
async def get_harvesting_recommendations(
    user_id: int,
    method: str = "hifo",
    db: Session = Depends(get_db)
):
    """Get tax-loss harvesting recommendations"""
    
    try:
        tax_method = TaxLotMethod(method.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tax lot method")
    
    engine = TaxLossHarvestingEngine(db)
    recommendations = engine.generate_harvesting_recommendations(user_id, tax_method)
    
    return [
        TaxLossHarvestingRecommendationResponse(
            symbol=rec.candidate.symbol,
            estimated_tax_savings=rec.estimated_tax_savings,
            replacement_security=rec.replacement_security,
            reasoning=rec.reasoning,
            urgency=rec.urgency,
            lots_to_sell_count=len(rec.lots_to_sell),
            total_quantity_to_sell=sum(lot.quantity for lot in rec.lots_to_sell),
            total_loss_to_realize=sum(lot.unrealized_gain_loss for lot in rec.lots_to_sell)
        )
        for rec in recommendations
    ]


@router.get("/summary/{user_id}", response_model=TaxLossSummaryResponse)
async def get_tax_loss_summary(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get comprehensive tax-loss harvesting summary"""
    
    engine = TaxLossHarvestingEngine(db)
    summary = engine.get_tax_loss_summary(user_id)
    
    return TaxLossSummaryResponse(**summary)


@router.post("/execute/{user_id}")
async def execute_tax_harvesting(
    user_id: int,
    request: ExecuteTaxHarvestingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Execute tax-loss harvesting for a specific security"""
    
    try:
        tax_method = TaxLotMethod(request.method.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tax lot method")
    
    engine = TaxLossHarvestingEngine(db)
    
    try:
        # Get recommendations for the specific symbol
        recommendations = engine.generate_harvesting_recommendations(user_id, tax_method)
        
        # Find recommendation for the requested symbol
        target_recommendation = None
        for rec in recommendations:
            if rec.candidate.symbol == request.symbol:
                target_recommendation = rec
                break
        
        if not target_recommendation:
            raise HTTPException(
                status_code=404, 
                detail=f"No tax-loss harvesting opportunity found for {request.symbol}"
            )
        
        # Override replacement security if specified
        if request.replacement_symbol:
            target_recommendation.replacement_security = request.replacement_symbol
        elif not request.execute_replacement:
            target_recommendation.replacement_security = None
        
        # Execute the recommendation
        result = engine.execute_tax_loss_harvesting(user_id, target_recommendation)
        
        if result["success"]:
            return {
                "message": f"Tax-loss harvesting executed for {request.symbol}",
                "estimated_tax_savings": result["estimated_tax_savings"],
                "sell_orders": result["sell_orders"],
                "buy_orders": result["buy_orders"]
            }
        else:
            raise HTTPException(
                status_code=500, 
                detail=result.get("error", "Failed to execute tax-loss harvesting")
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/methods")
async def get_tax_lot_methods():
    """Get available tax lot methods"""
    
    return {
        "methods": [
            {
                "method": "fifo",
                "name": "First In, First Out",
                "description": "Sell the oldest shares first"
            },
            {
                "method": "lifo",
                "name": "Last In, First Out",
                "description": "Sell the newest shares first"
            },
            {
                "method": "hifo",
                "name": "Highest In, First Out",
                "description": "Sell shares with highest cost basis first"
            },
            {
                "method": "specific_id",
                "name": "Specific Identification",
                "description": "Sell specific lots with largest losses"
            }
        ]
    }


@router.get("/wash-sale-check/{user_id}")
async def check_wash_sale_violations(
    user_id: int,
    symbol: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Check for potential wash sale rule violations"""
    
    engine = TaxLossHarvestingEngine(db)
    candidates = engine.identify_harvesting_candidates(user_id)
    
    if symbol:
        candidates = [c for c in candidates if c.symbol == symbol]
    
    wash_sale_info = []
    
    for candidate in candidates:
        if candidate.wash_sale_period_active:
            days_remaining = 30 - (datetime.now() - candidate.last_sale_date).days
            wash_sale_info.append({
                "symbol": candidate.symbol,
                "last_sale_date": candidate.last_sale_date,
                "days_remaining": days_remaining,
                "blocked_loss_amount": candidate.total_unrealized_loss
            })
    
    return {
        "wash_sale_violations": wash_sale_info,
        "total_blocked_symbols": len(wash_sale_info),
        "total_blocked_losses": sum(info["blocked_loss_amount"] for info in wash_sale_info)
    }


@router.get("/year-end-planning/{user_id}")
async def get_year_end_tax_planning(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get year-end tax planning analysis"""
    
    engine = TaxLossHarvestingEngine(db)
    summary = engine.get_tax_loss_summary(user_id)
    
    # Calculate days until year end
    now = datetime.now()
    year_end = datetime(now.year, 12, 31)
    days_until_year_end = (year_end - now).days
    
    # Get recommendations
    recommendations = engine.generate_harvesting_recommendations(user_id)
    
    # Categorize by urgency
    high_priority = [r for r in recommendations if r.urgency == "high"]
    medium_priority = [r for r in recommendations if r.urgency == "medium"]
    low_priority = [r for r in recommendations if r.urgency == "low"]
    
    return {
        "days_until_year_end": days_until_year_end,
        "total_potential_tax_savings": summary["total_potential_tax_savings"],
        "high_priority_opportunities": len(high_priority),
        "medium_priority_opportunities": len(medium_priority),
        "low_priority_opportunities": len(low_priority),
        "total_harvestable_losses": abs(summary["total_unrealized_losses"]),
        "recommendations_by_priority": {
            "high": [{
                "symbol": r.candidate.symbol,
                "estimated_savings": r.estimated_tax_savings,
                "reasoning": r.reasoning
            } for r in high_priority],
            "medium": [{
                "symbol": r.candidate.symbol,
                "estimated_savings": r.estimated_tax_savings,
                "reasoning": r.reasoning
            } for r in medium_priority],
            "low": [{
                "symbol": r.candidate.symbol,
                "estimated_savings": r.estimated_tax_savings,
                "reasoning": r.reasoning
            } for r in low_priority]
        }
    }


@router.get("/tax-rates")
async def get_current_tax_rates():
    """Get current tax rates for reference"""
    
    return {
        "tax_year": 2024,
        "short_term_capital_gains": {
            "description": "Ordinary income tax rates (held ≤ 1 year)",
            "rates": [
                {"bracket": "10%", "income_range": "$0 - $11,000"},
                {"bracket": "12%", "income_range": "$11,001 - $44,725"},
                {"bracket": "22%", "income_range": "$44,726 - $95,375"},
                {"bracket": "24%", "income_range": "$95,376 - $182,050"},
                {"bracket": "32%", "income_range": "$182,051 - $231,250"},
                {"bracket": "35%", "income_range": "$231,251 - $578,125"},
                {"bracket": "37%", "income_range": "$578,126+"}
            ]
        },
        "long_term_capital_gains": {
            "description": "Special rates for assets held > 1 year",
            "rates": [
                {"bracket": "0%", "income_range": "$0 - $44,625"},
                {"bracket": "15%", "income_range": "$44,626 - $492,300"},
                {"bracket": "20%", "income_range": "$492,301+"}
            ]
        },
        "wash_sale_rule": {
            "description": "Cannot deduct losses if substantially identical security purchased within 30 days",
            "period_days": 30
        }
    }