using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.AI;
using PeopleFlow.UnitySimulation.Agents;
using PeopleFlow.UnitySimulation.Config;

namespace PeopleFlow.UnitySimulation.Managers
{
    /// <summary>
    /// Main simulation controller - manages agents, exits, hazards, and simulation state
    /// </summary>
    public class SimulationManager : MonoBehaviour
    {
        public static SimulationManager Instance { get; private set; }

        [Header("Simulation Settings")]
        public int numAgents = 100;
        public GameObject agentPrefab;
        public List<Transform> exitPoints = new List<Transform>();
        public Transform spawnArea;
        public string emergencyType = "fire";
        public int currentFloorNumber = 1;
        public bool useAdvancedAgents = true;
        public float spawnMinDistance = 0.6f;
        public int spawnMaxAttempts = 20;

        [Header("Deterministic Settings")]
        public bool useFixedTimestep = true;
        public float fixedTimestep = 0.02f;

        [Header("Runtime")]
        public List<CrowdAgent> agents = new List<CrowdAgent>();
        public List<AdvancedAgentController> advancedAgents = new List<AdvancedAgentController>();
        public bool isRunning = false;
        public float simulationTime = 0f;
        public int evacuatedCount = 0;

        [Header("Analytics")]
        public float densityCellSize = 3f;
        public int highAgentThreshold = 1500;
        public float maxDecisionIntervalMultiplier = 2.5f;
        public float decisionIntervalMultiplier = 1f;

        [Header("References")]
        public WebSocketClient webSocketClient;
        public DataExporter dataExporter;
        public Environment.FloorPlanLoader floorPlanLoader;
        public ExitManager exitManager;
        public HazardManager hazardManager;
        public BoundaryManager boundaryManager;
        public CommunicationManager communicationManager;
        public SimulationAnalyticsManager analyticsManager;
        public AgentTraceRecorder traceRecorder;

        private readonly Dictionary<Vector2Int, int> densityGrid = new Dictionary<Vector2Int, int>();
        private readonly Dictionary<int, AdvancedAgentController> groupLeaders = new Dictionary<int, AdvancedAgentController>();
        private readonly Dictionary<int, List<AdvancedAgentController>> groups = new Dictionary<int, List<AdvancedAgentController>>();
        private readonly Dictionary<string, int> profileCounts = new Dictionary<string, int>();
        private readonly Dictionary<string, int> exitEvacCounts = new Dictionary<string, int>();
        private readonly HashSet<int> evacuatedAgents = new HashSet<int>();
        private int groupCounter = 1;

        public ExitManager ExitManager => exitManager;
        public HazardManager HazardManager => hazardManager;
        public BoundaryManager BoundaryManager => boundaryManager;
        public CommunicationManager CommunicationManager => communicationManager;
        public SimulationAnalyticsManager AnalyticsManager => analyticsManager;

        [Serializable]
        public class ProfileCountSnapshot
        {
            public string profile_id;
            public int count;
        }

        [Serializable]
        public class ExitEvacCountSnapshot
        {
            public string exit_id;
            public int count;
        }

        [Serializable]
        public class DensityCellSnapshot
        {
            public float x;
            public float z;
            public int count;
        }

