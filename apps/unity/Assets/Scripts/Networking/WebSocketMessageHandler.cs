using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using UnityEngine;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace PeopleFlow.UnitySimulation.Networking
{
    /// <summary>
    /// Handles WebSocket messages and dispatches them to appropriate handlers
    /// </summary>
    [Obsolete("Legacy handler. Prefer Managers.WebSocketClient with unified contracts.")]
    public class WebSocketMessageHandler : MonoBehaviour
    {
        [Header("Dependencies")]
        [SerializeField] private WebSocketClient webSocketClient;
        
        // Message type constants
        private const string MESSAGE_TYPE_SIMULATION_STATE = "simulation_state";
        private const string MESSAGE_TYPE_AGENT_UPDATE = "agent_update";
        private const string MESSAGE_TYPE_SIMULATION_CONTROL = "simulation_control";
        private const string MESSAGE_TYPE_ERROR = "error";
        private const string MESSAGE_TYPE_PONG = "pong";

        // Event definitions
        public event Action<SimulationState> OnSimulationStateUpdated;
        public event Action<List<AgentUpdate>> OnAgentUpdatesReceived;
        public event Action<string, string> OnSimulationControlReceived; // command, data
        public event Action<string> OnErrorReceived;

        private void OnEnable()
        {
            if (webSocketClient == null)
            {
                webSocketClient = GetComponent<WebSocketClient>();
            }

            if (webSocketClient != null)
            {
                webSocketClient.OnMessageReceived += HandleMessage;
            }
        }

        private void OnDisable()
        {
            if (webSocketClient != null)
            {
                webSocketClient.OnMessageReceived -= HandleMessage;
            }
        }

        private void HandleMessage(string message)
        {
            try
            {
                var json = JObject.Parse(message);
                var messageType = json["type"]?.ToString();

                switch (messageType)
                {
                    case MESSAGE_TYPE_SIMULATION_STATE:
                        var state = json.ToObject<SimulationState>();
                        OnSimulationStateUpdated?.Invoke(state);
                        break;
                        
                    case MESSAGE_TYPE_AGENT_UPDATE:
                        var updates = json["agents"]?.ToObject<List<AgentUpdate>>();
                        if (updates != null)
                        {
                            OnAgentUpdatesReceived?.Invoke(updates);
                        }
                        break;
                        
                    case MESSAGE_TYPE_SIMULATION_CONTROL:
                        var command = json["command"]?.ToString();
                        var data = json["data"]?.ToString();
                        if (!string.IsNullOrEmpty(command))
                        {
                            OnSimulationControlReceived?.Invoke(command, data);
                        }
                        break;
                        
                    case MESSAGE_TYPE_ERROR:
                        var errorMsg = json["message"]?.ToString() ?? "Unknown error";
                        OnErrorReceived?.Invoke(errorMsg);
                        break;
                        
                    case MESSAGE_TYPE_PONG:
                        // Handle pong response
                        break;
                        
                    default:
                        Debug.LogWarning($"Unknown message type: {messageType}");
                        break;
                }
            }
            catch (JsonReaderException ex)
            {
                Debug.LogError($"Error parsing WebSocket message: {ex.Message}");
            }
            catch (Exception ex)
            {
                Debug.LogError($"Error handling WebSocket message: {ex.Message}");
            }
        }

        public async Task SendPing()
        {
            var pingMessage = new JObject
            {
                ["type"] = "ping",
                ["timestamp"] = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()
            };
            
            await webSocketClient.SendMessage(pingMessage.ToString());
        }

        public async Task SendSimulationCommand(string command, object data = null)
        {
            var message = new JObject
            {
                ["type"] = "simulation_command",
                ["command"] = command,
                ["timestamp"] = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()
            };

            if (data != null)
            {
                message["data"] = JToken.FromObject(data);
            }

            await webSocketClient.SendMessage(message.ToString());
        }
    }

    #region Data Models

    [Serializable]
    public class SimulationState
    {
        public string simulation_id;
        public string status; // "running", "paused", "completed", "error"
        public float simulation_time;
        public int agent_count;
        public Dictionary<string, object> metadata;
    }

    [Serializable]
    public class AgentUpdate
    {
        public string agent_id;
        public Vector3 position;
        public Vector3 velocity;
        public string state;
        public Dictionary<string, object> metadata;
    }

    #endregion
}
