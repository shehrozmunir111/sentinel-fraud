from typing import Any, Dict, Tuple
from datetime import datetime
from app.services.velocity import VelocityCheckService
from app.services.ml_model import MLModelService
from app.repositories.transaction import TransactionRepository
from app.repositories.fraud_rule import FraudRuleRepository
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.fraud_rule import RuleType
import asyncio

from uuid import UUID

class RiskEngineService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.velocity_service = VelocityCheckService()
        self.ml_service = MLModelService()
        self.tx_repo = TransactionRepository(db)
        self.rule_repo = FraudRuleRepository(db)
    
    async def calculate_risk_score(self, transaction_data: dict) -> Tuple[int, str, Dict]:
        start_time = datetime.utcnow()
        
        # Ensure user_id is UUID
        if 'user_id' in transaction_data and not isinstance(transaction_data['user_id'], UUID):
            transaction_data['user_id'] = UUID(str(transaction_data['user_id']))
        
        velocity_task = self._check_velocity(transaction_data)
        amount_task = self._check_amount_rules(transaction_data)
        geo_task = self._check_geolocation_rules(transaction_data)
        ml_task = self._get_ml_prediction(transaction_data)
        
        results = await asyncio.gather(
            velocity_task, amount_task, geo_task, ml_task,
            return_exceptions=True
        )
        
        total_score = 0
        rule_contributions = {}
        
        if not isinstance(results[0], Exception):
            vel_score, vel_details = results[0]
            total_score += vel_score
            rule_contributions.update(vel_details)
        
        if not isinstance(results[1], Exception):
            amt_score, amt_details = results[1]
            total_score += amt_score
            rule_contributions.update(amt_details)
        
        if not isinstance(results[2], Exception):
            geo_score, geo_details = results[2]
            total_score += geo_score
            rule_contributions.update(geo_details)

        dynamic_score, dynamic_details = await self._check_dynamic_rules(transaction_data)
        total_score += dynamic_score
        rule_contributions.update(dynamic_details)
        
        ml_score = 0.0
        if not isinstance(results[3], Exception):
            ml_score = results[3]
            ml_risk = int(ml_score * 50)
            total_score += ml_risk
            rule_contributions['ml_prediction'] = ml_risk
        
        decision = self._make_decision(total_score, ml_score)
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return total_score, decision, {
            'ml_score': ml_score,
            'rule_contributions': rule_contributions,
            'processing_time_ms': processing_time
        }
    
    async def _check_velocity(self, tx: dict) -> Tuple[int, Dict]:
        scores = {}
        
        card_count, card_score = await self.velocity_service.check_card_velocity(tx['card_id'])
        if card_score > 0:
            scores['card_velocity'] = card_score
        
        user_count, user_score = await self.velocity_service.check_user_velocity(tx['user_id'])
        if user_score > 0:
            scores['user_velocity'] = user_score
        
        if tx.get('device_fingerprint'):
            dev_count, dev_score = await self.velocity_service.check_device_velocity(tx['device_fingerprint'])
            if dev_score > 0:
                scores['device_velocity'] = dev_score
        
        return sum(scores.values()), scores
    
    async def _check_amount_rules(self, tx: dict) -> Tuple[int, Dict]:
        scores = {}
        amount = float(tx['amount'])
        
        if amount > 50000:
            scores['amount_tier_50k'] = 50
        elif amount > 10000:
            scores['amount_tier_10k'] = 25
        
        avg_amount = await self.tx_repo.get_user_average_amount_30d(str(tx['user_id']))
        if avg_amount > 0 and amount > (avg_amount * 10):
            scores['amount_spike_10x'] = 35
        
        return sum(scores.values()), scores
    
    async def _check_geolocation_rules(self, tx: dict) -> Tuple[int, Dict]:
        scores = {}
        country = tx.get('country_code', '')
        user_id = str(tx['user_id'])
        
        high_risk_countries = {'XX', 'YY', 'ZZ'}
        if country in high_risk_countries:
            scores['high_risk_country'] = 30
        
        last_location = await self.velocity_service.get_last_transaction_location(user_id)
        if last_location and last_location.get('country') != country:
            scores['new_country'] = 15
            
            last_time = datetime.fromisoformat(last_location.get('timestamp', '2000-01-01'))
            current_time = tx['timestamp']
            if isinstance(current_time, str):
                current_time = datetime.fromisoformat(current_time.replace('Z', '+00:00'))
            
            hours_diff = (current_time - last_time).total_seconds() / 3600
            if hours_diff < 2:
                scores['impossible_travel'] = 60
        
        await self.velocity_service.set_last_transaction_location(user_id, {
            'country': country,
            'city': tx.get('city', ''),
            'timestamp': tx['timestamp'].isoformat() if isinstance(tx['timestamp'], datetime) else str(tx['timestamp'])
        })
        
        return sum(scores.values()), scores
    
    async def _get_ml_prediction(self, tx: dict) -> float:
        try:
            features = await self.ml_service.extract_features(tx, self.db)
            return await self.ml_service.predict(features)
        except Exception:
            return 0.0

    async def _check_dynamic_rules(self, tx: dict) -> Tuple[int, Dict[str, int]]:
        scores: Dict[str, int] = {}
        active_rules = await self.rule_repo.get_active_rules()

        for rule in active_rules:
            if await self._rule_matches(rule.rule_type, rule.conditions or {}, tx):
                scores[f"rule:{rule.rule_name}"] = rule.risk_weight

        return sum(scores.values()), scores

    async def _rule_matches(self, rule_type: RuleType, conditions: Dict[str, Any], tx: dict) -> bool:
        amount = float(tx["amount"])
        currency = tx.get("currency")
        country_code = tx.get("country_code")
        device_fingerprint = tx.get("device_fingerprint")

        if rule_type == RuleType.AMOUNT:
            min_amount = conditions.get("min_amount")
            max_amount = conditions.get("max_amount")
            required_currency = conditions.get("currency")
            if min_amount is not None and amount < float(min_amount):
                return False
            if max_amount is not None and amount <= float(max_amount):
                return False
            if required_currency and currency != required_currency:
                return False
            return True

        if rule_type == RuleType.GEOLOCATION:
            countries = conditions.get("country_codes") or conditions.get("countries")
            blocked_country = conditions.get("country_code")
            cities = conditions.get("cities")
            if countries and country_code not in countries:
                return False
            if blocked_country and country_code != blocked_country:
                return False
            if cities and tx.get("city") not in cities:
                return False
            return True

        if rule_type == RuleType.DEVICE:
            required_device = conditions.get("device_fingerprint")
            allow_missing = conditions.get("match_missing_device", False)
            if required_device:
                return device_fingerprint == required_device
            if allow_missing:
                return not device_fingerprint
            return bool(device_fingerprint)

        if rule_type == RuleType.VELOCITY:
            return await self._matches_velocity_rule(conditions, tx)

        return False

    async def _matches_velocity_rule(self, conditions: Dict[str, Any], tx: dict) -> bool:
        window_hours = int(conditions.get("window_hours", 1))
        entity = conditions.get("entity", "user")
        threshold = int(conditions.get("threshold", 0))
        if threshold <= 0:
            return False

        # Use persisted history rather than incrementing Redis counters again.
        if entity == "card":
            query_id = tx["card_id"]
            transactions = await self.tx_repo.get_card_transactions_last_hours(query_id, window_hours)
        else:
            query_id = str(tx["user_id"])
            transactions = await self.tx_repo.get_user_transactions_last_hours(query_id, window_hours)

        return len(transactions) >= threshold
    
    def _make_decision(self, total_score: int, ml_score: float) -> str:
        if total_score >= 80 or ml_score > 0.9:
            return "decline"
        elif total_score >= 50 or ml_score > 0.7:
            return "review"
        return "approve"