        void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }
            Instance = this;
        }

        void Start()
        {
            if (webSocketClient == null)
                webSocketClient = FindObjectOfType<WebSocketClient>();

            if (dataExporter == null)
                dataExporter = FindObjectOfType<DataExporter>();

            if (floorPlanLoader == null)
                floorPlanLoader = FindObjectOfType<Environment.FloorPlanLoader>();

            if (exitManager == null)
                exitManager = FindObjectOfType<ExitManager>();

            if (hazardManager == null)
                hazardManager = FindObjectOfType<HazardManager>();

            if (boundaryManager == null)
                boundaryManager = FindObjectOfType<BoundaryManager>();

            if (communicationManager == null)
                communicationManager = FindObjectOfType<CommunicationManager>();

            if (analyticsManager == null)
                analyticsManager = FindObjectOfType<SimulationAnalyticsManager>();

            if (traceRecorder == null)
                traceRecorder = FindObjectOfType<AgentTraceRecorder>();

            if (exitManager == null)
                exitManager = gameObject.AddComponent<ExitManager>();

            if (hazardManager == null)
                hazardManager = gameObject.AddComponent<HazardManager>();

            if (boundaryManager == null)
                boundaryManager = gameObject.AddComponent<BoundaryManager>();

            if (communicationManager == null)
                communicationManager = gameObject.AddComponent<CommunicationManager>();

            if (analyticsManager == null)
                analyticsManager = gameObject.AddComponent<SimulationAnalyticsManager>();

            if (traceRecorder == null)
                traceRecorder = gameObject.AddComponent<AgentTraceRecorder>();

            if (exitPoints.Count == 0)
            {
                var exits = GameObject.FindGameObjectsWithTag("Exit");
                foreach (var exit in exits)
                {
                    exitPoints.Add(exit.transform);
                }
            }
        }

        void Update()
        {
            if (isRunning)
            {
                float deltaTime = useFixedTimestep ? fixedTimestep : Time.deltaTime;
                simulationTime += deltaTime;
                UpdateSimulation();
            }
        }

        void FixedUpdate()
        {
            if (isRunning && useFixedTimestep)
            {
                // Physics updates happen here automatically
            }
        }

        /// <summary>
        /// Start simulation with configuration
        /// </summary>
        public void StartSimulation(int agentCount, string emergency, string simId)
        {
            var config = new SimulationConfig
            {
                num_agents = agentCount,
                emergency_type = emergency,
                floor_number = currentFloorNumber
            };
            StartSimulation(config, simId);
        }

        public void StartSimulation(SimulationConfig config, string simId)
        {
            if (config != null)
            {
                numAgents = config.num_agents > 0 ? config.num_agents : numAgents;
                emergencyType = string.IsNullOrEmpty(config.emergency_type) ? emergencyType : config.emergency_type;
                currentFloorNumber = config.floor_number > 0 ? config.floor_number : currentFloorNumber;

                if (config.seed != 0)
                {
                    UnityEngine.Random.InitState(config.seed);
                }

                if (boundaryManager != null && config.boundary != null)
                {
                    boundaryManager.SetBoundary(config.boundary);
                }

                if (exitManager != null && config.exits != null && config.exits.Length > 0)
                {
                    exitManager.LoadExits(config.exits);
                    exitPoints.Clear();
                    foreach (var exit in exitManager.Exits)
                    {
                        if (exit.transform != null)
                        {
                            exitPoints.Add(exit.transform);
                        }
                    }
                }

                if (hazardManager != null && config.hazards != null)
                {
                    hazardManager.LoadHazards(config.hazards);
                }
            }

            if (exitPoints.Count > 0 && exitManager != null && exitManager.Exits.Count == 0)
            {
                foreach (var exitPoint in exitPoints)
                {
                    exitManager.RegisterExit(exitPoint);
                }
            }

            isRunning = true;
            simulationTime = 0f;
            evacuatedCount = 0;
            evacuatedAgents.Clear();
            exitEvacCounts.Clear();

            SpawnAgents(config);

            if (traceRecorder != null)
            {
                traceRecorder.Clear();
            }

            if (!string.IsNullOrEmpty(simId) && webSocketClient != null)
            {
                webSocketClient.Connect(simId);
            }

            if (floorPlanLoader != null)
            {
                floorPlanLoader.LoadFloorPlan(null, null);
            }

            Debug.Log($"Simulation started: {numAgents} agents, {emergencyType} emergency");
        }

        private void SpawnAgents(SimulationConfig config)
        {
            foreach (var agent in agents)
            {
                if (agent != null) Destroy(agent.gameObject);
            }
            agents.Clear();
            advancedAgents.Clear();
            groups.Clear();
            groupLeaders.Clear();
            profileCounts.Clear();

            Vector3 spawnCenter = spawnArea != null ? spawnArea.position : Vector3.zero;
            Vector3 spawnSize = spawnArea != null ? spawnArea.localScale : new Vector3(40, 0, 40);

            if (config != null && config.spawn != null)
            {
                if (config.spawn.center != null)
                {
                    spawnCenter = new Vector3(config.spawn.center.x, config.spawn.center.y, config.spawn.center.z);
                }
                if (config.spawn.size != null)
                {
                    spawnSize = new Vector3(config.spawn.size.x, config.spawn.size.y, config.spawn.size.z);
                }
                if (config.spawn.max_attempts > 0)
                {
                    spawnMaxAttempts = config.spawn.max_attempts;
                }
            }

            List<AgentProfile> profiles = BuildProfiles(config);
            List<AgentProfile> profilePool = BuildProfilePool(numAgents, profiles, config != null ? config.profile_weights : null);

            int currentGroupId = 0;
            int currentGroupSize = 0;
            int currentGroupTarget = 0;

            for (int i = 0; i < numAgents; i++)
            {
                AgentProfile profile = profilePool.Count > 0 ? profilePool[profilePool.Count - 1] : profiles[UnityEngine.Random.Range(0, profiles.Count)];
                if (profilePool.Count > 0)
                {
                    profilePool.RemoveAt(profilePool.Count - 1);
                }

                Vector3 randomPos = Vector3.zero;
                bool found = false;
                for (int attempt = 0; attempt < Mathf.Max(4, spawnMaxAttempts); attempt++)
                {
                    if (boundaryManager != null && boundaryManager.HasBoundary)
                    {
                        randomPos = boundaryManager.GetRandomPointInside(spawnCenter.y);
                    }
                    else
                    {
                        randomPos = new Vector3(
                            spawnCenter.x + UnityEngine.Random.Range(-spawnSize.x / 2, spawnSize.x / 2),
                            spawnCenter.y,
                            spawnCenter.z + UnityEngine.Random.Range(-spawnSize.z / 2, spawnSize.z / 2)
                        );
                    }

                    if (NavMesh.SamplePosition(randomPos, out NavMeshHit hitCandidate, 5f, NavMesh.AllAreas))
                    {
                        if (!IsSpawnTooClose(hitCandidate.position))
                        {
                            randomPos = hitCandidate.position;
                            found = true;
                            break;
                        }
                    }
                }

                if (found && NavMesh.SamplePosition(randomPos, out NavMeshHit hit, 2f, NavMesh.AllAreas))
                {
                    GameObject agentObj = Instantiate(agentPrefab, hit.position, Quaternion.identity);
                    agentObj.name = $"Agent_{i}";

                    CrowdAgent agent = agentObj.GetComponent<CrowdAgent>();
                    if (agent != null)
                    {
                        agent.useAdvancedBehavior = useAdvancedAgents;
                        RegisterAgent(agent);
                    }

                    EnhancedCrowdAgent enhanced = agentObj.GetComponent<EnhancedCrowdAgent>();
                    if (enhanced != null)
                    {
                        enhanced.externalControl = useAdvancedAgents;
                    }

                    AdvancedAgentController advanced = agentObj.GetComponent<AdvancedAgentController>();
                    if (useAdvancedAgents)
                    {
                        if (advanced == null)
                        {
                            advanced = agentObj.AddComponent<AdvancedAgentController>();
                        }

                        int assignedGroup = 0;
                        bool leader = false;
                        if (profile.groupCohesion > 0.4f && UnityEngine.Random.value < profile.groupCohesion)
                        {
                            if (currentGroupId == 0 || currentGroupSize >= currentGroupTarget)
                            {
                                currentGroupId = groupCounter++;
                                currentGroupTarget = UnityEngine.Random.Range(2, 5);
                                currentGroupSize = 0;
                            }

                            assignedGroup = currentGroupId;
                            currentGroupSize += 1;
                            leader = currentGroupSize == 1 || profile.staff;
                        }

                        advanced.Initialize(profile, assignedGroup, leader);
                        advancedAgents.Add(advanced);

                        if (assignedGroup > 0)
                        {
                            if (!groups.ContainsKey(assignedGroup))
                            {
                                groups[assignedGroup] = new List<AdvancedAgentController>();
                            }
                            groups[assignedGroup].Add(advanced);
                            if (leader)
                            {
                                groupLeaders[assignedGroup] = advanced;
                            }
                        }

                        if (!profileCounts.ContainsKey(profile.id))
                        {
                            profileCounts[profile.id] = 0;
                        }
                        profileCounts[profile.id] += 1;
                    }
                    else if (agent != null)
                    {
                        if (exitPoints.Count > 0)
                        {
                            Transform targetExit = exitPoints[UnityEngine.Random.Range(0, exitPoints.Count)];
                            agent.SetTargetExit(targetExit);
                        }
                    }
                }
            }
        }

        private bool IsSpawnTooClose(Vector3 position)
        {
            float minDist = Mathf.Max(0.2f, spawnMinDistance);
            foreach (var agent in agents)
            {
                if (agent == null) continue;
                if (Vector3.Distance(position, agent.transform.position) < minDist)
                {
                    return true;
                }
            }
            foreach (var agent in advancedAgents)
            {
                if (agent == null) continue;
                if (Vector3.Distance(position, agent.transform.position) < minDist)
                {
                    return true;
                }
            }
            return false;
        }

        private List<AgentProfile> BuildProfiles(SimulationConfig config)
        {
            var profiles = new List<AgentProfile>();
            if (config != null && config.agent_profiles != null && config.agent_profiles.Length > 0)
            {
                foreach (var profileConfig in config.agent_profiles)
                {
                    profiles.Add(AgentProfile.FromConfig(profileConfig));
                }
            }

            if (profiles.Count == 0)
            {
                profiles.AddRange(AgentProfileLibrary.GetDefaults());
            }

            return profiles;
        }

        private List<AgentProfile> BuildProfilePool(int totalAgents, List<AgentProfile> profiles, SimulationProfileWeight[] weights)
        {
            var pool = new List<AgentProfile>();
            if (profiles == null || profiles.Count == 0) return pool;

            if (weights != null && weights.Length > 0)
            {
                float totalWeight = 0f;
                foreach (var weight in weights)
                {
                    totalWeight += weight.weight > 0 ? weight.weight : 0f;
                }

                int remaining = totalAgents;
                foreach (var weight in weights)
                {
                    AgentProfile profile = profiles.Find(p => p.id == weight.profile_id) ?? profiles[0];
                    int count = weight.count > 0 ? weight.count : Mathf.RoundToInt((weight.weight / Mathf.Max(0.01f, totalWeight)) * totalAgents);
                    count = Mathf.Clamp(count, 0, remaining);
                    for (int i = 0; i < count; i++)
                    {
                        pool.Add(profile);
                    }
                    remaining -= count;
                }

                while (remaining > 0)
                {
                    pool.Add(profiles[UnityEngine.Random.Range(0, profiles.Count)]);
                    remaining -= 1;
                }
            }

            if (pool.Count == 0)
            {
                for (int i = 0; i < totalAgents; i++)
                {
                    pool.Add(profiles[UnityEngine.Random.Range(0, profiles.Count)]);
                }
            }

            // Shuffle pool
            for (int i = 0; i < pool.Count; i++)
            {
                int j = UnityEngine.Random.Range(i, pool.Count);
                var temp = pool[i];
                pool[i] = pool[j];
                pool[j] = temp;
            }

            return pool;
        }

        private void UpdateSimulation()
        {
            RebuildDensityGrid();

            if (exitManager != null)
            {
                exitManager.UpdateQueues(advancedAgents);
            }

            int activeAgents = advancedAgents.Count > 0 ? advancedAgents.Count : agents.Count;
            if (highAgentThreshold > 0)
            {
                float overload = Mathf.Clamp01((activeAgents - highAgentThreshold) / (float)highAgentThreshold);
                decisionIntervalMultiplier = Mathf.Lerp(1f, maxDecisionIntervalMultiplier, overload);
            }
            else
            {
                decisionIntervalMultiplier = 1f;
            }

            if (hazardManager != null && exitManager != null)
            {
                exitManager.UpdateBlockedExits(hazardManager);
            }

            if (communicationManager != null)
            {
                communicationManager.BroadcastRecommendations(advancedAgents, exitManager, hazardManager);
            }

            if (analyticsManager != null)
            {
                analyticsManager.UpdateMetrics(advancedAgents, agents, hazardManager, densityCellSize);
            }

            if (traceRecorder != null)
            {
                traceRecorder.Capture(advancedAgents, agents);
            }

            if (agents.Count > 0 && (advancedAgents == null || advancedAgents.Count == 0))
            {
                foreach (var agent in agents)
                {
                    if (agent == null || !agent.hasEvacuated) continue;
                    if (!evacuatedAgents.Contains(agent.GetInstanceID()))
                    {
                        NotifyEvacuated(agent, agent.targetExit);
                    }
                }
            }

            if (evacuatedCount >= numAgents * 0.95f)
            {
                CompleteSimulation();
            }
        }

        private void RebuildDensityGrid()
        {
            densityGrid.Clear();

            if (advancedAgents.Count > 0)
            {
                foreach (var agent in advancedAgents)
                {
                    if (agent == null || agent.IsEvacuated) continue;
                    AddDensity(agent.transform.position);
                }
            }
            else
            {
                foreach (var agent in agents)
                {
                    if (agent == null || agent.GetStatus() == "evacuated") continue;
                    AddDensity(agent.transform.position);
                }
            }
        }

        private void AddDensity(Vector3 position)
        {
            Vector2Int cell = new Vector2Int(
                Mathf.FloorToInt(position.x / densityCellSize),
                Mathf.FloorToInt(position.z / densityCellSize)
            );

            if (!densityGrid.ContainsKey(cell))
                densityGrid[cell] = 0;
            densityGrid[cell] += 1;
        }

        public float GetLocalDensity(Vector3 position)
        {
            Vector2Int cell = new Vector2Int(
                Mathf.FloorToInt(position.x / densityCellSize),
                Mathf.FloorToInt(position.z / densityCellSize)
            );
            if (densityGrid.TryGetValue(cell, out int count))
            {
                return count;
            }
            return 0f;
        }

        private void CompleteSimulation()
        {
            isRunning = false;
            Debug.Log($"Simulation complete: {evacuatedCount}/{numAgents} evacuated in {simulationTime:F2}s");
        }

        public void PauseSimulation()
        {
            isRunning = false;
        }

        public void ResumeSimulation()
        {
            isRunning = true;
        }

        public void StopSimulation()
        {
            isRunning = false;
            evacuatedCount = 0;
            simulationTime = 0f;
        }

        public void RegisterAgent(CrowdAgent agent)
        {
            if (agent != null && !agents.Contains(agent))
            {
                agents.Add(agent);
            }
        }

        public void UnregisterAgent(CrowdAgent agent)
        {
            if (agent != null && agents.Contains(agent))
            {
                agents.Remove(agent);
            }
        }

        public void NotifyEvacuated(AdvancedAgentController agent, string exitId)
        {
            if (agent == null) return;
            if (!evacuatedAgents.Add(agent.GetInstanceID())) return;

            evacuatedCount += 1;
            if (!string.IsNullOrEmpty(exitId))
            {
                if (!exitEvacCounts.ContainsKey(exitId))
                {
                    exitEvacCounts[exitId] = 0;
                }
                exitEvacCounts[exitId] += 1;
            }
        }

        public void NotifyEvacuated(CrowdAgent agent, Transform exitTransform)
        {
            if (agent == null) return;
            if (!evacuatedAgents.Add(agent.GetInstanceID())) return;

            evacuatedCount += 1;
            if (exitManager != null && exitTransform != null)
            {
                string exitId = exitManager.GetExitIdByTransform(exitTransform);
                if (!string.IsNullOrEmpty(exitId))
                {
                    if (!exitEvacCounts.ContainsKey(exitId))
                    {
                        exitEvacCounts[exitId] = 0;
                    }
                    exitEvacCounts[exitId] += 1;
                }
            }
        }

        public Vector3 GetGroupLeaderPosition(int groupId)
        {
            if (groupId <= 0) return Vector3.zero;
            if (groupLeaders.TryGetValue(groupId, out var leader) && leader != null)
            {
                return leader.transform.position;
            }
            return Vector3.zero;
        }

        public AdvancedAgentController FindNearestStaff(Vector3 position, float radius)
        {
            AdvancedAgentController closest = null;
            float minDistance = radius;

            foreach (var agent in advancedAgents)
            {
                if (agent == null || agent.IsEvacuated || agent.profile == null || !agent.profile.staff) continue;
                float distance = Vector3.Distance(position, agent.transform.position);
                if (distance <= minDistance)
                {
                    minDistance = distance;
                    closest = agent;
                }
            }

            return closest;
        }

        public List<ProfileCountSnapshot> GetProfileCounts()
        {
            var snapshots = new List<ProfileCountSnapshot>();
            foreach (var kvp in profileCounts)
            {
                snapshots.Add(new ProfileCountSnapshot
                {
                    profile_id = kvp.Key,
                    count = kvp.Value
                });
            }
            return snapshots;
        }

        public List<ExitEvacCountSnapshot> GetExitEvacCounts()
        {
            var snapshots = new List<ExitEvacCountSnapshot>();
            foreach (var kvp in exitEvacCounts)
            {
                snapshots.Add(new ExitEvacCountSnapshot
                {
                    exit_id = kvp.Key,
                    count = kvp.Value
                });
            }
            return snapshots;
        }

        public List<DensityCellSnapshot> GetDensityHeatmap(int maxCells = 200)
        {
            var cells = new List<DensityCellSnapshot>();
            foreach (var kvp in densityGrid)
            {
                cells.Add(new DensityCellSnapshot
                {
                    x = kvp.Key.x * densityCellSize + densityCellSize / 2f,
                    z = kvp.Key.y * densityCellSize + densityCellSize / 2f,
                    count = kvp.Value
                });
            }

            cells.Sort((a, b) => b.count.CompareTo(a.count));
            if (cells.Count > maxCells)
            {
                cells.RemoveRange(maxCells, cells.Count - maxCells);
            }
            return cells;
        }

        public (int totalAgents, int evacuated, int remaining, float elapsedTime) GetStats()
        {
            return (numAgents, evacuatedCount, Mathf.Max(0, numAgents - evacuatedCount), simulationTime);
        }

        public void ApplyFloorPlanData(FloorPlanMessage floorPlan)
        {
            if (floorPlan == null) return;

            currentFloorNumber = floorPlan.floor_number > 0 ? floorPlan.floor_number : currentFloorNumber;

            if (boundaryManager != null && floorPlan.boundary_polygon != null && floorPlan.boundary_polygon.Length >= 3)
            {
                var boundary = new SimulationBoundary
                {
                    points = floorPlan.boundary_polygon,
                };
                boundaryManager.SetBoundary(boundary);
            }
            else if (boundaryManager != null && floorPlan.building_bounds != null)
            {
                var bounds = floorPlan.building_bounds;
                var boundary = new SimulationBoundary
                {
                    points = new[]
                    {
                        new Vector2Data { x = bounds.min_x, y = bounds.min_y },
                        new Vector2Data { x = bounds.max_x, y = bounds.min_y },
                        new Vector2Data { x = bounds.max_x, y = bounds.max_y },
                        new Vector2Data { x = bounds.min_x, y = bounds.max_y },
                    },
                    min_x = bounds.min_x,
                    max_x = bounds.max_x,
                    min_z = bounds.min_y,
                    max_z = bounds.max_y,
                };
                boundaryManager.SetBoundary(boundary);
            }

            FloorData selectedFloor = null;
            if (floorPlan.floors != null)
            {
                foreach (var floor in floorPlan.floors)
                {
                    if (floor.floorNumber == currentFloorNumber)
                    {
                        selectedFloor = floor;
                        break;
                    }
                }
                if (selectedFloor == null && floorPlan.floors.Length > 0)
                {
                    selectedFloor = floorPlan.floors[0];
                }
            }

            if (selectedFloor != null && selectedFloor.exits != null && exitManager != null)
            {
                var exitConfigs = new SimulationExitConfig[selectedFloor.exits.Length];
                for (int i = 0; i < selectedFloor.exits.Length; i++)
                {
                    var exit = selectedFloor.exits[i];
                    exitConfigs[i] = new SimulationExitConfig
                    {
                        id = exit.id,
                        label = "Exit",
                        x = exit.x,
                        y = exit.y,
                        z = exit.z,
                        width = exit.width,
                        capacity = exit.capacity,
                        is_emergency = exit.is_emergency,
                        is_accessible = exit.is_accessible
                    };
                }

                exitManager.LoadExits(exitConfigs);
                exitPoints.Clear();
                foreach (var exit in exitManager.Exits)
                {
                    if (exit.transform != null)
                    {
                        exitPoints.Add(exit.transform);
                    }
                }
            }
        }
    }
}
