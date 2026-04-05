using System;
using System.Collections.Generic;
using UnityEngine;
using PeopleFlow.UnitySimulation.Config;

namespace PeopleFlow.UnitySimulation.Managers
{
    /// <summary>
    /// Manages hazards (fire, smoke, blocked exits) and provides intensity queries.
    /// </summary>
    public class HazardManager : MonoBehaviour
    {
        [Serializable]
        public class HazardRuntime
        {
            public string id;
            public string hazardType;
            public Vector3 position;
            public float radius;
            public float intensity;
            public float growthRate;
            public float smokeDensity;
            public bool blocksExits;
            public bool isActive;
            public GameObject instance;
            public UnityEngine.AI.NavMeshObstacle navObstacle;
            public float startTime;
            public float duration;
        }

        [Serializable]
        public class HazardSnapshot
        {
            public string hazard_id;
            public string hazard_type;
            public float x;
            public float y;
            public float z;
            public float radius;
            public float intensity;
            public bool blocks_exits;
        }

        [Header("Hazard Prefabs")]
        public GameObject firePrefab;
        public GameObject smokePrefab;
        public GameObject hazardMarkerPrefab;

        [Header("Defaults")]
        public float defaultRadius = 6f;
        public float defaultIntensity = 1f;
        public bool drawGizmos = true;

        private readonly List<HazardRuntime> hazards = new List<HazardRuntime>();

        public IReadOnlyList<HazardRuntime> Hazards => hazards;

        public void ClearHazards()
        {
            foreach (var hazard in hazards)
            {
                if (hazard.instance != null)
                {
                    Destroy(hazard.instance);
                }
            }
            hazards.Clear();
        }

        public void LoadHazards(SimulationHazardConfig[] configs)
        {
            ClearHazards();
            if (configs == null) return;

            foreach (var config in configs)
            {
                bool isActive = config.is_active;
                if (!isActive)
                {
                    isActive = !string.IsNullOrEmpty(config.hazard_type) ||
                               config.radius > 0 ||
                               config.intensity > 0 ||
                               config.growth_rate > 0 ||
                               config.smoke_density > 0;
                }

                var runtime = new HazardRuntime
                {
                    id = string.IsNullOrEmpty(config.id) ? Guid.NewGuid().ToString() : config.id,
                    hazardType = string.IsNullOrEmpty(config.hazard_type) ? "fire" : config.hazard_type,
                    position = new Vector3(config.x, config.y, config.z),
                    radius = config.radius > 0 ? config.radius : defaultRadius,
                    intensity = config.intensity > 0 ? config.intensity : defaultIntensity,
                    growthRate = config.growth_rate,
                    smokeDensity = config.smoke_density,
                    blocksExits = config.blocks_exits,
                    isActive = isActive,
                    startTime = config.start_time,
                    duration = config.duration
                };

                runtime.instance = SpawnHazardVisual(runtime);
                hazards.Add(runtime);
            }
        }

        private GameObject SpawnHazardVisual(HazardRuntime hazard)
        {
            GameObject prefab = hazardMarkerPrefab;
            if (hazard.hazardType == "fire" && firePrefab != null)
            {
                prefab = firePrefab;
            }
            else if (hazard.hazardType == "smoke" && smokePrefab != null)
            {
                prefab = smokePrefab;
            }

            if (prefab == null)
            {
                GameObject marker = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                marker.transform.position = hazard.position;
                marker.transform.localScale = Vector3.one * Mathf.Max(1f, hazard.radius * 0.4f);
                marker.name = $"Hazard_{hazard.hazardType}";
                var renderer = marker.GetComponent<Renderer>();
                if (renderer != null)
                {
                    renderer.material = new Material(Shader.Find("Standard"))
                    {
                        color = hazard.hazardType == "smoke" ? new Color(0.4f, 0.4f, 0.4f, 0.6f) : new Color(1f, 0.3f, 0.1f, 0.8f)
                    };
                }
                AttachNavMeshObstacle(marker, hazard);
                return marker;
            }

            GameObject instance = Instantiate(prefab, hazard.position, Quaternion.identity, transform);
            instance.name = $"Hazard_{hazard.hazardType}";
            AttachNavMeshObstacle(instance, hazard);
            return instance;
        }

