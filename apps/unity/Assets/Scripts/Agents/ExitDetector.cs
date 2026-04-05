using UnityEngine;

namespace PeopleFlow.UnitySimulation.Agents
{
    /// <summary>
    /// Detects when agent reaches an exit
    /// </summary>
    public class ExitDetector : MonoBehaviour
    {
        [Header("Settings")]
        public float detectionRadius = 2f;
        public string exitTag = "Exit";

        private CrowdAgent agent;

        void Start()
        {
            agent = GetComponent<CrowdAgent>();
        }

        void Update()
        {
            if (agent == null || agent.GetStatus() == "evacuated") return;
            if (agent.useAdvancedBehavior) return;

            // Check for nearby exits
            Collider[] colliders = Physics.OverlapSphere(transform.position, detectionRadius);
            
            foreach (var collider in colliders)
            {
                if (collider.CompareTag(exitTag))
                {
                    // Reached exit
                    if (agent != null)
                    {
                        agent.status = "evacuated";
                        agent.hasEvacuated = true;
                        if (PeopleFlow.UnitySimulation.Managers.SimulationManager.Instance != null)
                        {
                            PeopleFlow.UnitySimulation.Managers.SimulationManager.Instance.NotifyEvacuated(agent, collider.transform);
                        }
                    }
                    break;
                }
            }
        }

        void OnDrawGizmosSelected()
        {
            // Draw detection radius
            Gizmos.color = Color.yellow;
            Gizmos.DrawWireSphere(transform.position, detectionRadius);
        }
    }
}
