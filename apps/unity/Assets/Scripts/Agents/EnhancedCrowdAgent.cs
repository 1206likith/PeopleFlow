using UnityEngine;
using UnityEngine.AI;
using System.Collections.Generic;

namespace PeopleFlow.UnitySimulation.Agents
{
    /// <summary>
    /// Enhanced Crowd Agent with body-based collision and social forces
    /// Integrates BodyCollision and SocialForces for realistic crowd behavior
    /// </summary>
    [RequireComponent(typeof(BodyCollision))]
    [RequireComponent(typeof(SocialForces))]
    public class EnhancedCrowdAgent : MonoBehaviour
    {
        [Header("Agent Settings")]
        public float baseSpeed = 1.4f;  // Base walking speed (m/s)
        public float panicSpeedMultiplier = 1.5f;  // Speed increase when panicked
        public Transform targetExit;
        
        [Header("Navigation")]
        public NavMeshAgent navAgent;
        public bool useNavMesh = true;
        public float navMeshUpdateInterval = 0.5f;  // Update NavMesh path every X seconds
        
        [Header("Behavior")]
        public float panicLevel = 0.0f;
        public float stressLevel = 0.0f;
        public string personality = "calm";
        public string populationProfile = "normal_adult";
        
        [Header("Dynamic Pathfinding")]
        public bool adaptivePathfinding = true;
        public float rerouteThreshold = 0.7f;  // Reroute if exit utilization > 70%
        public float rerouteCheckInterval = 2.0f;  // Check for reroute every X seconds
        public bool externalControl = false;
        
        private BodyCollision bodyCollision;
        private SocialForces socialForces;
        private Rigidbody rb;
        private float lastNavMeshUpdate = 0f;
        private float lastRerouteCheck = 0f;
        private List<Transform> availableExits = new List<Transform>();
        
        void Start()
        {
            // Get or add required components
            bodyCollision = GetComponent<BodyCollision>();
            if (bodyCollision == null)
            {
                bodyCollision = gameObject.AddComponent<BodyCollision>();
            }
            
            socialForces = GetComponent<SocialForces>();
            if (socialForces == null)
            {
                socialForces = gameObject.AddComponent<SocialForces>();
            }
            
            rb = GetComponent<Rigidbody>();
            if (rb == null)
            {
                rb = gameObject.AddComponent<Rigidbody>();
                rb.constraints = RigidbodyConstraints.FreezeRotationX | RigidbodyConstraints.FreezeRotationZ;
                rb.mass = 70f;
            }
            
            // Configure NavMesh agent
            if (navAgent == null)
            {
                navAgent = GetComponent<NavMeshAgent>();
            }
            
            if (navAgent != null)
            {
                navAgent.speed = baseSpeed;
                navAgent.acceleration = 8f;
                navAgent.angularSpeed = 360f;
                navAgent.stoppingDistance = 1.5f;
            }
            
            // Find all exits
            GameObject[] exitObjects = GameObject.FindGameObjectsWithTag("Exit");
            foreach (GameObject exit in exitObjects)
            {
                availableExits.Add(exit.transform);
            }
            
            // Set initial target
            if (targetExit == null && availableExits.Count > 0)
            {
                targetExit = FindNearestExit();
            }
        }
        
        void Update()
        {
            if (!externalControl)
            {
                var advancedController = GetComponent<AdvancedAgentController>();
                if (advancedController != null)
                {
                    externalControl = true;
                }
            }

            if (externalControl)
            {
                UpdateSocialBehavior();
                return;
            }

            // Update speed based on panic
            float currentSpeed = baseSpeed * (1.0f + panicLevel * panicSpeedMultiplier);
            
            if (navAgent != null && useNavMesh)
            {
                navAgent.speed = currentSpeed;
                
                // Update NavMesh path periodically
                if (Time.time - lastNavMeshUpdate > navMeshUpdateInterval)
                {
                    UpdateNavMeshPath();
                    lastNavMeshUpdate = Time.time;
                }
            }
            
            // Adaptive pathfinding - reroute if exit is congested
            if (adaptivePathfinding && Time.time - lastRerouteCheck > rerouteCheckInterval)
            {
                CheckAndReroute();
                lastRerouteCheck = Time.time;
            }
            
            // Update social forces based on personality
            UpdateSocialBehavior();
        }
        
        void FixedUpdate()
        {
            // Apply social forces (handled by SocialForces component)
            // Also apply manual movement if not using NavMesh
            if (!useNavMesh && targetExit != null)
            {
                MoveTowardsTarget();
            }
        }
        
        /// <summary>
        /// Update NavMesh path to target exit
        /// </summary>
        void UpdateNavMeshPath()
        {
            if (navAgent != null && targetExit != null)
            {
                navAgent.SetDestination(targetExit.position);
            }
        }
        
