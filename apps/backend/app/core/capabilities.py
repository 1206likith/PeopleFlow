from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class Capability:
    id: str
    category: str
    description: str
    default_enabled: bool = True


CAPABILITY_GROUPS: List[Tuple[str, List[Tuple[str, str, bool]]]] = [
    (
        "blueprint",
        [
            ("auto_boundary_detection", "Detect external boundaries from blueprints.", True),
            ("semantic_segmentation", "Use semantic segmentation for floor plan parsing.", True),
            ("morphology_cleanup", "Apply morphology cleanup to linework.", True),
            ("gap_detection", "Detect gaps for corridors, doors, and rooms.", True),
            ("room_inference", "Infer room regions from enclosed spaces.", True),
            ("corridor_classification", "Classify corridor regions from gaps.", True),
            ("door_detection", "Detect door-like openings from linework.", True),
            ("exit_snap_to_walls", "Snap detected exits to boundary segments.", True),
            ("exit_deduplication", "De-duplicate exit points by proximity.", True),
            ("quality_scoring", "Score floor plan processing quality.", True),
        ],
    ),
    (
        "exits",
        [
            ("manual_exit_authoring", "Allow manual exit authoring via API.", True),
            ("exit_capacity_modeling", "Track exit capacity attributes.", True),
            ("exit_accessibility_flags", "Store accessibility flags per exit.", True),
            ("exit_usage_tracking", "Track exit usage during simulations.", True),
            ("blocked_exit_rules", "Apply blocked exit rules during hazards.", True),
            ("multi_floor_exit_mapping", "Map exits to floors for multi-floor plans.", True),
            ("exit_heatmap_overlay", "Expose exit utilization for heatmaps.", True),
            ("exit_recommendations", "Generate exit improvement recommendations.", True),
            ("exit_load_balancing", "Recommend load balancing across exits.", True),
            ("exit_revision_history", "Track manual exit revision history.", True),
        ],
    ),
    (
        "hazards",
        [
            ("fire_spread_model", "Model fire hazard propagation.", True),
            ("smoke_diffusion_model", "Model smoke diffusion effects.", True),
            ("flood_propagation_model", "Model flood propagation effects.", True),
            ("gas_leak_dispersion", "Model gas leak dispersion.", True),
            ("earthquake_impact_zones", "Model earthquake impact zones.", True),
            ("structural_collapse_zones", "Model structural collapse zones.", True),
            ("tactical_attack_zones", "Model tactical attack zones.", True),
            ("hazard_schedule", "Schedule hazards with start times.", True),
            ("hazard_intensity_decay", "Decay hazard intensity over time.", True),
            ("hazard_blocked_exit_integration", "Integrate hazard-driven blocked exits.", True),
        ],
    ),
    (
        "agents",
        [
            ("behavioral_profiles", "Support behavioral profiles for agents.", True),
            ("personality_engine", "Generate agent personalities.", True),
            ("mobility_constraints", "Apply mobility constraints per profile.", True),
            ("pre_evacuation_delay", "Delay evacuation based on behavior.", True),
            ("social_force_movement", "Simulate social force movement.", True),
            ("group_dynamics", "Model group dynamics and cohesion.", True),
            ("panic_propagation", "Propagate panic through proximity.", True),
            ("visibility_impairment", "Reduce visibility due to hazards.", True),
            ("health_degradation", "Track health degradation from hazards.", False),
            ("assisted_evacuation", "Model assisted evacuation for vulnerable agents.", False),
        ],
    ),
    (
        "simulation",
        [
            ("mock_engine", "Run mock simulation engine.", True),
            ("core_engine", "Run research-grade core simulation engine.", True),
            ("realtime_streaming", "Stream frames over WebSocket.", True),
            ("frame_persistence", "Persist simulation frames to storage.", True),
            ("frame_stride_sampling", "Sample frames at configured stride.", True),
            ("time_limit_enforcement", "Stop simulations at time limits.", True),
            ("seed_reproducibility", "Seed RNG for reproducible runs.", True),
            ("pathfinding_grid", "Use grid-based pathfinding.", True),
            ("boundary_confinement", "Constrain movement to boundaries.", True),
            ("scenario_batches", "Run batch scenarios for ensembles.", True),
        ],
    ),
    (
        "analytics",
        [
            ("evacuation_kpis", "Compute evacuation KPIs.", True),
            ("flow_rate_metrics", "Compute flow rate metrics.", True),
            ("congestion_heatmap", "Compute congestion heatmaps.", True),
            ("density_speed_curve", "Compute density-speed curves.", True),
            ("survival_score", "Compute survival score.", True),
            ("bottleneck_detection", "Detect bottlenecks in crowd flow.", True),
            ("exit_utilization_metrics", "Compute exit utilization metrics.", True),
            ("percentile_reporting", "Report percentile-based summaries.", True),
            ("timeline_export", "Export timeline summaries.", True),
            ("csv_exports", "Export data as CSV.", True),
        ],
    ),
    (
        "optimization",
        [
            ("multi_objective_optimization", "Multi-objective optimization engine.", True),
            ("route_recommendations", "Recommend routing policies.", True),
            ("exit_addition_suggestions", "Suggest adding exits.", True),
            ("policy_simulation", "Simulate policy changes.", True),
            ("capacity_tuning", "Tune capacity parameters.", True),
            ("crowd_redirection", "Redirect crowd away from hazards.", True),
            ("signage_guidance", "Simulate signage guidance.", False),
            ("hazard_mitigation", "Recommend hazard mitigation steps.", True),
            ("reinforcement_learning_routing", "Use RL for routing policies.", False),
            ("parameter_calibration", "Calibrate simulation parameters.", True),
        ],
    ),
    (
        "experiments",
        [
            ("baseline_runner", "Run baseline experiment suites.", True),
            ("ablation_runner", "Run ablation experiment suites.", True),
            ("calibration_runner", "Run calibration experiments.", True),
            ("optimization_runner", "Run optimization experiments.", True),
            ("validation_suite", "Run validation suites.", True),
            ("experiment_indexing", "Index experiment outputs.", True),
            ("metrics_export", "Export experiment metrics.", True),
            ("report_generation", "Generate experiment reports.", True),
            ("reproducible_configs", "Ensure reproducible configs.", True),
            ("results_versioning", "Version experiment results.", False),
        ],
    ),
    (
        "ops",
        [
            ("health_checks", "Expose health check endpoints.", True),
            ("readiness_checks", "Expose readiness check endpoints.", True),
            ("metrics_endpoint", "Expose Prometheus metrics endpoint.", True),
            ("correlation_ids", "Inject correlation IDs for tracing.", True),
            ("structured_logging", "Structured logging for requests.", True),
            ("rate_limiting", "Apply rate limiting policies.", True),
            ("security_headers", "Attach security headers.", True),
            ("feature_flags", "Runtime feature flag control.", True),
            ("audit_logging", "Record audit log events.", True),
            ("artifacts_storage", "Persist artifacts to disk.", True),
        ],
    ),
    (
        "security",
        [
            ("jwt_auth", "Deprecated JWT authentication capability (removed in v2).", False),
            ("password_strength_validation", "Enforce password strength.", True),
            ("cors_controls", "CORS configuration controls.", True),
            ("file_upload_validation", "Validate uploaded files.", True),
            ("safe_filename_sanitization", "Sanitize file names.", True),
            ("role_based_access_control", "Role-based access control.", False),
            ("api_key_auth", "API key authentication.", False),
            ("data_retention_policy", "Data retention policies.", False),
            ("pii_redaction", "PII redaction for logs.", False),
            ("request_throttling", "Advanced request throttling.", True),
        ],
    ),
]


CAPABILITIES: List[Capability] = []
for category, entries in CAPABILITY_GROUPS:
    for suffix, description, default_enabled in entries:
        cap_id = f"{category}.{suffix}"
        CAPABILITIES.append(
            Capability(
                id=cap_id,
                category=category,
                description=description,
                default_enabled=default_enabled,
            )
        )


CAPABILITY_INDEX: Dict[str, Capability] = {cap.id: cap for cap in CAPABILITIES}

if len(CAPABILITIES) != 100:
    raise RuntimeError(f"Expected 100 capabilities, found {len(CAPABILITIES)}")


def list_capabilities() -> List[Dict[str, object]]:
    return [
        {
            "id": cap.id,
            "category": cap.category,
            "description": cap.description,
            "default_enabled": cap.default_enabled,
        }
        for cap in CAPABILITIES
    ]
