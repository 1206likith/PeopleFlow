using System.Collections.Generic;
using UnityEngine;
using PeopleFlow.UnitySimulation.Agents;

namespace PeopleFlow.UnitySimulation.Managers
{
    /// <summary>
    /// Records agent traces for research replay and analysis.
    /// </summary>
    public class AgentTraceRecorder : MonoBehaviour
    {
        public bool recordTraces = true;
        public int maxAgents = 50;
        public float sampleInterval = 0.5f;
        public int maxSamplesPerAgent = 2000;

        private float lastSampleTime = 0f;
        private readonly Dictionary<int, List<Vector3>> traces = new Dictionary<int, List<Vector3>>();

        public void Capture(List<AdvancedAgentController> advancedAgents, List<CrowdAgent> agents)
        {
            if (!recordTraces) return;
            if (Time.time - lastSampleTime < sampleInterval) return;
            lastSampleTime = Time.time;

            int recorded = 0;

            if (advancedAgents != null && advancedAgents.Count > 0)
            {
                foreach (var agent in advancedAgents)
                {
                    if (agent == null || agent.IsEvacuated) continue;
                    if (recorded >= maxAgents) break;
                    RecordSample(agent.GetInstanceID(), agent.transform.position);
                    recorded += 1;
                }
            }
            else if (agents != null)
            {
                foreach (var agent in agents)
                {
                    if (agent == null || agent.GetStatus() == "evacuated") continue;
                    if (recorded >= maxAgents) break;
                    RecordSample(agent.GetInstanceID(), agent.transform.position);
                    recorded += 1;
                }
            }
        }

        private void RecordSample(int id, Vector3 position)
        {
            if (!traces.ContainsKey(id))
            {
                traces[id] = new List<Vector3>();
            }

            if (traces[id].Count >= maxSamplesPerAgent) return;
            traces[id].Add(position);
        }

        public Dictionary<int, List<Vector3>> GetTraces()
        {
            return traces;
        }

        public void Clear()
        {
            traces.Clear();
        }
    }
}
