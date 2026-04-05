using System;
using System.Collections.Generic;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;
using PeopleFlow.UnitySimulation.Config;
using PeopleFlow.UnitySimulation.Agents;

namespace PeopleFlow.UnitySimulation.Managers
{
    /// <summary>
    /// Production-grade WebSocket client for Unity
    /// Uses native .NET WebSocket for real-time bidirectional communication
    /// </summary>
    public class WebSocketClient : MonoBehaviour
    {
        private ClientWebSocket ws;
        private CancellationTokenSource cancellationTokenSource;
        private bool isConnected = false;
        private Queue<string> messageQueue = new Queue<string>();
        private Dictionary<string, Action<string>> messageHandlers = new Dictionary<string, Action<string>>();

        [Header("Connection Settings")]
        public string serverUrl = "ws://localhost:8000";
        public string simulationId = "";
        public float reconnectDelay = 2f;
        public int maxReconnectAttempts = 5;

        [Header("Frame Settings")]
        public float frameRate = 10f; // FPS
        public int schemaVersion = 1;

        private float lastFrameTime = 0f;
        private int reconnectAttempts = 0;

        public bool IsConnected => isConnected && ws != null && ws.State == WebSocketState.Open;

        public event Action<string> OnMessageReceived;

        void Awake()
        {
            cancellationTokenSource = new CancellationTokenSource();
        }

        void OnDestroy()
        {
            Disconnect();
        }

        /// <summary>
        /// Connect to WebSocket server
        /// </summary>
        public async void Connect(string simId)
        {
            if (IsConnected)
            {
                Debug.LogWarning("WebSocket already connected");
                return;
            }

            simulationId = simId;
            string url = $"{serverUrl}/ws/unity/{simulationId}";

            try
            {
                ws = new ClientWebSocket();
                await ws.ConnectAsync(new Uri(url), cancellationTokenSource.Token);

                isConnected = true;
                reconnectAttempts = 0;

                Debug.Log($"WebSocketClient: Connected to {url}");

                _ = ReceiveMessages();

                await SendMessage(BuildMessage("subscribe"));
                await SendMessage(BuildMessage("request_floor_plan"));
            }
            catch (Exception e)
            {
                Debug.LogError($"WebSocketClient: Connection failed: {e.Message}");
                isConnected = false;
                HandleReconnect();
            }
        }

        /// <summary>
        /// Disconnect from server
        /// </summary>
        public void Disconnect()
        {
            if (cancellationTokenSource != null)
            {
                cancellationTokenSource.Cancel();
            }

            if (ws != null)
            {
                if (ws.State == WebSocketState.Open)
                {
                    ws.CloseAsync(WebSocketCloseStatus.NormalClosure, "Client disconnect", CancellationToken.None);
                }
                ws.Dispose();
                ws = null;
            }

            isConnected = false;
            Debug.Log("WebSocketClient: Disconnected");
        }

        /// <summary>
        /// Receive messages from server
        /// </summary>
        private async Task ReceiveMessages()
        {
            var buffer = new byte[1024 * 4];

            while (IsConnected && !cancellationTokenSource.Token.IsCancellationRequested)
            {
                try
                {
                    var result = await ws.ReceiveAsync(new ArraySegment<byte>(buffer), cancellationTokenSource.Token);

                    if (result.MessageType == WebSocketMessageType.Text)
                    {
                        string message = Encoding.UTF8.GetString(buffer, 0, result.Count);
                        ProcessMessage(message);
                    }
                    else if (result.MessageType == WebSocketMessageType.Close)
                    {
                        Debug.Log("WebSocketClient: Server closed connection");
                        isConnected = false;
                        HandleReconnect();
                        break;
                    }
                }
                catch (Exception e)
                {
                    if (!cancellationTokenSource.Token.IsCancellationRequested)
                    {
                        Debug.LogError($"WebSocketClient: Receive error: {e.Message}");
                        isConnected = false;
                        HandleReconnect();
                    }
                    break;
                }
            }
        }

        /// <summary>
        /// Process received message
        /// </summary>
        private void ProcessMessage(string message)
        {
            try
            {
                var data = JsonUtility.FromJson<WebSocketMessage>(message);

                if (data.type == "ping")
                {
                    SendMessage(BuildMessage("pong"));
                    return;
                }

                lock (messageQueue)
                {
                    messageQueue.Enqueue(message);
                }
                OnMessageReceived?.Invoke(message);
            }
            catch (Exception e)
            {
                Debug.LogError($"WebSocketClient: Error processing message: {e.Message}");
            }
        }

