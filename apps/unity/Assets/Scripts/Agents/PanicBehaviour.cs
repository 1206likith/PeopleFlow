using UnityEngine;
using UnityEngine.AI;

namespace PeopleFlow.UnitySimulation.Agents
{
    /// <summary>
    /// Handles panic behavior - affects speed and decision making
    /// </summary>
    public class PanicBehaviour : MonoBehaviour
    {
        [Header("Panic Settings")]
        [Range(0f, 1f)] public float panicLevel = 0f;
        public float maxSpeedMultiplier = 2.0f;
        public float decisionQualityReduction = 0.4f;

        [Header("Social Influence")]
        public float socialInfluenceRadius = 5f;
        public float socialInfluenceStrength = 0.3f;

        private NavMeshAgent agent;
        private CrowdAgent crowdAgent;
        private float baseSpeed;

        void Awake()
        {
            agent = GetComponent<NavMeshAgent>();
            crowdAgent = GetComponent<CrowdAgent>();
            
            if (agent != null)
            {
                baseSpeed = agent.speed;
            }
        }

        void Update()
        {
            if (agent == null) return;
            if (crowdAgent != null && crowdAgent.useAdvancedBehavior) return;

            // Apply social influence (panic contagion)
            ApplySocialInfluence();

            // Update speed based on panic
            UpdateSpeedFromPanic();

            // Apply decision quality reduction
            if (panicLevel > 0.7f)
            {
                // High panic causes occasional random direction changes
                if (Random.value < 0.05f * panicLevel)
                {
                    AddRandomDeviation();
                }
            }
        }

        /// <summary>
        /// Apply social influence - agents near panicking agents also panic
        /// </summary>
        private void ApplySocialInfluence()
        {
            Collider[] nearbyAgents = Physics.OverlapSphere(transform.position, socialInfluenceRadius);
            
            float avgNearbyPanic = 0f;
            int count = 0;

            foreach (var collider in nearbyAgents)
            {
                PanicBehaviour otherPanic = collider.GetComponent<PanicBehaviour>();
                if (otherPanic != null && otherPanic != this)
                {
                    avgNearbyPanic += otherPanic.panicLevel;
                    count++;
                }
            }

            if (count > 0)
            {
                avgNearbyPanic /= count;
                float socialEffect = (avgNearbyPanic - panicLevel) * socialInfluenceStrength;
                panicLevel = Mathf.Clamp01(panicLevel + socialEffect * Time.deltaTime);
            }
        }

        /// <summary>
        /// Update speed based on panic level
        /// </summary>
        private void UpdateSpeedFromPanic()
        {
            if (agent == null) return;

            float speedMultiplier;
            
            if (panicLevel < 0.7f)
            {
                // Moderate panic increases speed
                speedMultiplier = 1f + panicLevel * (maxSpeedMultiplier - 1f);
            }
            else
            {
                // Extreme panic causes erratic movement
                speedMultiplier = maxSpeedMultiplier - (panicLevel - 0.7f) * 0.5f;
            }

            agent.speed = Mathf.Max(0.1f, baseSpeed * speedMultiplier);
        }

        /// <summary>
        /// Add random deviation to path (panic causes poor decisions)
        /// </summary>
        private void AddRandomDeviation()
        {
            if (agent == null || !agent.hasPath) return;

            Vector3 currentDirection = agent.desiredVelocity.normalized;
            Vector3 randomDeviation = new Vector3(
                Random.Range(-1f, 1f),
                0f,
                Random.Range(-1f, 1f)
            ).normalized * panicLevel;

            Vector3 newDirection = (currentDirection + randomDeviation).normalized;
            
            // Try to set new destination
            Vector3 newDestination = transform.position + newDirection * 5f;
            
            NavMeshHit hit;
            if (NavMesh.SamplePosition(newDestination, out hit, 2f, NavMesh.AllAreas))
            {
                agent.SetDestination(hit.position);
            }
        }

        /// <summary>
        /// Get decision quality (1.0 = perfect, 0.0 = terrible)
        /// </summary>
        public float GetDecisionQuality()
        {
            return 1f - (panicLevel * decisionQualityReduction);
        }

        /// <summary>
        /// Increase panic level
        /// </summary>
        public void IncreasePanic(float amount)
        {
            panicLevel = Mathf.Clamp01(panicLevel + amount);
        }

        /// <summary>
        /// Decrease panic level (calming down)
        /// </summary>
        public void DecreasePanic(float amount)
        {
            panicLevel = Mathf.Clamp01(panicLevel - amount);
        }
    }
}
