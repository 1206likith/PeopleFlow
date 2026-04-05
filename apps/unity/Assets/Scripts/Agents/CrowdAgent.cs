using UnityEngine;
using UnityEngine.AI;
using PeopleFlow.UnitySimulation.Agents;

namespace PeopleFlow.UnitySimulation.Agents
{
    /// <summary>
    /// Main agent behavior - handles movement, pathfinding, and evacuation
    /// </summary>
    [RequireComponent(typeof(NavMeshAgent))]
    public class CrowdAgent : MonoBehaviour
    {
        [Header("Movement")]
        public float baseSpeed = 3.5f;
        public float panicSpeedMultiplier = 1.5f;
        private NavMeshAgent navAgent;

        [Header("Target")]
        public Transform currentTarget;
        public Transform targetExit;

        [Header("Status")]
        public string status = "moving"; // moving, evacuated, stuck
        public bool hasEvacuated = false;
        public float panicLevel = 0f;
        public float distanceToDanger = 100f;
        public bool useAdvancedBehavior = false;

        [Header("Components")]
        private PanicBehaviour panicBehaviour;
        private ExitDetector exitDetector;
        private AdvancedAgentController advancedController;
        private TrailRenderer trailRenderer;
        private LineRenderer velocityVectorRenderer;
        private Renderer agentRenderer;

        void Awake()
        {
            navAgent = GetComponent<NavMeshAgent>();
            panicBehaviour = GetComponent<PanicBehaviour>();
            exitDetector = GetComponent<ExitDetector>();
            advancedController = GetComponent<AdvancedAgentController>();

            if (navAgent != null)
            {
                navAgent.speed = baseSpeed;
                navAgent.acceleration = 8f;
                navAgent.angularSpeed = 120f;
            }
        }

        void Start()
        {
            // Register with simulation manager
            if (SimulationManager.Instance != null)
            {
                SimulationManager.Instance.RegisterAgent(this);
            }

            // Setup Agent Trails
            trailRenderer = gameObject.AddComponent<TrailRenderer>();
            trailRenderer.time = 4.0f;
            trailRenderer.startWidth = 0.3f;
            trailRenderer.endWidth = 0.0f;
            trailRenderer.material = new Material(Shader.Find("Sprites/Default"));
            trailRenderer.startColor = new Color(0f, 1f, 1f, 0.4f);
            trailRenderer.endColor = new Color(0f, 0f, 1f, 0f);

            // Setup Velocity Vectors
            velocityVectorRenderer = gameObject.AddComponent<LineRenderer>();
            velocityVectorRenderer.startWidth = 0.08f;
            velocityVectorRenderer.endWidth = 0.02f;
            velocityVectorRenderer.material = new Material(Shader.Find("Sprites/Default"));
            velocityVectorRenderer.startColor = Color.yellow;
            velocityVectorRenderer.endColor = Color.red;
            velocityVectorRenderer.positionCount = 2;

            agentRenderer = GetComponentInChildren<Renderer>();
        }

        void Update()
        {
            if (useAdvancedBehavior)
            {
                if (advancedController == null)
                {
                    advancedController = GetComponent<AdvancedAgentController>();
                }
                if (advancedController != null)
                {
                    panicLevel = advancedController.panicLevel;
                    status = advancedController.IsEvacuated ? "evacuated" : "moving";
                    return;
                }
            }

            if (navAgent == null) return;

            // Update panic level based on distance to danger
            UpdatePanicLevel();

            // Update speed based on panic
            UpdateSpeed();

            // Navigate to exit
            if (status == "moving" && targetExit != null)
            {
                NavigateToExit();
            }

            // Check if reached exit
            CheckExitReached();

            // Update Visuals (Trails, Vectors, Colors)
            UpdateVisuals();
        }

        private void UpdateVisuals()
        {
            // Panic Color Coding (Blue -> Red)
            if (agentRenderer != null)
            {
                Color targetColor = Color.Lerp(Color.blue, Color.red, panicLevel);
                agentRenderer.material.color = Color.Lerp(agentRenderer.material.color, targetColor, Time.deltaTime * 5f);
            }

            // Velocity Vector Line
            if (velocityVectorRenderer != null && navAgent != null)
            {
                Vector3 startPos = transform.position + Vector3.up * 0.1f;
                // Scale vector by speed
                Vector3 endPos = startPos + navAgent.velocity.normalized * (navAgent.velocity.magnitude * 0.5f);
                if (navAgent.velocity.magnitude < 0.1f) endPos = startPos; // Hide if standing still
                velocityVectorRenderer.SetPosition(0, startPos);
                velocityVectorRenderer.SetPosition(1, endPos);
            }
        }