        private void AttachNavMeshObstacle(GameObject obj, HazardRuntime hazard)
        {
            if (obj == null || hazard == null) return;
            if (!hazard.blocksExits && hazard.hazardType != "fire") return;

            var obstacle = obj.GetComponent<UnityEngine.AI.NavMeshObstacle>();
            if (obstacle == null)
            {
                obstacle = obj.AddComponent<UnityEngine.AI.NavMeshObstacle>();
            }
            obstacle.carving = true;
            obstacle.shape = UnityEngine.AI.NavMeshObstacleShape.Capsule;
            obstacle.radius = Mathf.Max(0.5f, hazard.radius * 0.25f);
            obstacle.height = 2f;
            hazard.navObstacle = obstacle;
        }

        void Update()
        {
            if (hazards.Count == 0) return;

            float dt = Time.deltaTime;
            foreach (var hazard in hazards)
            {
                float simTime = SimulationManager.Instance != null ? SimulationManager.Instance.simulationTime : Time.time;
                bool withinWindow = simTime >= hazard.startTime;
                if (hazard.duration > 0)
                {
                    withinWindow = withinWindow && simTime <= hazard.startTime + hazard.duration;
                }

                if (!hazard.isActive || !withinWindow)
                {
                    if (hazard.instance != null)
                    {
                        hazard.instance.SetActive(false);
                    }
                    continue;
                }

                if (hazard.instance != null && !hazard.instance.activeSelf)
                {
                    hazard.instance.SetActive(true);
                }

                if (hazard.growthRate > 0f)
                {
                    hazard.radius += hazard.growthRate * dt;
                }
                if (hazard.instance != null)
                {
                    hazard.instance.transform.position = hazard.position;
                    hazard.instance.transform.localScale = Vector3.one * Mathf.Max(1f, hazard.radius * 0.4f);
                }
                if (hazard.navObstacle != null)
                {
                    hazard.navObstacle.radius = Mathf.Max(0.5f, hazard.radius * 0.25f);
                }
            }
        }

        public float GetHazardIntensity(Vector3 position)
        {
            float total = 0f;
            foreach (var hazard in hazards)
            {
                if (!hazard.isActive) continue;
                float distance = Vector3.Distance(position, hazard.position);
                if (distance <= hazard.radius)
                {
                    float falloff = 1f - (distance / Mathf.Max(0.1f, hazard.radius));
                    total += hazard.intensity * falloff;
                }
            }
            return total;
        }

        public float GetSmokeIntensity(Vector3 position)
        {
            float total = 0f;
            foreach (var hazard in hazards)
            {
                if (!hazard.isActive || hazard.hazardType != "smoke") continue;
                float distance = Vector3.Distance(position, hazard.position);
                if (distance <= hazard.radius)
                {
                    float falloff = 1f - (distance / Mathf.Max(0.1f, hazard.radius));
                    total += hazard.smokeDensity * falloff;
                }
            }
            return total;
        }

        public bool IsExitBlocked(Vector3 exitPosition, float buffer = 1.5f)
        {
            foreach (var hazard in hazards)
            {
                if (!hazard.isActive || !hazard.blocksExits) continue;
                float distance = Vector3.Distance(exitPosition, hazard.position);
                if (distance <= hazard.radius + buffer)
                {
                    return true;
                }
            }
            return false;
        }

        public List<HazardSnapshot> GetSnapshots()
        {
            var snapshots = new List<HazardSnapshot>();
            foreach (var hazard in hazards)
            {
                if (!hazard.isActive) continue;
                snapshots.Add(new HazardSnapshot
                {
                    hazard_id = hazard.id,
                    hazard_type = hazard.hazardType,
                    x = hazard.position.x,
                    y = hazard.position.y,
                    z = hazard.position.z,
                    radius = hazard.radius,
                    intensity = hazard.intensity,
                    blocks_exits = hazard.blocksExits
                });
            }
            return snapshots;
        }

        private void OnDrawGizmos()
        {
            if (!drawGizmos) return;
            Gizmos.color = new Color(1f, 0.2f, 0.1f, 0.2f);
            foreach (var hazard in hazards)
            {
                if (!hazard.isActive) continue;
                Gizmos.DrawSphere(hazard.position, hazard.radius);
            }
        }
    }
}
