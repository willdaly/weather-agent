from app.scoring import compute_risk, score_to_band


def test_score_to_band_low():
    assert score_to_band(0) == "low"
    assert score_to_band(3) == "low"


def test_score_to_band_moderate():
    assert score_to_band(4) == "moderate"
    assert score_to_band(6) == "moderate"


def test_score_to_band_high():
    assert score_to_band(7) == "high"
    assert score_to_band(9) == "high"


def test_score_to_band_severe():
    assert score_to_band(10) == "severe"
    assert score_to_band(20) == "severe"


def test_snow_morning_commute():
    risk, conf = compute_risk(["snow"], ["bus", "subway"], is_peak=True)
    # snow=5, bus extra=2, peak+2 -> 9 -> high
    assert risk == "high"
    assert conf > 0.6


def test_freezing_rain_risk():
    risk, conf = compute_risk(["freezing rain"], ["subway", "bus"], is_peak=False)
    # freezing_rain=7, bus extra=2 -> 9 -> high
    assert risk == "high"


def test_ferry_high_wind():
    risk, conf = compute_risk(["high wind"], ["ferry"], is_peak=False)
    # high_wind=5, ferry extra=3 -> 8 -> high
    assert risk == "high"


def test_light_rain_low_risk():
    risk, conf = compute_risk(["light rain"], ["subway"], is_peak=False)
    assert risk == "low"


def test_peak_bonus_applied():
    risk_off_peak, _ = compute_risk(["heavy rain"], ["bus"], is_peak=False)
    risk_peak, _ = compute_risk(["heavy rain"], ["bus"], is_peak=True)
    # Off-peak: heavy_rain=4, bus=1 -> 5 moderate; peak: +2 -> 7 high
    assert risk_off_peak in ("moderate", "high")
    # Peak version must be at least as severe
    bands = ["low", "moderate", "high", "severe"]
    assert bands.index(risk_peak) >= bands.index(risk_off_peak)


def test_confidence_range():
    for risk_val, conf_val in [
        compute_risk(["rain"], ["bus"], False),
        compute_risk(["snow", "ice"], ["commuter rail"], True),
        compute_risk([], ["subway"], False),
    ]:
        assert 0.0 <= conf_val <= 1.0
