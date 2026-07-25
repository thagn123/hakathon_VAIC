"""Contracts for the three-role corporate credit request workflow."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class CorporateCreditRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    customer_id: str = Field(min_length=1, max_length=64)
    case_id: Optional[str] = None
    company_name: str = Field(min_length=2, max_length=300)
    tax_id: str = Field(min_length=8, max_length=30)
    legal_type: str = Field(min_length=2, max_length=100)
    representative: str = Field(min_length=2, max_length=200)
    industry: str = Field(min_length=2, max_length=300)
    business_scale: str = Field(min_length=2, max_length=300)
    total_assets_billion_vnd: Decimal = Field(ge=0)
    net_revenue_billion_vnd: Decimal = Field(ge=0)
    net_profit_billion_vnd: Decimal
    debt_to_equity_ratio: Decimal = Field(ge=0)
    cic_debt_classification: str = Field(min_length=1, max_length=100)
    current_debt_billion_vnd: Decimal = Field(ge=0)
    collateral_description: str = Field(min_length=2, max_length=300)
    collateral_value_billion_vnd: Decimal = Field(ge=0)
    casa_avg_balance_billion_vnd: Decimal = Field(ge=0)
    repayment_history: str = Field(min_length=2, max_length=100)
    request_type: Literal["loan", "service", "both"]
    requested_amount_vnd: Decimal = Field(gt=0)
    requested_term_months: Optional[int] = Field(default=None, ge=1, le=360)
    purpose: str = Field(min_length=5, max_length=2000)


class CreditForwardRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    rm_note: str = Field(default="", max_length=2000)


class CreditAppraisalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    recommendation: Literal["recommend", "not_recommended", "needs_more_information"]
    reason: str = Field(min_length=5, max_length=2000)


class CreditDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    decision: Literal["approved", "rejected", "needs_more_information"]
    reason: str = Field(min_length=5, max_length=2000)
