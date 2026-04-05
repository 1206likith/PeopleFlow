using UnityEngine;

namespace PeopleFlow.UnitySimulation.Managers
{
    /// <summary>
    /// Controller that receives commands from backend and controls simulation
    /// </summary>
    public class SimulationController : MonoBehaviour
    {
        [Header("References")]
        public SimulationManager simulationManager;

        void Start()
        {
            if (simulationManager == null)
                simulationManager = FindObjectOfType<SimulationManager>();
        }

        public void StartSimulation(int numAgents, string emergencyType, string simId)
        {
            if (simulationManager != null)
            {
                simulationManager.StartSimulation(numAgents, emergencyType, simId);
            }
        }

        public void PauseSimulation()
        {
            if (simulationManager != null)
            {
                simulationManager.PauseSimulation();
            }
        }

        public void ResumeSimulation()
        {
            if (simulationManager != null)
            {
                simulationManager.ResumeSimulation();
            }
        }

        public void StopSimulation()
        {
            if (simulationManager != null)
            {
                simulationManager.StopSimulation();
            }
        }
    }
}
