using System.Collections.Generic;
using UnityEngine;
using UnityEngine.AI;
using PeopleFlow.UnitySimulation.Agents;

namespace PeopleFlow.UnitySimulation.Managers
{
    /// <summary>
    /// Computes aggregate simulation analytics for research-grade reporting.
    /// </summary>
    public class SimulationAnalyticsManager : MonoBehaviour
    {
        [Header("Metrics")]
        public float averageSpeed;
        public float averagePanic;
        public float averageStress;
        public float hazardExposure;
        public float congestionIndex;

        public void UpdateMetrics(
            List<AdvancedAgentController> advancedAgents,
            List<CrowdAgent> agents,
            HazardManager hazardManager,
            float densityCellSize)
        {
            int total = 0;
            float speedSum = 0f;
            float panicSum = 0f;
            float stressSum = 0f;
            float hazardSum = 0f;

            Dictionary<Vector2Int, int> density = new Dictionary<Vector2Int, int>();
            float cellSize = Mathf.Max(1.5f, densityCellSize);

            if (advancedAgents != null && advancedAgents.Count > 0)
            {
                foreach (var agent in advancedAgents)
                {
                    if (agent == null || agent.IsEvacuated) continue;
                    total += 1;
                    var nav = agent.GetComponent<NavMeshAgent>();
                    if (nav != null)
                    {
                        speedSum += nav.velocity.magnitude;
                    }
                    panicSum += agent.panicLevel;
                    stressSum += agent.stressLevel;
                    if (hazardManager != null)
                    {
                        hazardSum += hazardManager.GetHazardIntensity(agent.transform.position);
                    }

                    Vector2Int cell = new Vector2Int(
                        Mathf.FloorToInt(agent.transform.position.x / cellSize),
                        Mathf.FloorToInt(agent.transform.position.z / cellSize)
                    );
                    if (!density.ContainsKey(cell)) density[cell] = 0;
                    density[cell] += 1;
                }
            }
            else if (agents != null)
            {
                foreach (var agent in agents)
                {
                    if (agent == null || agent.GetStatus() == "evacuated") continue;
                    total += 1;
                    speedSum += agent.GetCurrentSpeed();
                    panicSum += agent.panicLevel;
                    if (hazardManager != null)
                    {
                        hazardSum += hazardManager.GetHazardIntensity(agent.transform.position);
                    }

                    Vector2Int cell = new Vector2Int(
                        Mathf.FloorToInt(agent.transform.position.x / cellSize),
                        Mathf.FloorToInt(agent.transform.position.z / cellSize)
                    );
                    if (!density.ContainsKey(cell)) density[cell] = 0;
                    density[cell] += 1;
                }
            }

            if (total > 0)
            {
                averageSpeed = speedSum / total;
                averagePanic = panicSum / total;
                averageStress = stressSum / total;
                hazardExposure = hazardSum / total;
            }
            else
            {
                averageSpeed = 0f;
                averagePanic = 0f;
                averageStress = 0f;
                hazardExposure = 0f;
            }

            float congestion = 0f;
            foreach (var kvp in density)
            {
                congestion += kvp.Value * kvp.Value;
            }
            congestionIndex = total > 0 ? congestion / total : 0f;
        }
    }
}
