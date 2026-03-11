"""
SentinelFraud Risk Engine Service
Combines ML score + rule-based engine into final risk score.
Target: <100ms end-to-end response.

Rules engine (additive risk weights):
  Velocity: card >5/h (+30), user >10/h (+20), device >20/h (+40)
  Amount:   >$10k (+25), >$50k (+50), spike 10x avg (+35)
  Geo:      high-risk country (+30), impossible travel (+60), new country (+15)
  Device:   new device (+20)
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.cache import cache_risk_score, get_cached_risk_score
from app.repositories.transaction_repo import TransactionRepository
from app.services.velocity_check import VelocityCheckService
from app.services.ml_model import ml_model_service

logger = logging.getLogger(__name__)

velocity_service = VelocityCheckService()


@dataclass
class RuleResult:
    score: int = 0
    triggers: list[str] = field(default_factory=list)


@dataclass
class RiskResult:
    transaction_id: str = ""
    risk_score: int = 0          # 0-100
    decision: str = "approve"    # approve|review|decline
    ml_score: Optional[float] = None
    rule_score: int = 0
    rule_triggers: list[str] = field(default_factory=list)
    processing_time_ms: float = 0.0
    is_fraud: bool = False


class RiskEngineService:
    """
    Orchestrates all risk checks and returns a composite risk score.
    Designed for async, sub-100ms execution.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.tx_repo = TransactionRepository(db)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def calculate_risk_score(
        self,
        transaction_id: str,
        card_id: str,
        amount: float,
        currency: str,
        country_code: Optional[str],
        ip_address: Optional[str],
        device_fingerprint: Optional[str],
        merchant_category: Optional[str],
        user_id: Optional[str],
        timestamp: Optional[datetime] = None,
    ) -> RiskResult:
        start = time.perf_counter()
        result = RiskResult(transaction_id=transaction_id)

        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        # 1. Velocity checks (Redis)
        vel_result = await velocity_service.check_and_increment(
            card_id=card_id,
            user_id=str(user_id) if user_id else None,
            device_fingerprint=device_fingerprint,
        )
        result.rule_score += vel_result.risk_addition
        result.rule_triggers.extend(vel_result.triggers)

        # 2. Amount rules
        avg_30d = await self.tx_repo.get_avg_amount_30d(card_id)
        amount_result = self._apply_amount_rules(amount, avg_30d)
        result.rule_score += amount_result.score
        result.rule_triggers.extend(amount_result.triggers)

        # 3. Geo rules
        last_tx = await self.tx_repo.get_last_transaction(card_id)
        geo_result = self._apply_geo_rules(
            country_code=country_code,
            last_transaction=last_tx,
            timestamp=timestamp,
        )
        result.rule_score += geo_result.score
        result.rule_triggers.extend(geo_result.triggers)

        # 4. Device rules
        if device_fingerprint and last_tx and last_tx.device_fingerprint != device_fingerprint:
            result.rule_score += 20
            result.rule_triggers.append("new_device(weight=+20)")

        # 5. ML prediction
        time_since_last = 999_999.0
        if last_tx and last_tx.timestamp:
            last_ts = last_tx.timestamp
            if last_ts.tzinfo is None:
                last_ts = last_ts.replace(tzinfo=timezone.utc)
            delta = (timestamp - last_ts).total_seconds()
            time_since_last = max(0.0, delta)

        is_international = bool(
            country_code and country_code not in ["US", "USA"]
        )
        is_new_device = bool(
            device_fingerprint
            and last_tx
            and last_tx.device_fingerprint != device_fingerprint
        )
        is_high_risk = country_code in settings.HIGH_RISK_COUNTRIES if country_code else False

        ml_score = ml_model_service.predict(
            amount=amount,
            timestamp=timestamp,
            avg_amount_30d=avg_30d,
            time_since_last_tx_seconds=time_since_last,
            is_international=is_international,
            is_new_device=is_new_device,
            is_high_risk_country=is_high_risk,
            merchant_category=merchant_category,
            currency=currency,
            card_velocity_1h=vel_result.card_count,
            user_velocity_1h=vel_result.user_count,
        )
        result.ml_score = ml_score

        # 6. Combine scores (weighted average)
        result.risk_score = self._combine_scores(
            rule_score=result.rule_score,
            ml_score=ml_score,
        )

        # 7. Decision
        result.decision = self._make_decision(result.risk_score)
        result.is_fraud = result.risk_score >= settings.RISK_SCORE_FRAUD_THRESHOLD

        result.processing_time_ms = (time.perf_counter() - start) * 1000
        logger.debug(
            "Risk score for %s: %d (%s) in %.2fms",
            transaction_id,
            result.risk_score,
            result.decision,
            result.processing_time_ms,
        )

        # 8. Cache result
        await cache_risk_score(transaction_id, {
            "risk_score": result.risk_score,
            "decision": result.decision,
            "ml_score": result.ml_score,
            "rule_score": result.rule_score,
        })

        return result

    # ------------------------------------------------------------------
    # Rule: Amount
    # ------------------------------------------------------------------
    def _apply_amount_rules(self, amount: float, avg_30d: float) -> RuleResult:
        r = RuleResult()
        if amount >= settings.VERY_HIGH_AMOUNT_THRESHOLD:
            r.score += 50
            r.triggers.append(f"amount_very_high:{amount:.2f}(threshold={settings.VERY_HIGH_AMOUNT_THRESHOLD},weight=+50)")
        elif amount >= settings.HIGH_AMOUNT_THRESHOLD:
            r.score += 25
            r.triggers.append(f"amount_high:{amount:.2f}(threshold={settings.HIGH_AMOUNT_THRESHOLD},weight=+25)")

        if avg_30d > 0 and amount >= avg_30d * settings.AMOUNT_SPIKE_MULTIPLIER:
            r.score += 35
            r.triggers.append(f"amount_spike:{amount:.2f}_vs_avg_{avg_30d:.2f}(x{settings.AMOUNT_SPIKE_MULTIPLIER},weight=+35)")
        return r

    # ------------------------------------------------------------------
    # Rule: Geo
    # ------------------------------------------------------------------
    def _apply_geo_rules(
        self,
        country_code: Optional[str],
        last_transaction,
        timestamp: datetime,
    ) -> RuleResult:
        r = RuleResult()
        if not country_code:
            return r

        # High-risk country
        if country_code in settings.HIGH_RISK_COUNTRIES:
            r.score += 30
            r.triggers.append(f"high_risk_country:{country_code}(weight=+30)")

        if last_transaction:
            last_country = last_transaction.country_code
            last_ts = last_transaction.timestamp

            # New country
            if last_country and last_country != country_code:
                r.score += 15
                r.triggers.append(f"new_country:{last_country}->{country_code}(weight=+15)")

                # Impossible travel: different countries within 2h
                if last_ts:
                    if last_ts.tzinfo is None:
                        last_ts = last_ts.replace(tzinfo=timezone.utc)
                    if (timestamp - last_ts) < timedelta(hours=2):
                        r.score += 60
                        r.triggers.append(f"impossible_travel:{last_country}->{country_code}_in_<2h(weight=+60)")

        return r

    # ------------------------------------------------------------------
    # Score combination
    # ------------------------------------------------------------------
    @staticmethod
    def _combine_scores(rule_score: int, ml_score: Optional[float]) -> int:
        """
        Weighted: 40% rule-based + 60% ML (if available).
        Rule score is already additive (can exceed 100); we cap at 100.
        """
        rule_normalized = min(100, rule_score)
        if ml_score is not None:
            combined = int(rule_normalized * 0.40 + ml_score * 100 * 0.60)
        else:
            combined = rule_normalized
        return max(0, min(100, combined))

    # ------------------------------------------------------------------
    # Decision
    # ------------------------------------------------------------------
    @staticmethod
    def _make_decision(risk_score: int) -> str:
        if risk_score >= settings.RISK_SCORE_FRAUD_THRESHOLD:
            return "decline"
        if risk_score >= settings.RISK_SCORE_REVIEW_THRESHOLD:
            return "review"
        return "approve"