        /// <summary>
        /// Process queued messages on main thread
        /// </summary>
        void Update()
        {
            lock (messageQueue)
            {
                while (messageQueue.Count > 0)
                {
                    string message = messageQueue.Dequeue();
                    HandleMessage(message);
                }
            }

            if (IsConnected && Time.time - lastFrameTime >= (1f / frameRate))
            {
                lastFrameTime = Time.time;
                SendSimulationFrame();
            }
        }

        /// <summary>
        /// Handle message based on type
        /// </summary>
        private void HandleMessage(string message)
        {
            try
            {
                var data = JsonUtility.FromJson<WebSocketMessage>(message);

                if (messageHandlers.ContainsKey(data.type))
                {
                    messageHandlers[data.type]?.Invoke(message);
                }

                switch (data.type)
                {
                    case "start_simulation":
                        if (SimulationManager.Instance != null)
                        {
                            var startMessage = JsonUtility.FromJson<SimulationStartMessage>(message);
                            if (startMessage != null && startMessage.config != null)
                            {
                                SimulationManager.Instance.StartSimulation(startMessage.config, simulationId);
                            }
                            else
                            {
                                var legacyConfig = JsonUtility.FromJson<LegacySimulationConfig>(message);
                                if (legacyConfig != null && legacyConfig.config != null)
                                {
                                    SimulationManager.Instance.StartSimulation(
                                        legacyConfig.config.num_agents,
                                        legacyConfig.config.emergency_type,
                                        simulationId
                                    );
                                }
                            }
                        }
                        break;

                    case "pause_simulation":
                        SimulationManager.Instance?.PauseSimulation();
                        break;

                    case "resume_simulation":
                        SimulationManager.Instance?.ResumeSimulation();
                        break;

                    case "stop_simulation":
                        SimulationManager.Instance?.StopSimulation();
                        break;

                    case "floor_plan_data":
                        HandleFloorPlanData(message);
                        break;

                    case "update_hazards":
                        HandleHazardUpdate(message);
                        break;

                    case "update_exits":
                        HandleExitUpdate(message);
                        break;

                    case "update_boundary":
                        HandleBoundaryUpdate(message);
                        break;
                }
            }
            catch (Exception e)
            {
                Debug.LogError($"WebSocketClient: Error handling message: {e.Message}");
            }
        }

        private void HandleFloorPlanData(string message)
        {
            try
            {
                var floorPlanData = JsonUtility.FromJson<FloorPlanMessage>(message);
                Debug.Log($"WebSocketClient: Received floor plan data for {floorPlanData.building_name}");

                if (SimulationManager.Instance != null)
                {
                    SimulationManager.Instance.ApplyFloorPlanData(floorPlanData);
                }

                if (SimulationManager.Instance != null && SimulationManager.Instance.floorPlanLoader != null)
                {
                    SimulationManager.Instance.floorPlanLoader.LoadFloorPlanData(floorPlanData);
                }
            }
            catch (Exception e)
            {
                Debug.LogError($"WebSocketClient: Error handling floor plan data: {e.Message}");
            }
        }

        private void HandleHazardUpdate(string message)
        {
            try
            {
                var update = JsonUtility.FromJson<HazardUpdateMessage>(message);
                if (SimulationManager.Instance != null && SimulationManager.Instance.HazardManager != null)
                {
                    SimulationManager.Instance.HazardManager.LoadHazards(update.hazards);
                }
            }
            catch (Exception e)
            {
                Debug.LogError($"WebSocketClient: Error handling hazard update: {e.Message}");
            }
        }

        private void HandleExitUpdate(string message)
        {
            try
            {
                var update = JsonUtility.FromJson<ExitUpdateMessage>(message);
                if (SimulationManager.Instance != null && SimulationManager.Instance.ExitManager != null)
                {
                    SimulationManager.Instance.ExitManager.LoadExits(update.exits);
                }
            }
            catch (Exception e)
            {
                Debug.LogError($"WebSocketClient: Error handling exit update: {e.Message}");
            }
        }

        private void HandleBoundaryUpdate(string message)
        {
            try
            {
                var update = JsonUtility.FromJson<BoundaryUpdateMessage>(message);
                if (SimulationManager.Instance != null && SimulationManager.Instance.BoundaryManager != null)
                {
                    SimulationManager.Instance.BoundaryManager.SetBoundary(update.boundary);
                }
            }
            catch (Exception e)
            {
                Debug.LogError($"WebSocketClient: Error handling boundary update: {e.Message}");
            }
        }

