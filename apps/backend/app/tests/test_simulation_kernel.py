from __future__ import annotations

from app.sim.simulation_kernel import SimulationKernel


def _floor_plan_fixture() -> dict:
    return {
        "building_bounds": {"min_x": 0, "min_y": 0, "max_x": 100, "max_y": 100},
        "detected_walls": [
            {"x1": 0, "y1": 0, "x2": 100, "y2": 0},
            {"x1": 100, "y1": 0, "x2": 100, "y2": 100},
            {"x1": 100, "y1": 100, "x2": 0, "y2": 100},
            {"x1": 0, "y1": 100, "x2": 0, "y2": 0},
        ],
        "detected_obstacles": [],
        "rooms": [],
        "exits": [{"id": "main-exit", "x": 50.0, "y": 0.0, "z": 0.0, "width": 4.0, "capacity": 120}],
        "hazards": [],
        "image_dimensions": {"width": 100, "height": 100},
    }


def _kernel_summary(kernel: SimulationKernel, steps: int = 6) -> list[dict]:
    timeline: list[dict] = []
    for _ in range(steps):
        frame = kernel.step(0.2)
        agents = frame.get("agents", [])[:5]
        timeline.append(
            {
                "frame_id": frame.get("frame_id"),
                "timestamp": round(float(frame.get("timestamp", 0.0)), 4),
                "evacuated": int(dict(frame.get("stats") or {}).get("evacuated", 0)),
                "remaining": int(dict(frame.get("stats") or {}).get("remaining", 0)),
                "hazard_concentration": round(float(dict(frame.get("hazard_state") or {}).get("max_concentration", 0.0)), 4),
                "agents": [
                    (
                        agent.get("agent_id"),
                        round(float(agent.get("x", 0.0)), 4),
                        round(float(agent.get("z", 0.0)), 4),
                        agent.get("status"),
                    )
                    for agent in agents
                ],
            }
        )
    return timeline


def test_simulation_kernel_is_deterministic_for_same_seed():
    config = {
        "seed": 4242,
        "mode": "studio",
        "num_agents": 24,
        "emergency_type": "fire",
        "routing_policy": "guided_evacuation",
        "panic_level": 0.58,
        "blocked_exits": [],
        "hazards": [],
    }

    kernel_a = SimulationKernel("session-deterministic-a", config)
    kernel_b = SimulationKernel("session-deterministic-a", config)
    floor_plan = _floor_plan_fixture()
    kernel_a.initialize(floor_plan)
    kernel_b.initialize(floor_plan)

    assert _kernel_summary(kernel_a) == _kernel_summary(kernel_b)


def test_simulation_kernel_modes_do_not_change_results_without_config_changes():
    studio_config = {
        "seed": 7171,
        "mode": "studio",
        "num_agents": 18,
        "emergency_type": "gas_leak",
        "routing_policy": "least_crowded",
        "panic_level": 0.43,
        "blocked_exits": [],
        "hazards": [],
    }
    batch_config = {**studio_config, "mode": "batch"}

    kernel_studio = SimulationKernel("session-mode-shared", studio_config)
    kernel_batch = SimulationKernel("session-mode-shared", batch_config)
    floor_plan = _floor_plan_fixture()
    kernel_studio.initialize(floor_plan)
    kernel_batch.initialize(floor_plan)

    assert _kernel_summary(kernel_studio) == _kernel_summary(kernel_batch)
