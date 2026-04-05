using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.AI;
using PeopleFlow.UnitySimulation.Config;
using PeopleFlow.UnitySimulation.Agents;

namespace PeopleFlow.UnitySimulation.Managers
{
    /// <summary>
    /// Manages exits, queueing, and exit scoring for agents.
    /// </summary>
    public class ExitManager : MonoBehaviour
    {
        [Serializable]
        public class ExitRuntime
        {
            public string id;
            public string label;
            public Transform transform;
            public float width;
            public float capacity;
            public bool isEmergency;
            public bool isAccessible;
            public bool isBlocked;
            public float preferenceWeight;
            public float queueRadius;
            public int queuedAgents;
            public float flowRate;
            public float estimatedWait;
        }

        [Serializable]
        public class ExitUsageSnapshot
        {
            public string exit_id;
            public float x;
            public float y;
            public float z;
            public float width;
            public float capacity;
            public int queue_length;
            public bool is_blocked;
            public float estimated_wait;
        }

        [Header("Exit Settings")]
        public GameObject exitPrefab;
        public Transform exitsParent;
        public float defaultWidth = 2f;
        public float defaultCapacity = 1.33f;
        public float defaultQueueRadius = 4f;
        public bool drawGizmos = true;

        private readonly List<ExitRuntime> exits = new List<ExitRuntime>();

        public IReadOnlyList<ExitRuntime> Exits => exits;

        public void ClearExits()
        {
            foreach (var exit in exits)
            {
                if (exit.transform != null && exit.transform.gameObject != null)
                {
                    Destroy(exit.transform.gameObject);
                }
            }
            exits.Clear();
        }

        public void LoadExits(SimulationExitConfig[] configs)
        {
            ClearExits();
            if (configs == null || configs.Length == 0) return;

            foreach (var config in configs)
            {
                Vector3 position = new Vector3(config.x, config.y, config.z);
                Transform exitTransform = SpawnExit(position, config.label);
                var runtime = new ExitRuntime
                {
                    id = string.IsNullOrEmpty(config.id) ? Guid.NewGuid().ToString() : config.id,
                    label = string.IsNullOrEmpty(config.label) ? "Exit" : config.label,
                    transform = exitTransform,
                    width = config.width > 0 ? config.width : defaultWidth,
                    capacity = config.capacity > 0 ? config.capacity : defaultCapacity,
                    isEmergency = config.is_emergency,
                    isAccessible = config.is_accessible,
                    isBlocked = config.is_blocked,
                    preferenceWeight = config.preference_weight > 0 ? config.preference_weight : 1f,
                    queueRadius = config.queue_radius > 0 ? config.queue_radius : defaultQueueRadius,
                    queuedAgents = 0,
                    flowRate = 0f
                };
                exits.Add(runtime);
            }
        }

        public void RegisterExit(Transform transform, SimulationExitConfig config = null)
        {
            if (transform == null) return;
            var runtime = new ExitRuntime
            {
                id = config != null && !string.IsNullOrEmpty(config.id) ? config.id : Guid.NewGuid().ToString(),
                label = config != null && !string.IsNullOrEmpty(config.label) ? config.label : transform.name,
                transform = transform,
                width = config != null && config.width > 0 ? config.width : defaultWidth,
                capacity = config != null && config.capacity > 0 ? config.capacity : defaultCapacity,
                isEmergency = config != null && config.is_emergency,
                isAccessible = config != null && config.is_accessible,
                isBlocked = config != null && config.is_blocked,
                preferenceWeight = config != null && config.preference_weight > 0 ? config.preference_weight : 1f,
                queueRadius = config != null && config.queue_radius > 0 ? config.queue_radius : defaultQueueRadius
            };
            exits.Add(runtime);
        }

        public void UpdateQueues(List<AdvancedAgentController> agents)
        {
            foreach (var exit in exits)
            {
                exit.queuedAgents = 0;
            }

            if (agents == null) return;

            foreach (var agent in agents)
            {
                if (agent == null || agent.IsEvacuated) continue;
                var exit = GetExitById(agent.CurrentExitId);
                if (exit != null)
                {
                    float distance = Vector3.Distance(agent.transform.position, exit.transform.position);
                    if (distance <= Mathf.Max(1f, exit.queueRadius))
                    {
                        exit.queuedAgents += 1;
                    }
                }
            }

            foreach (var exit in exits)
            {
                exit.flowRate = exit.capacity > 0 ? exit.queuedAgents / exit.capacity : exit.queuedAgents;
                exit.estimatedWait = exit.capacity > 0 ? exit.queuedAgents / Mathf.Max(1f, exit.capacity) : exit.queuedAgents;
            }
        }