        private string BuildMessage(string type)
        {
            return $"{{\"type\":\"{type}\",\"simulation_id\":\"{simulationId}\",\"schema_version\":{schemaVersion}}}";
        }

        /// <summary>
        /// Send simulation frame with standardized schema
        /// </summary>
        private void SendSimulationFrame()
        {
            if (!IsConnected || SimulationManager.Instance == null) return;

            var frameData = new StandardizedFrameData
            {
                schema_version = schemaVersion,
                type = "simulation_update",
                simulation_id = simulationId,
                frame_id = Time.frameCount,
                timestamp = Time.time,
                floor_number = SimulationManager.Instance.currentFloorNumber,
                seed = 0,
                replay_id = "",
                hazard_state = "",
                agents = new List<StandardizedAgentData>(),
                bottlenecks = new List<StandardizedBottleneckData>(),
                hazards = new List<StandardizedHazardData>(),
                exit_usage = new List<StandardizedExitUsage>(),
                exit_evac_counts = new List<StandardizedExitEvacCount>(),
                profile_counts = new List<StandardizedProfileCount>(),
                stats = new StandardizedStats()
            };

            if (SimulationManager.Instance.agents.Count > 0)
            {
                foreach (var agent in SimulationManager.Instance.agents)
                {
                    if (agent != null)
                    {
                        var pos = agent.transform.position;
                        string profileId = "";
                        var advanced = agent.GetComponent<AdvancedAgentController>();
                        if (advanced != null && advanced.profile != null)
                        {
                            profileId = advanced.profile.id;
                        }

                        string targetExitId = "";
                        if (advanced != null)
                        {
                            targetExitId = advanced.CurrentExitId;
                        }
                        else if (agent.targetExit != null && SimulationManager.Instance.ExitManager != null)
                        {
                            targetExitId = SimulationManager.Instance.ExitManager.GetExitIdByTransform(agent.targetExit);
                        }

                        frameData.agents.Add(new StandardizedAgentData
                        {
                            agent_id = agent.GetInstanceID(),
                            x = pos.x,
                            y = pos.y,
                            z = pos.z,
                            speed = agent.GetCurrentSpeed(),
                            status = agent.GetStatus(),
                            profile_id = profileId,
                            panic_level = advanced != null ? advanced.panicLevel : agent.panicLevel,
                            stress_level = advanced != null ? advanced.stressLevel : 0f,
                            target_exit = targetExitId,
                            visibility = advanced != null ? advanced.visibility : 1f,
                            smoke_exposure = advanced != null ? advanced.smokeExposure : 0f
                        });
                    }
                }
            }
            else
            {
                foreach (var advanced in SimulationManager.Instance.advancedAgents)
                {
                    if (advanced == null) continue;
                    var pos = advanced.transform.position;
                    float speed = 0f;
                    var navAgent = advanced.GetComponent<UnityEngine.AI.NavMeshAgent>();
                    if (navAgent != null)
                    {
                        speed = navAgent.velocity.magnitude;
                    }

                    frameData.agents.Add(new StandardizedAgentData
                    {
                        agent_id = advanced.GetInstanceID(),
                        x = pos.x,
                        y = pos.y,
                        z = pos.z,
                        speed = speed,
                        status = advanced.IsEvacuated ? "evacuated" : "moving",
                        profile_id = advanced.profile != null ? advanced.profile.id : "",
                        panic_level = advanced.panicLevel,
                        stress_level = advanced.stressLevel,
                        target_exit = advanced.CurrentExitId,
                        visibility = advanced.visibility,
                        smoke_exposure = advanced.smokeExposure
                    });
                }
            }

            frameData.bottlenecks = DetectBottlenecks();

            if (SimulationManager.Instance.HazardManager != null)
            {
                foreach (var hazard in SimulationManager.Instance.HazardManager.GetSnapshots())
                {
                    frameData.hazards.Add(new StandardizedHazardData
                    {
                        hazard_id = hazard.hazard_id,
                        hazard_type = hazard.hazard_type,
                        x = hazard.x,
                        y = hazard.y,
                        z = hazard.z,
                        radius = hazard.radius,
                        intensity = hazard.intensity,
                        blocks_exits = hazard.blocks_exits
                    });
                }
            }

            if (SimulationManager.Instance.ExitManager != null)
            {
                foreach (var exit in SimulationManager.Instance.ExitManager.GetUsageSnapshots())
                {
                    frameData.exit_usage.Add(new StandardizedExitUsage
                    {
                        exit_id = exit.exit_id,
                        x = exit.x,
                        y = exit.y,
                        z = exit.z,
                        width = exit.width,
                        capacity = exit.capacity,
                        queue_length = exit.queue_length,
                        is_blocked = exit.is_blocked,
                        estimated_wait = exit.estimated_wait
                    });
                }
            }

            foreach (var profile in SimulationManager.Instance.GetProfileCounts())
            {
                frameData.profile_counts.Add(new StandardizedProfileCount
                {
                    profile_id = profile.profile_id,
                    count = profile.count
                });
            }

            foreach (var exitCount in SimulationManager.Instance.GetExitEvacCounts())
            {
                frameData.exit_evac_counts.Add(new StandardizedExitEvacCount
                {
                    exit_id = exitCount.exit_id,
                    count = exitCount.count
                });
            }

            var stats = SimulationManager.Instance.GetStats();
            frameData.stats = new StandardizedStats
            {
                total_agents = stats.totalAgents,
                evacuated = stats.evacuated,
                remaining = stats.remaining,
                elapsed_time = stats.elapsedTime,
                avg_speed = SimulationManager.Instance.AnalyticsManager != null ? SimulationManager.Instance.AnalyticsManager.averageSpeed : 0f,
                avg_panic = SimulationManager.Instance.AnalyticsManager != null ? SimulationManager.Instance.AnalyticsManager.averagePanic : 0f,
                avg_stress = SimulationManager.Instance.AnalyticsManager != null ? SimulationManager.Instance.AnalyticsManager.averageStress : 0f,
                hazard_exposure = SimulationManager.Instance.AnalyticsManager != null ? SimulationManager.Instance.AnalyticsManager.hazardExposure : 0f,
                congestion_index = SimulationManager.Instance.AnalyticsManager != null ? SimulationManager.Instance.AnalyticsManager.congestionIndex : 0f,
                evacuation_rate = stats.elapsedTime > 0 ? stats.evacuated / stats.elapsedTime : 0f
            };

            SendMessage(frameData);
        }

