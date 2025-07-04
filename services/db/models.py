from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON, Enum, Float

from .base import Base


class FinancialStatement(Base):
    __tablename__ = "financial_statements"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    period_type = Column(Enum("quarterly", "annual", name="period_type"), nullable=False)
    fiscal_period = Column(String, nullable=False)
    statement_type = Column(Enum("IS", "BS", "CF", name="statement_type"), nullable=False)
    data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class KeyMetric(Base):
    __tablename__ = "key_metrics"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    metric_name = Column(String, nullable=False)
    value = Column(Float)
    period = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class IntrinsicValuation(Base):
    __tablename__ = "intrinsic_valuations"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    valuation_type = Column(String, nullable=False)
    base_value = Column(Float)
    bear_value = Column(Float)
    bull_value = Column(Float)
    as_of_date = Column(DateTime)
    inputs = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class QualitativeSignal(Base):
    __tablename__ = "qualitative_signals"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    signal_type = Column(String, nullable=False)
    score = Column(Float)
    data = Column(JSON)
    as_of_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


# -------------------- Special situations --------------------


class SpecialSituation(Base):
    __tablename__ = "special_situations"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    filing_type = Column(String, nullable=False)
    filed_at = Column(DateTime)
    url = Column(String)
    data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)