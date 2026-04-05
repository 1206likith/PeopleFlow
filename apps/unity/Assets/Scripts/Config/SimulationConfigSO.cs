using UnityEngine;

namespace PeopleFlow.UnitySimulation.Config
{
    /// <summary>
    /// ScriptableObject for simulation configuration
    /// Allows easy configuration without code changes
    /// </summary>
    [CreateAssetMenu(fileName = "SimulationConfig", menuName = "PeopleFlow/Simulation Config")]
    public class SimulationConfigSO : ScriptableObject
    {
        [Header("Server Configuration")]
        [Tooltip("Backend API server URL")]
        public string serverUrl = "http://localhost:8000";
        
        [Tooltip("WebSocket server URL")]
        public string websocketUrl = "ws://localhost:8000";
        
        [Tooltip("Authentication token (if required)")]
        public string authToken = "";
        
        [Header("Simulation Settings")]
        [Tooltip("Target frame rate for simulation updates")]
        [Range(1, 60)]
        public float frameRate = 10f;
        
        [Tooltip("Deterministic timestep for reproducible simulations")]
        public bool useFixedTimestep = true;
        
        [Tooltip("Fixed timestep value (seconds)")]
        [Range(0.01f, 0.1f)]
        public float fixedTimestep = 0.02f;
        
        [Header("WebSocket Settings")]
        [Tooltip("Reconnection delay in seconds")]
        public float reconnectDelay = 2f;
        
        [Tooltip("Maximum reconnection attempts")]
        [Range(1, 10)]
        public int maxReconnectAttempts = 5;
        
        [Header("Schema Version")]
        [Tooltip("Frame data schema version")]
        public int schemaVersion = 1;
        
        [Header("Performance")]
        [Tooltip("Maximum agents to render")]
        [Range(100, 10000)]
        public int maxAgentsRender = 1000;
        
        [Tooltip("Enable NavMesh per floor")]
        public bool enableMultiFloorNavMesh = true;
        
        /// <summary>
        /// Get WebSocket URL
        /// </summary>
        public string GetWebSocketUrl()
        {
            return websocketUrl;
        }
        
        /// <summary>
        /// Get API URL
        /// </summary>
        public string GetApiUrl()
        {
            return serverUrl;
        }
        
        /// <summary>
        /// Validate configuration
        /// </summary>
        public bool Validate()
        {
            if (string.IsNullOrEmpty(serverUrl))
            {
                Debug.LogError("SimulationConfig: serverUrl is required");
                return false;
            }
            
            if (string.IsNullOrEmpty(websocketUrl))
            {
                Debug.LogError("SimulationConfig: websocketUrl is required");
                return false;
            }
            
            if (frameRate <= 0)
            {
                Debug.LogError("SimulationConfig: frameRate must be positive");
                return false;
            }
            
            return true;
        }
    }
}

