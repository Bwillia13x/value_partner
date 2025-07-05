from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from .database import get_db, User
from .auth_routes import get_current_user
from .reporting import PortfolioReporting
from pydantic import BaseModel

router = APIRouter(prefix="/reporting", tags=["reporting"])


class ReportSummaryResponse(BaseModel):
    """Response model for report summary"""
    user_info: dict
    portfolio_summary: dict
    performance_metrics: Optional[dict]
    asset_allocation: dict
    top_holdings: list
    recent_transactions: list
    optimization_suggestions: list
    generated_at: datetime


@router.get("/summary/{user_id}", response_model=ReportSummaryResponse)
async def get_report_summary(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive report summary data"""
    
    try:
        if user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        reporting = PortfolioReporting(db)
        if user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        report_data = reporting.generate_comprehensive_report(user_id)
        
        return ReportSummaryResponse(
            user_info=report_data.user_info,
            portfolio_summary=report_data.portfolio_summary,
            performance_metrics=report_data.performance_metrics.__dict__ if report_data.performance_metrics else None,
            asset_allocation=report_data.asset_allocation,
            top_holdings=report_data.top_holdings,
            recent_transactions=report_data.recent_transactions,
            optimization_suggestions=report_data.optimization_suggestions,
            generated_at=report_data.generated_at
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")


@router.get("/pdf/{user_id}")
async def generate_pdf_report(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate and download PDF report"""
    
    try:
        if user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        reporting = PortfolioReporting(db)
        pdf_bytes = reporting.generate_pdf_report(user_id)
        
        # Return PDF as response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=portfolio_report_{user_id}_{datetime.now().strftime('%Y%m%d')}.pdf"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")


@router.get("/chart/{user_id}")
async def generate_chart(
    user_id: int,
    chart_type: str = "performance",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate chart image"""
    
    try:
        if user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        reporting = PortfolioReporting(db)
        chart_base64 = reporting.generate_chart_image(user_id, chart_type)
        
        return {
            "chart_type": chart_type,
            "image_base64": chart_base64,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating chart: {str(e)}")


@router.get("/templates")
async def get_report_templates():
    """Get available report templates"""
    
    templates = [
        {
            "name": "comprehensive",
            "display_name": "Comprehensive Report",
            "description": "Full portfolio analysis with performance metrics, allocation, and recommendations",
            "sections": [
                "Portfolio Summary",
                "Performance Metrics",
                "Asset Allocation",
                "Top Holdings",
                "Recent Transactions",
                "Optimization Suggestions"
            ]
        },
        {
            "name": "performance",
            "display_name": "Performance Report",
            "description": "Focus on returns, risk metrics, and benchmark comparison",
            "sections": [
                "Performance Metrics",
                "Risk Analysis",
                "Benchmark Comparison",
                "Historical Charts"
            ]
        },
        {
            "name": "allocation",
            "display_name": "Asset Allocation Report",
            "description": "Detailed breakdown of portfolio composition and diversification",
            "sections": [
                "Asset Allocation",
                "Sector Analysis",
                "Geographic Distribution",
                "Holdings Details"
            ]
        }
    ]
    
    return {"templates": templates}


@router.get("/schedule/{user_id}")
async def get_report_schedule(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's report scheduling preferences"""
    
    # In a real implementation, this would fetch from a user_preferences table
    # For now, return default scheduling options
    
    return {
        "user_id": user_id,
        "scheduled_reports": [
            {
                "type": "comprehensive",
                "frequency": "monthly",
                "next_generation": "2024-01-01T00:00:00",
                "email_delivery": True
            }
        ],
        "available_frequencies": ["daily", "weekly", "monthly", "quarterly"],
        "delivery_options": ["email", "download", "dashboard"]
    }


@router.post("/schedule/{user_id}")
async def schedule_report(
    user_id: int,
    report_type: str,
    frequency: str,
    delivery_method: str = "email",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Schedule automatic report generation"""
    
    # In a real implementation, this would:
    # 1. Validate user permissions
    # 2. Store schedule in database
    # 3. Set up background job
    
    return {
        "message": "Report scheduled successfully",
        "user_id": user_id,
        "report_type": report_type,
        "frequency": frequency,
        "delivery_method": delivery_method,
        "scheduled_at": datetime.now().isoformat()
    }


@router.get("/history/{user_id}")
async def get_report_history(
    user_id: int,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's report generation history"""
    
    # In a real implementation, this would fetch from a reports_history table
    # For now, return mock data
    
    return {
        "user_id": user_id,
        "reports": [
            {
                "id": 1,
                "type": "comprehensive",
                "generated_at": "2024-01-15T10:30:00",
                "status": "completed",
                "download_url": f"/reporting/pdf/{user_id}",
                "file_size": "245 KB"
            },
            {
                "id": 2,
                "type": "performance",
                "generated_at": "2024-01-01T00:00:00",
                "status": "completed",
                "download_url": f"/reporting/pdf/{user_id}",
                "file_size": "180 KB"
            }
        ],
        "total_count": 2
    }