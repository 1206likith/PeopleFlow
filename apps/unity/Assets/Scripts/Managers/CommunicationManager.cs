using System.Collections.Generic;
using UnityEngine;
using PeopleFlow.UnitySimulation.Agents;

namespace PeopleFlow.UnitySimulation.Managers
{
    /// <summary>
    /// Shares exit recommendations from staff/leaders to nearby agents.
    /// </summary>
    public class CommunicationManager : MonoBehaviour
    {
        [Header("Broadcast Settings")]
        public float broadcastInterval = 2f;
        public float influenceRadius = 10f;
        public float complianceThreshold = 0.4f;
        public float panicOverrideThreshold = 0.85f;
        public bool includeLeaders = true;

        private float lastBroadcastTime = 0f;

        public void BroadcastRecommendations(
            List<AdvancedAgentController> agents,
            ExitManager exitManager,
            HazardManager hazardManager)
        {
            if (agents == null || agents.Count == 0 || exitManager == null) return;

            if (Time.time - lastBroadcastTime < broadcastInterval)
            {
                return;
            }

            lastBroadcastTime = Time.time;

            foreach (var source in agents)
            {
                if (source == null || source.IsEvacuated || source.profile == null) continue;

                bool canBroadcast = source.profile.staff || (includeLeaders && source.isLeader);
                if (!canBroadcast) continue;

                var suggestedExit = exitManager.GetBestExit(source.profile, source.transform.position, hazardManager, source.panicLevel);
                if (suggestedExit == null) continue;

                foreach (var target in agents)
                {
                    if (target == null || target == source || target.IsEvacuated) continue;
                    if (target.profile == null || target.profile.compliance < complianceThreshold) continue;
                    if (target.panicLevel > panicOverrideThreshold) continue;

                    float distance = Vector3.Distance(source.transform.position, target.transform.position);
                    if (distance <= influenceRadius)
                    {
                        target.ApplyRecommendation(suggestedExit.id);
                    }
                }
            }
        }
    }
}
