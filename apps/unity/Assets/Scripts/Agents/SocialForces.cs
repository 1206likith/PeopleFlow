using System.Collections.Generic;
using UnityEngine;

namespace PeopleFlow.UnitySimulation.Agents
{
    /// <summary>
    /// Social Force Model for realistic crowd behavior
    /// Implements pushing forces, interpersonal repulsion, and group cohesion
    /// Based on research: Helbing & Molnar's Social Force Model
    /// </summary>
    public class SocialForces : MonoBehaviour
    {
        [Header("Social Force Parameters")]
        public float repulsionStrength = 2000f;  // Strength of repulsion between agents
        public float repulsionRange = 1.5f;  // Range of repulsion in meters
        public float attractionStrength = 500f;  // Strength of attraction to group/family
        public float attractionRange = 5.0f;  // Range of attraction
        
        [Header("Group Behavior")]
        public bool followGroup = true;
        public float groupCohesionStrength = 300f;
        public float groupAlignmentStrength = 200f;
        public List<Transform> groupMembers = new List<Transform>();  // Family/group members
        
        [Header("Leader Following")]
        public bool followLeader = false;
        public Transform leader = null;
        public float leaderFollowStrength = 400f;
        public float leaderFollowDistance = 3.0f;
        
        [Header("Panic Behavior")]
        public float panicMultiplier = 1.5f;  // Increases forces when panicked
        public float panicThreshold = 0.6f;  // Panic level threshold
        
        private Rigidbody rb;
        private BodyCollision bodyCollision;
        private CrowdAgent crowdAgent;
        private List<SocialForces> nearbyAgents = new List<SocialForces>();
        
        void Start()
        {
            rb = GetComponent<Rigidbody>();
            bodyCollision = GetComponent<BodyCollision>();
            crowdAgent = GetComponent<CrowdAgent>();
            
            if (rb == null)
            {
                rb = gameObject.AddComponent<Rigidbody>();
            }
        }
        
        void Update()
        {
            // Find nearby agents
            FindNearbyAgents();
        }
        
        void FixedUpdate()
        {
            // Apply social forces in FixedUpdate for physics consistency
            Vector3 socialForce = CalculateSocialForces();
            
            if (rb != null && socialForce.magnitude > 0.01f)
            {
                rb.AddForce(socialForce, ForceMode.Force);
            }
        }
        
        void FindNearbyAgents()
        {
            nearbyAgents.Clear();
            Collider[] colliders = Physics.OverlapSphere(transform.position, repulsionRange * 2f);
            
            foreach (Collider col in colliders)
            {
                if (col.gameObject != gameObject)
                {
                    SocialForces otherAgent = col.GetComponent<SocialForces>();
                    if (otherAgent != null)
                    {
                        nearbyAgents.Add(otherAgent);
                    }
                }
            }
        }
        
        /// <summary>
        /// Calculate total social forces acting on this agent
        /// Combines repulsion, attraction, group cohesion, and leader following
        /// </summary>
        public Vector3 CalculateSocialForces()
        {
            Vector3 totalForce = Vector3.zero;
            
            // Get panic level from agent
            float panicLevel = crowdAgent != null ? crowdAgent.GetPanicLevel() : 0f;
            float forceMultiplier = 1.0f + (panicLevel * panicMultiplier);
            
            // Interpersonal repulsion (avoid collisions)
            totalForce += CalculateRepulsionForces() * forceMultiplier;
            
            // Group cohesion (stay with family/group)
            if (followGroup && groupMembers.Count > 0)
            {
                totalForce += CalculateGroupCohesion() * forceMultiplier;
            }
            
            // Leader following
            if (followLeader && leader != null)
            {
                totalForce += CalculateLeaderFollowing() * forceMultiplier;
            }
            
            // Body collision repulsion (from BodyCollision component)
            if (bodyCollision != null)
            {
                totalForce += bodyCollision.GetRepulsionForce() * forceMultiplier;
            }
            
            return totalForce;
        }
        
