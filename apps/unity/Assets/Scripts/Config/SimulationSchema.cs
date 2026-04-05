using System;

namespace PeopleFlow.UnitySimulation.Config
{
    [Serializable]
    public class SimulationStartMessage
    {
        public int schema_version;
        public string type;
        public string simulation_id;
        public SimulationConfig config;
        public string timestamp;
    }

    [Serializable]
    public class SimulationConfig
    {
        public int num_agents;
        public string emergency_type;
        public float panic_level;
        public int seed;
        public int floor_number;
        public float max_runtime_seconds;
        public int frame_stride;
        public bool record_frames;
        public string scenario_id;
        public string batch_id;
        public int batch_index;

        public SimulationProfileConfig[] agent_profiles;
        public SimulationProfileWeight[] profile_weights;
        public SimulationExitConfig[] exits;
        public SimulationHazardConfig[] hazards;
        public SimulationBoundary boundary;
        public SimulationSpawnConfig spawn;
        public SimulationFloorPlanRef floor_plan;
    }

    [Serializable]
    public class SimulationFloorPlanRef
    {
        public string floor_plan_id;
        public string building_name;
    }

    [Serializable]
    public class SimulationSpawnConfig
    {
        public Vector3Data center;
        public Vector3Data size;
        public int max_attempts;
    }

    [Serializable]
    public class SimulationProfileConfig
    {
        public string id;
        public string label;
        public float base_speed;
        public float max_speed;
        public float reaction_time;
        public float panic_susceptibility;
        public float mobility;
        public float compliance;
        public float group_cohesion;
        public float patience;
        public float familiarity;
        public float vision_range;
        public float hazard_aversion;
        public bool staff;
        public bool mobility_limited;
        public bool needs_assistance;
        public float exit_preference_emergency;
        public float exit_preference_accessible;
        public float exit_preference_nearest;
        public float exit_preference_known;
    }

    [Serializable]
    public class SimulationProfileWeight
    {
        public string profile_id;
        public float weight;
        public int count;
    }

    [Serializable]
    public class SimulationExitConfig
    {
        public string id;
        public string label;
        public float x;
        public float y;
        public float z;
        public float width;
        public float capacity;
        public bool is_emergency;
        public bool is_accessible;
        public bool is_blocked;
        public float preference_weight;
        public float queue_radius;
    }

    [Serializable]
    public class SimulationHazardConfig
    {
        public string id;
        public string hazard_type;
        public float x;
        public float y;
        public float z;
        public float radius;
        public float intensity;
        public float growth_rate;
        public float smoke_density;
        public bool blocks_exits;
        public bool is_active;
        public float start_time;
        public float duration;
    }

    [Serializable]
    public class SimulationBoundary
    {
        public Vector2Data[] points;
        public float min_x;
        public float max_x;
        public float min_z;
        public float max_z;
    }

    [Serializable]
    public class Vector2Data
    {
        public float x;
        public float y;
    }

    [Serializable]
    public class Vector3Data
    {
        public float x;
        public float y;
        public float z;
    }

    [Serializable]
    public class FloorPlanMessage
    {
        public int schema_version;
        public string type;
        public string simulation_id;
        public string building_name;
        public FloorData[] floors;
        public string file_path;
        public int floor_number;
        public WallData[] detected_walls;
        public WallData[] boundaries;
        public Vector2Data[] boundary_polygon;
        public BuildingBounds building_bounds;
        public ObstacleData[] detected_obstacles;
    }

    [Serializable]
    public class FloorData
    {
        public int floorNumber;
        public string name;
        public ExitData[] exits;
    }

    [Serializable]
    public class ExitData
    {
        public string id;
        public float x;
        public float y;
        public float z;
        public float width;
        public float capacity;
        public bool is_emergency;
        public bool is_accessible;
    }

    [Serializable]
    public class WallData
    {
        public float x1;
        public float y1;
        public float x2;
        public float y2;
        public float length;
        public float thickness;
        public string type;
        public float confidence;
    }

    [Serializable]
    public class BuildingBounds
    {
        public float min_x;
        public float min_y;
        public float max_x;
        public float max_y;
        public float width;
        public float height;
    }

    [Serializable]
    public class ObstacleData
    {
        public float x;
        public float y;
        public float z;
        public float width;
        public float height;
        public float depth;
        public string type;
    }
}