        private List<StandardizedBottleneckData> DetectBottlenecks()
        {
            var bottlenecks = new List<StandardizedBottleneckData>();
            var agents = SimulationManager.Instance.agents;
            bool useAdvanced = agents == null || agents.Count == 0;
            if (useAdvanced && (SimulationManager.Instance.advancedAgents == null || SimulationManager.Instance.advancedAgents.Count == 0))
            {
                return bottlenecks;
            }

            float cellSize = Mathf.Max(2f, SimulationManager.Instance.densityCellSize);
            Dictionary<Vector2Int, int> densityGrid = new Dictionary<Vector2Int, int>();

            if (!useAdvanced)
            {
                foreach (var agent in agents)
                {
                    if (agent == null || agent.GetStatus() == "evacuated") continue;

                    var pos = agent.transform.position;
                    var gridPos = new Vector2Int(
                        Mathf.FloorToInt(pos.x / cellSize),
                        Mathf.FloorToInt(pos.z / cellSize)
                    );

                    if (!densityGrid.ContainsKey(gridPos))
                        densityGrid[gridPos] = 0;
                    densityGrid[gridPos]++;
                }
            }
            else
            {
                foreach (var advanced in SimulationManager.Instance.advancedAgents)
                {
                    if (advanced == null || advanced.IsEvacuated) continue;
                    var pos = advanced.transform.position;
                    var gridPos = new Vector2Int(
                        Mathf.FloorToInt(pos.x / cellSize),
                        Mathf.FloorToInt(pos.z / cellSize)
                    );

                    if (!densityGrid.ContainsKey(gridPos))
                        densityGrid[gridPos] = 0;
                    densityGrid[gridPos]++;
                }
            }

            foreach (var kvp in densityGrid)
            {
                if (kvp.Value > 6)
                {
                    bottlenecks.Add(new StandardizedBottleneckData
                    {
                        x = kvp.Key.x * cellSize + cellSize / 2f,
                        y = 0f,
                        z = kvp.Key.y * cellSize + cellSize / 2f,
                        density = kvp.Value
                    });
                }
            }

            return bottlenecks;
        }

        /// <summary>
        /// Send raw JSON message to server
        /// </summary>
        public async Task SendMessage(string message)
        {
            if (!IsConnected) return;

            try
            {
                byte[] bytes = Encoding.UTF8.GetBytes(message);

                await ws.SendAsync(
                    new ArraySegment<byte>(bytes),
                    WebSocketMessageType.Text,
                    true,
                    cancellationTokenSource.Token
                );
            }
            catch (Exception e)
            {
                Debug.LogError($"WebSocketClient: Send error: {e.Message}");
                isConnected = false;
            }
        }

