using System.Collections.Generic;
using UnityEngine;

namespace PeopleFlow.UnitySimulation.Agents
{
    /// <summary>
    /// Body-based collision system for realistic human interactions
    /// Implements rectangle/circle collision to reflect human width and shoulder interactions
    /// Based on research: arXiv crowd dynamics papers
    /// </summary>
    public class BodyCollision : MonoBehaviour
    {
        [Header("Body Dimensions")]
        public float bodyWidth = 0.5f;  // Shoulder width in meters (typical: 0.4-0.6m)
        public float bodyDepth = 0.3f;  // Body depth in meters
        public bool useCircleCollision = false;  // Use circle (simpler) or rectangle (more accurate)
        
        [Header("Collision Settings")]
        public float collisionRadius = 0.5f;  // Effective collision radius
        public float repulsionForce = 2.0f;  // Force applied when colliding
        public float repulsionDistance = 1.0f;  // Distance at which repulsion starts
        
        [Header("Debug")]
        public bool showCollisionBounds = false;
        
        private Rigidbody rb;
        private Collider agentCollider;
        private List<BodyCollision> nearbyAgents = new List<BodyCollision>();
        
        void Start()
        {
            rb = GetComponent<Rigidbody>();
            if (rb == null)
            {
                rb = gameObject.AddComponent<Rigidbody>();
                rb.constraints = RigidbodyConstraints.FreezeRotationX | RigidbodyConstraints.FreezeRotationZ;
                rb.mass = 70f;  // Average human mass in kg
            }
            
            // Create or configure collider
            agentCollider = GetComponent<Collider>();
            if (agentCollider == null)
            {
                if (useCircleCollision)
                {
                    CapsuleCollider capsule = gameObject.AddComponent<CapsuleCollider>();
                    capsule.radius = collisionRadius;
                    capsule.height = 1.8f;  // Average human height
                    capsule.center = new Vector3(0, 0.9f, 0);
                    agentCollider = capsule;
                }
                else
                {
                    BoxCollider box = gameObject.AddComponent<BoxCollider>();
                    box.size = new Vector3(bodyWidth, 1.8f, bodyDepth);
                    box.center = new Vector3(0, 0.9f, 0);
                    agentCollider = box;
                }
            }
            
            // Set physics material for realistic friction
            PhysicMaterial physicsMat = new PhysicMaterial("AgentPhysics");
            physicsMat.dynamicFriction = 0.6f;
            physicsMat.staticFriction = 0.6f;
            physicsMat.bounciness = 0.0f;
            agentCollider.material = physicsMat;
        }
        
        void Update()
        {
            // Find nearby agents for collision detection
            FindNearbyAgents();
        }
        
        void FindNearbyAgents()
        {
            nearbyAgents.Clear();
            Collider[] colliders = Physics.OverlapSphere(transform.position, repulsionDistance);
            
            foreach (Collider col in colliders)
            {
                if (col != agentCollider)
                {
                    BodyCollision otherAgent = col.GetComponent<BodyCollision>();
                    if (otherAgent != null)
                    {
                        nearbyAgents.Add(otherAgent);
                    }
                }
            }
        }
        
        /// <summary>
        /// Calculate repulsion force from nearby agents
        /// Implements body-based collision with realistic human dimensions
        /// </summary>
        public Vector3 GetRepulsionForce()
        {
            Vector3 totalRepulsion = Vector3.zero;
            
            foreach (BodyCollision otherAgent in nearbyAgents)
            {
                Vector3 direction = transform.position - otherAgent.transform.position;
                float distance = direction.magnitude;
                
                if (distance < repulsionDistance && distance > 0.01f)
                {
                    direction.Normalize();
                    
                    // Calculate overlap based on body dimensions
                    float overlap = repulsionDistance - distance;
                    float bodyOverlap = CalculateBodyOverlap(otherAgent, distance);
                    
                    // Apply repulsion force (stronger when closer)
                    float forceMagnitude = repulsionForce * (overlap / repulsionDistance) * bodyOverlap;
                    totalRepulsion += direction * forceMagnitude;
                }
            }
            
            return totalRepulsion;
        }
        
        /// <summary>
        /// Calculate body overlap between two agents
        /// Uses rectangle collision for more accurate human body representation
        /// </summary>
        private float CalculateBodyOverlap(BodyCollision other, float distance)
        {
            if (useCircleCollision)
            {
                // Simple circle collision
                float combinedRadius = collisionRadius + other.collisionRadius;
                return Mathf.Max(0, 1.0f - (distance / combinedRadius));
            }
            else
            {
                // Rectangle collision (more accurate for human body)
                Vector3 toOther = other.transform.position - transform.position;
                Vector3 forward = transform.forward;
                Vector3 right = transform.right;
                
                // Project other agent's position onto this agent's body rectangle
                float projRight = Vector3.Dot(toOther, right);
                float projForward = Vector3.Dot(toOther, forward);
                
                // Check if within body bounds
                float halfWidth = bodyWidth / 2f;
                float halfDepth = bodyDepth / 2f;
                float otherHalfWidth = other.bodyWidth / 2f;
                float otherHalfDepth = other.bodyDepth / 2f;
                
                // Calculate overlap in width and depth
                float widthOverlap = Mathf.Max(0, (halfWidth + otherHalfWidth) - Mathf.Abs(projRight));
                float depthOverlap = Mathf.Max(0, (halfDepth + otherHalfDepth) - Mathf.Abs(projForward));
                
                // Return normalized overlap factor
                float maxOverlap = halfWidth + otherHalfWidth + halfDepth + otherHalfDepth;
                return (widthOverlap + depthOverlap) / maxOverlap;
            }
        }
        
        /// <summary>
        /// Check if agent is in contact with another agent
        /// </summary>
        public bool IsInContact(BodyCollision other)
        {
            float distance = Vector3.Distance(transform.position, other.transform.position);
            float contactDistance = collisionRadius + other.collisionRadius;
            return distance < contactDistance;
        }
        
        void OnDrawGizmos()
        {
            if (showCollisionBounds)
            {
                // Draw collision bounds
                Gizmos.color = Color.yellow;
                if (useCircleCollision)
                {
                    Gizmos.DrawWireSphere(transform.position, collisionRadius);
                }
                else
                {
                    // Draw rectangle bounds
                    Vector3[] corners = new Vector3[4];
                    float halfWidth = bodyWidth / 2f;
                    float halfDepth = bodyDepth / 2f;
                    
                    corners[0] = transform.position + transform.right * halfWidth + transform.forward * halfDepth;
                    corners[1] = transform.position - transform.right * halfWidth + transform.forward * halfDepth;
                    corners[2] = transform.position - transform.right * halfWidth - transform.forward * halfDepth;
                    corners[3] = transform.position + transform.right * halfWidth - transform.forward * halfDepth;
                    
                    for (int i = 0; i < 4; i++)
                    {
                        Gizmos.DrawLine(corners[i], corners[(i + 1) % 4]);
                    }
                }
                
                // Draw repulsion distance
                Gizmos.color = Color.red;
                Gizmos.DrawWireSphere(transform.position, repulsionDistance);
            }
        }
    }
}

