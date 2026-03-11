"""
SentinelFraud Unit Tests
Tests for Risk Engine, Velocity Service, ML Features, Security
"""

import asyncio
import math
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.security import hash_password, verify_password, create_access_token, decode_token
from app.ml.features import extract_features, FEATURE_NAMES
from app.services.risk_engine import RiskEngineService
from app.services.velocity_check import VelocityCheckService


# ---------------------------------------------------------------------------
# Security tests
# ---------------------------------------------------------------------------
class TestSecurity:
    def test_hash_and_verify_password(self):
        password = "SecurePass123!"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed)
        assert not verify_password("wrong_password", hashed)

    def test_create_and_decode_access_token(self):
        user_id = str(uuid.uuid4())
        token = create_access_token(subject=user_id, role="analyst")
        payload = decode_token(token)
        assert payload["sub"] == user_id
        assert payload["role"] == "analyst"
        assert payload["type"] == "access"

    def test_invalid_token_raises(self):
        with pytest.raises(ValueError):
            decode_token("not.a.valid.token")


# ---------------------------------------------------------------------------
# ML Feature extraction tests
# ---------------------------------------------------------------------------
class TestMLFeatures:
    def test_feature_vector_length(self):
        ts = datetime(2024, 3, 15, 14, 30, tzinfo=timezone.utc)
        features = extract_features(
            amount=150.0,
            timestamp=ts,
            avg_amount_30d=120.0,
            time_since_last_tx_seconds=3600,
            is_international=False,
            is_new_device=False,
            is_high_risk_country=False,
            merchant_category="grocery",
            currency="USD",
            card_velocity_1h=2,
            user_velocity_1h=3,
        )
        assert len(features) == len(FEATURE_NAMES)

    def test_amount_log_feature(self):
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        features = extract_features(
            amount=100.0,
            timestamp=ts,
            avg_amount_30d=100.0,
            time_since_last_tx_seconds=3600,
            is_international=False,
            is_new_device=False,
            is_high_risk_country=False,
            merchant_category=None,
            currency="USD",
            card_velocity_1h=1,
            user_velocity_1h=1,
        )
        # features[1] = log1p(amount)
        assert abs(features[1] - math.log1p(100.0)) < 1e-6

    def test_weekend_detection(self):
        # Saturday = weekday 5
        saturday = datetime(2024, 3, 16, 12, 0, tzinfo=timezone.utc)  # Saturday
        weekday = datetime(2024, 3, 18, 12, 0, tzinfo=timezone.utc)   # Monday
        f_sat = extract_features(100, saturday, 100, 3600, False, False, False, None, "USD", 1, 1)
        f_mon = extract_features(100, weekday, 100, 3600, False, False, False, None, "USD", 1, 1)
        assert f_sat[4] == 1.0   # is_weekend
        assert f_mon[4] == 0.0

    def test_night_detection(self):
        night = datetime(2024, 3, 15, 2, 0, tzinfo=timezone.utc)   # 2 AM
        day = datetime(2024, 3, 15, 14, 0, tzinfo=timezone.utc)    # 2 PM
        f_night = extract_features(100, night, 100, 3600, False, False, False, None, "USD", 1, 1)
        f_day = extract_features(100, day, 100, 3600, False, False, False, None, "USD", 1, 1)
        assert f_night[5] == 1.0  # is_night
        assert f_day[5] == 0.0


# ---------------------------------------------------------------------------
# Risk Engine unit tests (mocked DB + Redis)
# ---------------------------------------------------------------------------
class TestRiskEngine:
    def _make_engine(self):
        mock_db = MagicMock()
        engine = RiskEngineService(mock_db)
        return engine

    def test_combine_scores_ml_only(self):
        engine = self._make_engine()
        score = engine._combine_scores(rule_score=0, ml_score=0.9)
        assert score == 54  # 0*0.4 + 90*0.6

    def test_combine_scores_rule_only(self):
        engine = self._make_engine()
        score = engine._combine_scores(rule_score=80, ml_score=None)
        assert score == 80

    def test_combine_scores_both(self):
        engine = self._make_engine()
        score = engine._combine_scores(rule_score=50, ml_score=0.8)
        assert score == 68  # 50*0.4 + 80*0.6

    def test_combine_scores_capped(self):
        engine = self._make_engine()
        score = engine._combine_scores(rule_score=200, ml_score=1.0)
        assert score == 100

    def test_decision_approve(self):
        engine = self._make_engine()
        assert engine._make_decision(10) == "approve"
        assert engine._make_decision(39) == "approve"

    def test_decision_review(self):
        engine = self._make_engine()
        assert engine._make_decision(40) == "review"
        assert engine._make_decision(69) == "review"

    def test_decision_decline(self):
        engine = self._make_engine()
        assert engine._make_decision(70) == "decline"
        assert engine._make_decision(100) == "decline"

    def test_amount_rule_high(self):
        engine = self._make_engine()
        result = engine._apply_amount_rules(amount=15_000, avg_30d=500)
        assert result.score == 25
        assert any("amount_high" in t for t in result.triggers)

    def test_amount_rule_very_high(self):
        engine = self._make_engine()
        result = engine._apply_amount_rules(amount=60_000, avg_30d=500)
        assert result.score == 50
        assert any("amount_very_high" in t for t in result.triggers)

    def test_amount_rule_spike(self):
        engine = self._make_engine()
        result = engine._apply_amount_rules(amount=5_000, avg_30d=100)
        # 5000 >= 100 * 10 = 1000 → spike
        assert result.score == 35
        assert any("amount_spike" in t for t in result.triggers)


# ---------------------------------------------------------------------------
# Velocity tests (mocked Redis)
# ---------------------------------------------------------------------------
class TestVelocityCheck:
    @pytest.mark.asyncio
    async def test_card_velocity_breach(self):
        service = VelocityCheckService()
        with patch("app.services.velocity_check.increment_velocity_counter", new_callable=AsyncMock) as mock_inc:
            mock_inc.return_value = 8  # Over limit of 5
            result = await service.check_and_increment("card123", None, None)
            assert result.risk_addition == 30
            assert any("card_velocity" in t for t in result.triggers)

    @pytest.mark.asyncio
    async def test_no_breach(self):
        service = VelocityCheckService()
        with patch("app.services.velocity_check.increment_velocity_counter", new_callable=AsyncMock) as mock_inc:
            mock_inc.return_value = 2  # Under all limits
            result = await service.check_and_increment("card123", "user456", "device789")
            assert result.risk_addition == 0
            assert len(result.triggers) == 0


# ---------------------------------------------------------------------------
# Conftest / async setup
# ---------------------------------------------------------------------------
@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