        /// <summary>
        /// Manual movement towards target (when not using NavMesh)
        /// </summary>
        void MoveTowardsTarget()
        {
            if (targetExit == null) return;
            
            Vector3 direction = (targetExit.position - transform.position).normalized;
            direction.y = 0;  // Keep on ground
            
            // Apply movement force
            float speed = baseSpeed * (1.0f + panicLevel * panicSpeedMultiplier);
            rb.AddForce(direction * speed * rb.mass, ForceMode.Force);
            
            // Rotate towards target
            if (direction.magnitude > 0.1f)
            {
                Quaternion targetRotation = Quaternion.LookRotation(direction);
                transform.rotation = Quaternion.Slerp(transform.rotation, targetRotation, Time.fixedDeltaTime * 5f);
            }
        }
        
        /// <summary>
        /// Check if exit is congested and reroute if needed
        /// Implements dynamic pathfinding adaptation
        /// </summary>
        void CheckAndReroute()
        {
            if (targetExit == null || availableExits.Count <= 1) return;
            
            // Count agents near current target exit
            int agentsNearExit = CountAgentsNearExit(targetExit);
            
            // Estimate exit utilization
            float exitWidth = 2.0f;  // Default, should come from exit data
            float flowCapacity = 1.33f * exitWidth;  // Research-validated flow rate
            float utilization = agentsNearExit / (flowCapacity * 10f);  // 10 second window
            
            // Reroute if exit is overloaded
            if (utilization > rerouteThreshold)
            {
                Transform alternativeExit = FindLessCongestedExit();
                if (alternativeExit != null && alternativeExit != targetExit)
                {
                    targetExit = alternativeExit;
                    if (navAgent != null)
                    {
                        navAgent.SetDestination(targetExit.position);
                    }
                }
            }
        }
        
        /// <summary>
        /// Count agents near a specific exit
        /// </summary>
        int CountAgentsNearExit(Transform exit)
        {
            int count = 0;
            float checkRadius = 5.0f;
            
            Collider[] colliders = Physics.OverlapSphere(exit.position, checkRadius);
            foreach (Collider col in colliders)
            {
                if (col.GetComponent<EnhancedCrowdAgent>() != null || 
                    col.GetComponent<CrowdAgent>() != null)
                {
                    count++;
                }
            }
            
            return count;
        }
        
        /// <summary>
        /// Find less congested exit
        /// </summary>
        Transform FindLessCongestedExit()
        {
            Transform bestExit = targetExit;
            int minAgents = int.MaxValue;
            
            foreach (Transform exit in availableExits)
            {
                int agents = CountAgentsNearExit(exit);
                if (agents < minAgents)
                {
                    minAgents = agents;
                    bestExit = exit;
                }
            }
            
            return bestExit;
        }
        
        /// <summary>
        /// Find nearest exit
        /// </summary>
        Transform FindNearestExit()
        {
            Transform nearest = null;
            float minDistance = float.MaxValue;
            
            foreach (Transform exit in availableExits)
            {
                float distance = Vector3.Distance(transform.position, exit.position);
                if (distance < minDistance)
                {
                    minDistance = distance;
                    nearest = exit;
                }
            }
            
            return nearest;
        }
        
        /// <summary>
        /// Update social behavior based on personality and panic
        /// </summary>
        void UpdateSocialBehavior()
        {
            if (socialForces == null) return;
            
            // Panic increases repulsion
            if (panicLevel > panicSpeedMultiplier)
            {
                socialForces.repulsionStrength = 2000f * (1.0f + panicLevel);
            }
            
            // Leader personality follows others
            if (personality == "leader")
            {
                socialForces.SetGroupFollowing(true);
            }
            
            // Panicked agents have stronger repulsion
            if (panicLevel > 0.6f)
            {
                socialForces.repulsionStrength = 3000f;
            }
        }
        
        /// <summary>
        /// Set target exit
        /// </summary>
        public void SetTargetExit(Transform exit)
        {
            targetExit = exit;
            if (navAgent != null)
            {
                navAgent.SetDestination(exit.position);
            }
        }
        
        /// <summary>
        /// Get panic level
        /// </summary>
        public float GetPanicLevel()
        {
            return panicLevel;
        }
        
        /// <summary>
        /// Set panic level
        /// </summary>
        public void SetPanicLevel(float level)
        {
            panicLevel = Mathf.Clamp01(level);
        }
        
        /// <summary>
        /// Get agent status
        /// </summary>
        public string GetStatus()
        {
            if (targetExit != null)
            {
                float distance = Vector3.Distance(transform.position, targetExit.position);
                if (distance < 2.0f)
                {
                    return "evacuated";
                }
            }
            
            if (panicLevel > 0.8f)
            {
                return "panicked";
            }
            
            return "moving";
        }
    }
}

