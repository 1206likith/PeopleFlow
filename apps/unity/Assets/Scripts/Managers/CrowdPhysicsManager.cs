using UnityEngine;
using System.Collections.Generic;
using PeopleFlow.UnitySimulation.Agents;
using PeopleFlow.UnitySimulation.Environment;

namespace PeopleFlow.UnitySimulation.Managers
{
    /// <summary>
    /// Manages crowd physics and social forces
    /// Coordinates body-based collision and social force calculations
    /// </summary>
    public class CrowdPhysicsManager : MonoBehaviour
    {
        [Header("Physics Settings")]
        public float physicsUpdateRate = 50f;  // Fixed timestep for physics
        public bool enableBodyCollision = true;
        public bool enableSocialForces = true;
        
        [Header("Performance")]
        public int maxAgentsPerFrame = 10;  // Limit physics calculations per frame
        
        private List<BodyCollision> allBodyCollisions = new List<BodyCollision>();
        private List<SocialForces> allSocialForces = new List<SocialForces>();
        private List<EnhancedCrowdAgent> allAgents = new List<EnhancedCrowdAgent>();
        private float fixedDeltaTime;
        private int currentAgentIndex = 0;
        
        void Start()
        {
            fixedDeltaTime = 1.0f / physicsUpdateRate;
            Time.fixedDeltaTime = fixedDeltaTime;
            
            // Find all agents
            RefreshAgentList();
        }
        
        void Update()
        {
            // Refresh agent list periodically
            if (Time.frameCount % 60 == 0)  // Every 60 frames
            {
                RefreshAgentList();
            }
        }
        
        void FixedUpdate()
        {
            // Process physics in batches for performance
            if (enableBodyCollision || enableSocialForces)
            {
                ProcessPhysicsBatch();
            }
        }
        
        /// <summary>
        /// Refresh list of all agents
        /// </summary>
        void RefreshAgentList()
        {
            allBodyCollisions.Clear();
            allSocialForces.Clear();
            allAgents.Clear();
            
            // Find all agents with body collision
            BodyCollision[] bodyCollisions = FindObjectsOfType<BodyCollision>();
            allBodyCollisions.AddRange(bodyCollisions);
            
            // Find all agents with social forces
            SocialForces[] socialForces = FindObjectsOfType<SocialForces>();
            allSocialForces.AddRange(socialForces);
            
            // Find all enhanced agents
            EnhancedCrowdAgent[] agents = FindObjectsOfType<EnhancedCrowdAgent>();
            allAgents.AddRange(agents);
        }
        
        /// <summary>
        /// Process physics in batches for performance
        /// </summary>
        void ProcessPhysicsBatch()
        {
            int processed = 0;
            int startIndex = currentAgentIndex;
            
            while (processed < maxAgentsPerFrame && allAgents.Count > 0)
            {
                EnhancedCrowdAgent agent = allAgents[currentAgentIndex];
                
                if (agent != null)
                {
                    // Body collision is handled automatically by BodyCollision component
                    // Social forces are handled automatically by SocialForces component
                    // This manager just coordinates and optimizes
                }
                
                currentAgentIndex = (currentAgentIndex + 1) % allAgents.Count;
                processed++;
                
                // Prevent infinite loop
                if (currentAgentIndex == startIndex && processed > 0)
                {
                    break;
                }
            }
        }
        
        /// <summary>
        /// Enable/disable body collision
        /// </summary>
        public void SetBodyCollisionEnabled(bool enabled)
        {
            enableBodyCollision = enabled;
            foreach (BodyCollision bc in allBodyCollisions)
            {
                if (bc != null)
                {
                    bc.enabled = enabled;
                }
            }
        }
        
        /// <summary>
        /// Enable/disable social forces
        /// </summary>
        public void SetSocialForcesEnabled(bool enabled)
        {
            enableSocialForces = enabled;
            foreach (SocialForces sf in allSocialForces)
            {
                if (sf != null)
                {
                    sf.enabled = enabled;
                }
            }
        }
        
        /// <summary>
        /// Get statistics about crowd physics
        /// </summary>
        public Dictionary<string, object> GetPhysicsStats()
        {
            return new Dictionary<string, object>
            {
                { "total_agents", allAgents.Count },
                { "body_collision_enabled", enableBodyCollision },
                { "social_forces_enabled", enableSocialForces },
                { "physics_update_rate", physicsUpdateRate }
            };
        }
    }
}

