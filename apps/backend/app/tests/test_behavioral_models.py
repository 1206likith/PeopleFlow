from app.services.behavioral_models import AgentBehavior, BehavioralModelEngine, DecisionModel
from app.services.evacuation_parameters import PopulationProfile


def test_update_behavior_accepts_disaster_proximity_signal():
    engine = BehavioralModelEngine()
    behavior = AgentBehavior(
        profile=PopulationProfile.NORMAL_ADULT,
        decision_model=DecisionModel.BOUNDED_RATIONALITY,
        pre_evacuation_delay=0.0,
        walking_speed=1.2,
        panic_level=0.2,
        stress_level=0.1,
        cognitive_load=0.0,
        social_influence=0.2,
        bounded_rationality_factor=0.8,
    )

    updated = engine.update_behavior(
        behavior,
        nearby_panic=0.0,
        disaster_proximity=0.9,
        congestion_level=0.2,
        time_in_simulation=12.0,
    )

    assert updated.panic_level > 0.2
    assert updated.stress_level > 0.1
    assert updated.cognitive_load > 0.0
