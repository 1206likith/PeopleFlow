using System.Collections.Generic;
using System.IO;
using UnityEngine;
using PeopleFlow.UnitySimulation.Agents;
using PeopleFlow.UnitySimulation.Managers;

namespace PeopleFlow.UnitySimulation.Managers
{
    /// <summary>
    /// Exports simulation data to JSON format for backend processing
    /// </summary>
    public class DataExporter : MonoBehaviour
    {
        [System.Serializable]
        public class AgentSnapshot
        {
            public int agent_id;
            public float x;
            public float y;
            public float z;
            public float speed;
            public string status;
            public float panic_level;
            public float stress_level;
            public string profile_id;
            public string target_exit;
            public float visibility;
            public float smoke_exposure;
        }

        [System.Serializable]
        public class FrameData
        {
            public float time;
            public List<AgentSnapshot> agents;
            public List<BottleneckData> bottlenecks;
            public List<HazardManager.HazardSnapshot> hazards;
            public List<ExitManager.ExitUsageSnapshot> exit_usage;
            public List<SimulationManager.ProfileCountSnapshot> profile_counts;
            public List<SimulationManager.ExitEvacCountSnapshot> exit_evac_counts;
        }

        [System.Serializable]
        public class BottleneckData
        {
            public float x;
            public float y;
            public float z;
            public int density;
        }

        [Header("Export Settings")]
        public bool autoExport = true;
        public float exportInterval = 0.1f; // 10 FPS
        public string exportPath = "SimulationData";

        private float lastExportTime = 0f;

        void Update()
        {
            if (autoExport && SimulationManager.Instance != null && SimulationManager.Instance.isRunning)
            {
                if (Time.time - lastExportTime >= exportInterval)
                {
                    lastExportTime = Time.time;
                    ExportCurrentFrame();
                }
            }
        }

        /// <summary>
        /// Export current frame data
        /// </summary>
        public void ExportCurrentFrame()
        {
            var frameData = CollectFrameData();
            string json = JsonUtility.ToJson(frameData, true);
            
            // Save to file (optional - mainly for debugging)
            if (!string.IsNullOrEmpty(exportPath))
            {
                string filePath = Path.Combine(Application.persistentDataPath, exportPath, 
                    $"frame_{Mathf.RoundToInt(Time.time * 1000f)}.json");
                Directory.CreateDirectory(Path.GetDirectoryName(filePath));
                File.WriteAllText(filePath, json);
            }
        }

        /// <summary>
        /// Collect current frame data from simulation
        /// </summary>
        public FrameData CollectFrameData()
        {
            var frameData = new FrameData
            {
                time = Time.time,
                agents = new List<AgentSnapshot>(),
                bottlenecks = new List<BottleneckData>(),
                hazards = new List<HazardManager.HazardSnapshot>(),
                exit_usage = new List<ExitManager.ExitUsageSnapshot>(),
                profile_counts = new List<SimulationManager.ProfileCountSnapshot>(),
                exit_evac_counts = new List<SimulationManager.ExitEvacCountSnapshot>()
            };

            // Collect agent data
            if (SimulationManager.Instance != null)
            {
                foreach (var agent in SimulationManager.Instance.agents)
                {
                    if (agent != null)
                    {
                        var pos = agent.transform.position;
                        var advanced = agent.GetComponent<AdvancedAgentController>();
                        string profileId = advanced != null && advanced.profile != null ? advanced.profile.id : "";
                        string targetExitId = advanced != null ? advanced.CurrentExitId : "";
                        if (string.IsNullOrEmpty(targetExitId) && SimulationManager.Instance.ExitManager != null && agent.targetExit != null)
                        {
                            targetExitId = SimulationManager.Instance.ExitManager.GetExitIdByTransform(agent.targetExit);
                        }

                        frameData.agents.Add(new AgentSnapshot
                        {
                            agent_id = agent.GetInstanceID(),
                            x = pos.x,
                            y = pos.y,
                            z = pos.z,
                            speed = agent.GetCurrentSpeed(),
                            status = agent.GetStatus(),
                            panic_level = advanced != null ? advanced.panicLevel : agent.panicLevel,
                            stress_level = advanced != null ? advanced.stressLevel : 0f,
                            profile_id = profileId,
                            target_exit = targetExitId,
                            visibility = advanced != null ? advanced.visibility : 1f,
                            smoke_exposure = advanced != null ? advanced.smokeExposure : 0f
                        });
                    }
                }
            }

            // Detect bottlenecks
            frameData.bottlenecks = DetectBottlenecks();

            if (SimulationManager.Instance != null)
            {
                if (SimulationManager.Instance.HazardManager != null)
                {
                    frameData.hazards = SimulationManager.Instance.HazardManager.GetSnapshots();
                }
                if (SimulationManager.Instance.ExitManager != null)
                {
                    frameData.exit_usage = SimulationManager.Instance.ExitManager.GetUsageSnapshots();
                }
                frameData.profile_counts = SimulationManager.Instance.GetProfileCounts();
                frameData.exit_evac_counts = SimulationManager.Instance.GetExitEvacCounts();
            }

            return frameData;
        }

        /// <summary>
        /// Detect bottlenecks (high-density areas)
        /// </summary>
        private List<BottleneckData> DetectBottlenecks()
        {
            var bottlenecks = new List<BottleneckData>();

            if (SimulationManager.Instance == null) return bottlenecks;

            var agents = SimulationManager.Instance.agents;
            if (agents == null || agents.Count == 0) return bottlenecks;

            // Grid-based density calculation
            float cellSize = 5f;
            Dictionary<Vector2Int, int> densityGrid = new Dictionary<Vector2Int, int>();

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

            // Find high-density cells (bottlenecks)
            foreach (var kvp in densityGrid)
            {
                if (kvp.Value > 8) // Threshold
                {
                    bottlenecks.Add(new BottleneckData
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
        /// Export simulation summary
        /// </summary>
        public void ExportSummary()
        {
            if (SimulationManager.Instance == null) return;

            var stats = SimulationManager.Instance.GetStats();
            string json = JsonUtility.ToJson(stats, true);

            string filePath = Path.Combine(Application.persistentDataPath, exportPath, "summary.json");
            Directory.CreateDirectory(Path.GetDirectoryName(filePath));
            File.WriteAllText(filePath, json);

            Debug.Log($"Simulation summary exported to: {filePath}");
        }
    }
}