        public ExitRuntime GetBestExit(AgentProfile profile, Vector3 position, HazardManager hazardManager, float panicLevel)
        {
            if (exits.Count == 0) return null;

            ExitRuntime best = null;
            float bestScore = float.MaxValue;

            foreach (var exit in exits)
            {
                if (exit.transform == null) continue;

                if (profile.mobilityLimited && !exit.isAccessible)
                {
                    continue;
                }

                float distance = EstimatePathLength(position, exit.transform.position);
                float hazardPenalty = hazardManager != null ? hazardManager.GetHazardIntensity(exit.transform.position) : 0f;
                float queuePenalty = exit.queuedAgents / Mathf.Max(1f, exit.capacity);
                float waitPenalty = exit.estimatedWait * (1f - profile.patience);

                float emergencyBias = exit.isEmergency ? (1f - profile.exitPreferenceEmergency) : 1f;
                float accessibleBias = exit.isAccessible ? (1f - profile.exitPreferenceAccessible) : 1f;

                float score = distance;
                score *= (1f + hazardPenalty * profile.hazardAversion);
                score *= (1f + queuePenalty * (1f - profile.patience));
                score *= (1f + waitPenalty * 0.5f);
                score *= emergencyBias * accessibleBias;
                score /= Mathf.Max(0.1f, exit.preferenceWeight);

                if (exit.isBlocked)
                {
                    score *= 5f;
                }

                if (panicLevel > 0.7f)
                {
                    score *= (1f - profile.exitPreferenceNearest * 0.2f);
                }

                if (score < bestScore)
                {
                    bestScore = score;
                    best = exit;
                }
            }

            return best;
        }

        public ExitRuntime GetExitById(string exitId)
        {
            if (string.IsNullOrEmpty(exitId)) return null;
            foreach (var exit in exits)
            {
                if (exit.id == exitId) return exit;
            }
            return null;
        }

        public string GetExitIdByTransform(Transform exitTransform)
        {
            if (exitTransform == null) return null;
            foreach (var exit in exits)
            {
                if (exit.transform == exitTransform)
                {
                    return exit.id;
                }
            }
            return null;
        }

        public void UpdateBlockedExits(HazardManager hazardManager)
        {
            if (hazardManager == null) return;
            foreach (var exit in exits)
            {
                if (exit.transform == null) continue;
                exit.isBlocked = hazardManager.IsExitBlocked(exit.transform.position);
            }
        }

        public List<ExitUsageSnapshot> GetUsageSnapshots()
        {
            var snapshots = new List<ExitUsageSnapshot>();
            foreach (var exit in exits)
            {
                if (exit.transform == null) continue;
                snapshots.Add(new ExitUsageSnapshot
                {
                    exit_id = exit.id,
                    x = exit.transform.position.x,
                    y = exit.transform.position.y,
                    z = exit.transform.position.z,
                    width = exit.width,
                    capacity = exit.capacity,
                    queue_length = exit.queuedAgents,
                    is_blocked = exit.isBlocked,
                    estimated_wait = exit.estimatedWait
                });
            }
            return snapshots;
        }

        private Transform SpawnExit(Vector3 position, string label)
        {
            GameObject exitObj;
            if (exitPrefab != null)
            {
                exitObj = Instantiate(exitPrefab, position, Quaternion.identity, exitsParent ?? transform);
            }
            else
            {
                exitObj = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                exitObj.transform.position = position;
                exitObj.transform.localScale = new Vector3(2f, 0.5f, 2f);
                var renderer = exitObj.GetComponent<Renderer>();
                if (renderer != null)
                {
                    renderer.material = new Material(Shader.Find("Standard"))
                    {
                        color = Color.green
                    };
                }
            }
            exitObj.name = string.IsNullOrEmpty(label) ? "Exit" : label;
            exitObj.tag = "Exit";
            return exitObj.transform;
        }

        private float EstimatePathLength(Vector3 start, Vector3 end)
        {
            NavMeshPath path = new NavMeshPath();
            if (NavMesh.CalculatePath(start, end, NavMesh.AllAreas, path) && path.corners.Length > 1)
            {
                float length = 0f;
                for (int i = 1; i < path.corners.Length; i++)
                {
                    length += Vector3.Distance(path.corners[i - 1], path.corners[i]);
                }
                return length;
            }
            return Vector3.Distance(start, end);
        }

        private void OnDrawGizmos()
        {
            if (!drawGizmos) return;
            Gizmos.color = new Color(0.2f, 1f, 0.4f, 0.4f);
            foreach (var exit in exits)
            {
                if (exit.transform == null) continue;
                Gizmos.DrawSphere(exit.transform.position, 0.4f);
                Gizmos.DrawWireSphere(exit.transform.position, Mathf.Max(1f, exit.queueRadius));
            }
        }
    }
}