        /// <summary>
        /// Calculate repulsion forces from nearby agents
        /// Implements exponential decay based on distance
        /// </summary>
        private Vector3 CalculateRepulsionForces()
        {
            Vector3 repulsion = Vector3.zero;
            
            foreach (SocialForces otherAgent in nearbyAgents)
            {
                Vector3 direction = transform.position - otherAgent.transform.position;
                float distance = direction.magnitude;
                
                if (distance < repulsionRange && distance > 0.01f)
                {
                    direction.Normalize();
                    
                    // Exponential decay: stronger when closer
                    float forceMagnitude = repulsionStrength * Mathf.Exp(-distance / repulsionRange);
                    
                    // Add body overlap factor if available
                    if (bodyCollision != null && otherAgent.bodyCollision != null)
                    {
                        // Body overlap is handled by BodyCollision component separately
                        // Social forces add additional repulsion on top
                    }
                    
                    repulsion += direction * forceMagnitude;
                }
            }
            
            return repulsion;
        }
        
        /// <summary>
        /// Calculate group cohesion force
        /// Keeps family/group members together
        /// </summary>
        private Vector3 CalculateGroupCohesion()
        {
            Vector3 cohesion = Vector3.zero;
            Vector3 groupCenter = Vector3.zero;
            int validMembers = 0;
            
            foreach (Transform member in groupMembers)
            {
                if (member != null && member != transform)
                {
                    float distance = Vector3.Distance(transform.position, member.position);
                    if (distance < attractionRange)
                    {
                        groupCenter += member.position;
                        validMembers++;
                    }
                }
            }
            
            if (validMembers > 0)
            {
                groupCenter /= validMembers;
                Vector3 direction = (groupCenter - transform.position).normalized;
                float distance = Vector3.Distance(transform.position, groupCenter);
                
                // Attraction force (stronger when further from group)
                float forceMagnitude = groupCohesionStrength * (distance / attractionRange);
                cohesion = direction * forceMagnitude;
            }
            
            return cohesion;
        }
        
        /// <summary>
        /// Calculate leader following force
        /// Agents follow designated leaders
        /// </summary>
        private Vector3 CalculateLeaderFollowing()
        {
            if (leader == null) return Vector3.zero;
            
            Vector3 direction = (leader.position - transform.position);
            float distance = direction.magnitude;
            
            if (distance > leaderFollowDistance && distance < attractionRange)
            {
                direction.Normalize();
                float forceMagnitude = leaderFollowStrength * (distance / attractionRange);
                return direction * forceMagnitude;
            }
            
            return Vector3.zero;
        }
        
        /// <summary>
        /// Set group members (family/group)
        /// </summary>
        public void SetGroupMembers(List<Transform> members)
        {
            groupMembers = new List<Transform>(members);
        }
        
        /// <summary>
        /// Set leader to follow
        /// </summary>
        public void SetLeader(Transform leaderTransform)
        {
            leader = leaderTransform;
            followLeader = leader != null;
        }
        
        /// <summary>
        /// Enable/disable group following
        /// </summary>
        public void SetGroupFollowing(bool enabled)
        {
            followGroup = enabled;
        }
        
        void OnDrawGizmos()
        {
            // Draw repulsion range
            Gizmos.color = Color.red;
            Gizmos.DrawWireSphere(transform.position, repulsionRange);
            
            // Draw attraction range
            Gizmos.color = Color.green;
            Gizmos.DrawWireSphere(transform.position, attractionRange);
            
            // Draw group connections
            if (followGroup)
            {
                Gizmos.color = Color.blue;
                foreach (Transform member in groupMembers)
                {
                    if (member != null && member != transform)
                    {
                        Gizmos.DrawLine(transform.position, member.position);
                    }
                }
            }
            
            // Draw leader connection
            if (followLeader && leader != null)
            {
                Gizmos.color = Color.yellow;
                Gizmos.DrawLine(transform.position, leader.position);
            }
        }
    }
}

