using System;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;

namespace PeopleFlow.UnitySimulation.Managers
{
    [Obsolete("Legacy HTTP polling manager. Use WebSocketClient.")]
    public class WebSocketManager : MonoBehaviour
    {
        public static WebSocketManager Instance { get; private set; }

        [Header("Connection Settings")]
        public string serverUrl = "http://localhost:8000";
        public string simulationId = "";
        public float updateInterval = 0.1f;

        [Header("Status")]
        public bool connected = false;
        public bool isRunning = false;

        void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }
            Instance = this;
            DontDestroyOnLoad(gameObject);
        }

        public void Connect(string simId)
        {
            simulationId = simId;
            connected = true;
            isRunning = true;
            Debug.LogWarning("WebSocketManager is deprecated. Use WebSocketClient instead.");
        }

        public void Disconnect()
        {
            connected = false;
            isRunning = false;
        }

        public void SendCommand(string commandType)
        {
            Debug.LogWarning($"WebSocketManager deprecated command: {commandType}");
        }
    }
}