        /// <summary>
        /// Send message to server
        /// </summary>
        public async Task SendMessage(object data)
        {
            if (!IsConnected) return;

            try
            {
                string json = JsonUtility.ToJson(data);
                byte[] bytes = Encoding.UTF8.GetBytes(json);

                await ws.SendAsync(
                    new ArraySegment<byte>(bytes),
                    WebSocketMessageType.Text,
                    true,
                    cancellationTokenSource.Token
                );
            }
            catch (Exception e)
            {
                Debug.LogError($"WebSocketClient: Send error: {e.Message}");
                isConnected = false;
            }
        }

        /// <summary>
        /// Register message handler
        /// </summary>
        public void On(string eventType, Action<string> handler)
        {
            if (!messageHandlers.ContainsKey(eventType))
                messageHandlers[eventType] = handler;
            else
                messageHandlers[eventType] += handler;
        }

        /// <summary>
        /// Handle reconnection
        /// </summary>
        private void HandleReconnect()
        {
            if (reconnectAttempts >= maxReconnectAttempts)
            {
                Debug.LogError("WebSocketClient: Max reconnection attempts reached");
                return;
            }

            reconnectAttempts++;
            Debug.Log($"WebSocketClient: Reconnecting in {reconnectDelay}s (attempt {reconnectAttempts})");

            StartCoroutine(ReconnectCoroutine());
        }

        private System.Collections.IEnumerator ReconnectCoroutine()
        {
            yield return new WaitForSeconds(reconnectDelay);
            if (!string.IsNullOrEmpty(simulationId))
            {
                Connect(simulationId);
            }
        }

        // Data structures
        [System.Serializable]
        public class WebSocketMessage
        {
            public int schema_version;
            public string type;
            public string simulation_id;
        }

        [System.Serializable]
        private class LegacySimulationConfig
        {
            public string type;
            public LegacyConfigData config;
        }

        [System.Serializable]
        private class LegacyConfigData
        {
            public int num_agents;
            public string emergency_type;
            public float panic_level;
            public int seed;
            public int floor_number;
        }

        [System.Serializable]
        private class HazardUpdateMessage
        {
            public string type;
            public SimulationHazardConfig[] hazards;
        }

        [System.Serializable]
        private class ExitUpdateMessage
        {
            public string type;
            public SimulationExitConfig[] exits;
        }

        [System.Serializable]
        private class BoundaryUpdateMessage
        {
            public string type;
            public SimulationBoundary boundary;
        }

        [System.Serializable]
        public class StandardizedFrameData
        {
            public int schema_version;
            public string type;
            public string simulation_id;
            public int frame_id;
            public float timestamp;
            public int floor_number;
            public int seed;
            public string replay_id;
            public string hazard_state;
            public List<StandardizedAgentData> agents;
            public List<StandardizedBottleneckData> bottlenecks;
            public List<StandardizedHazardData> hazards;
            public List<StandardizedExitUsage> exit_usage;
            public List<StandardizedExitEvacCount> exit_evac_counts;
            public List<StandardizedProfileCount> profile_counts;
            public StandardizedStats stats;
        }

        [System.Serializable]
        public class StandardizedAgentData
        {
            public int agent_id;
            public float x;
            public float y;
            public float z;
            public float speed;
            public string status;
            public string profile_id;
            public float panic_level;
            public float stress_level;
            public string target_exit;
            public float visibility;
            public float smoke_exposure;
        }

        [System.Serializable]
        public class StandardizedBottleneckData
        {
            public float x;
            public float y;
            public float z;
            public int density;
        }

        [System.Serializable]
        public class StandardizedHazardData
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

        [System.Serializable]
        public class StandardizedExitUsage
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

        [System.Serializable]
        public class StandardizedExitEvacCount
        {
            public string exit_id;
            public int count;
        }

        [System.Serializable]
        public class StandardizedProfileCount
        {
            public string profile_id;
            public int count;
        }

        [System.Serializable]
        public class StandardizedStats
        {
            public int total_agents;
            public int evacuated;
            public int remaining;
            public float elapsed_time;
            public float avg_speed;
            public float avg_panic;
            public float avg_stress;
            public float hazard_exposure;
            public float congestion_index;
            public float evacuation_rate;
        }
    }
}