        /// <summary>
        /// Update panic level based on environment
        /// </summary>
        private void UpdatePanicLevel()
        {
            // Calculate panic based on distance to danger
            if (distanceToDanger < 10f)
            {
                panicLevel = Mathf.Lerp(panicLevel, 1f - (distanceToDanger / 10f), Time.deltaTime);
            }
            else
            {
                panicLevel = Mathf.Lerp(panicLevel, 0f, Time.deltaTime * 0.5f);
            }

            // Apply panic behavior
            if (panicBehaviour != null)
            {
                panicBehaviour.panicLevel = panicLevel;
            }
        }

        /// <summary>
        /// Update agent speed based on panic
        /// </summary>
        private void UpdateSpeed()
        {
            if (navAgent == null) return;

            float speedMultiplier = 1f;
            
            if (panicLevel < 0.7f)
            {
                // Moderate panic increases speed
                speedMultiplier = 1f + panicLevel * 0.5f;
            }
            else
            {
                // Extreme panic causes erratic movement (reduced effective speed)
                speedMultiplier = 1.35f - (panicLevel - 0.7f) * 0.5f;
            }

            navAgent.speed = baseSpeed * speedMultiplier;
        }

        /// <summary>
        /// Navigate to assigned exit
        /// </summary>
        private void NavigateToExit()
        {
            if (targetExit == null || navAgent == null) return;

            // Check if we need to recalculate path
            if (!navAgent.hasPath || navAgent.remainingDistance < 0.1f || navAgent.pathStatus != NavMeshPathStatus.PathComplete)
            {
                navAgent.SetDestination(targetExit.position);
            }

            // Add some randomness if panicking
            if (panicLevel > 0.5f && Random.value < 0.1f)
            {
                Vector3 randomOffset = new Vector3(
                    Random.Range(-1f, 1f),
                    0f,
                    Random.Range(-1f, 1f)
                ) * panicLevel;
                Vector3 newDestination = targetExit.position + randomOffset;
                
                NavMeshHit hit;
                if (NavMesh.SamplePosition(newDestination, out hit, 2f, NavMesh.AllAreas))
                {
                    navAgent.SetDestination(hit.position);
                }
            }
        }

        /// <summary>
        /// Check if agent reached exit
        /// </summary>
        private void CheckExitReached()
        {
            if (targetExit == null || status == "evacuated") return;

            float distanceToExit = Vector3.Distance(transform.position, targetExit.position);
            
            if (distanceToExit < 2f) // Exit reached
            {
                status = "evacuated";
                hasEvacuated = true;
                
                if (navAgent != null)
                {
                    navAgent.isStopped = true;
                }

                // Unregister from simulation
                if (SimulationManager.Instance != null)
                {
                    SimulationManager.Instance.NotifyEvacuated(this, targetExit);
                    SimulationManager.Instance.UnregisterAgent(this);
                }
            }
        }

        /// <summary>
        /// Set target exit
        /// </summary>
        public void SetTargetExit(Transform exit)
        {
            targetExit = exit;
            currentTarget = exit;
            
            if (navAgent != null && exit != null)
            {
                navAgent.SetDestination(exit.position);
            }
        }

        /// <summary>
        /// Set destination manually
        /// </summary>
        public void SetDestination(Vector3 position)
        {
            if (navAgent != null)
            {
                navAgent.SetDestination(position);
            }
        }

        /// <summary>
        /// Set speed multiplier
        /// </summary>
        public void SetSpeedMultiplier(float multiplier)
        {
            if (navAgent != null)
            {
                navAgent.speed = Mathf.Max(0.1f, baseSpeed * Mathf.Max(0f, multiplier));
            }
        }

        /// <summary>
        /// Get current speed
        /// </summary>
        public float GetCurrentSpeed()
        {
            if (navAgent != null)
            {
                return navAgent.velocity.magnitude;
            }
            return 0f;
        }

        /// <summary>
        /// Get current status
        /// </summary>
        public string GetStatus()
        {
            if (useAdvancedBehavior && advancedController != null)
            {
                return advancedController.IsEvacuated ? "evacuated" : "moving";
            }

            if (navAgent != null && !navAgent.hasPath && status == "moving")
            {
                status = "stuck";
            }
            return status;
        }

        /// <summary>
        /// Set distance to danger (for panic calculation)
        /// </summary>
        public void SetDistanceToDanger(float distance)
        {
            distanceToDanger = distance;
        }

        void OnDestroy()
        {
            if (SimulationManager.Instance != null)
            {
                SimulationManager.Instance.UnregisterAgent(this);
            }
        }
    }
}
