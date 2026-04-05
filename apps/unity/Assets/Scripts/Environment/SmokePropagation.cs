using UnityEngine;
using System.Collections.Generic;

namespace PeopleFlow.UnitySimulation.Environment
{
    /// <summary>
    /// Smoke propagation system for fire emergencies
    /// Affects visibility and movement speed
    /// Based on research: Multi-scale evacuation simulation with environment effects
    /// </summary>
    public class SmokePropagation : MonoBehaviour
    {
        [Header("Smoke Source")]
        public Transform smokeSource;
        public float smokeRadius = 20f;
        public float smokePropagationRate = 0.05f;  // 5% per second
        public float maxSmokeOpacity = 1.0f;
        
        [Header("Effects")]
        public float visibilityReduction = 0.3f;  // Reduces visibility in smoke
        public float speedReduction = 0.1f;  // Reduces movement speed in smoke
        public float panicIncrease = 0.02f;  // Increases panic per second in smoke
        
        [Header("Visualization")]
        public ParticleSystem smokeParticleSystem;
        public Material smokeMaterial;
        public bool showSmokeGizmos = true;
        
        private Dictionary<Collider, float> agentsInSmoke = new Dictionary<Collider, float>();
        private float currentSmokeOpacity = 0f;
        
        void Start()
        {
            // Create smoke particle system if not assigned
            if (smokeParticleSystem == null)
            {
                GameObject smokeObj = new GameObject("SmokeParticles");
                smokeObj.transform.SetParent(transform);
                smokeParticleSystem = smokeObj.AddComponent<ParticleSystem>();
                
                var main = smokeParticleSystem.main;
                main.startLifetime = 10f;
                main.startSpeed = 0.5f;
                main.startSize = 2f;
                main.maxParticles = 1000;
                
                var emission = smokeParticleSystem.emission;
                emission.rateOverTime = 50f;
                
                var shape = smokeParticleSystem.shape;
                shape.shapeType = ParticleSystemShapeType.Sphere;
                shape.radius = smokeRadius;
            }
            
            if (smokeSource == null)
            {
                smokeSource = transform;
            }
        }
        
        void Update()
        {
            // Propagate smoke over time
            if (currentSmokeOpacity < maxSmokeOpacity)
            {
                currentSmokeOpacity = Mathf.Min(maxSmokeOpacity, currentSmokeOpacity + smokePropagationRate * Time.deltaTime);
            }
            
            // Update particle system
            if (smokeParticleSystem != null)
            {
                var main = smokeParticleSystem.main;
                main.startColor = new Color(0.3f, 0.3f, 0.3f, currentSmokeOpacity);
            }
            
            // Check for agents in smoke
            CheckAgentsInSmoke();
            
            // Apply smoke effects to agents
            ApplySmokeEffects();
        }
        
        /// <summary>
        /// Check which agents are in smoke
        /// </summary>
        void CheckAgentsInSmoke()
        {
            agentsInSmoke.Clear();
            
            Collider[] colliders = Physics.OverlapSphere(smokeSource.position, smokeRadius);
            foreach (Collider col in colliders)
            {
                // Check if it's an agent
                if (col.GetComponent<EnhancedCrowdAgent>() != null || 
                    col.GetComponent<CrowdAgent>() != null)
                {
                    float distance = Vector3.Distance(smokeSource.position, col.transform.position);
                    float smokeIntensity = 1.0f - (distance / smokeRadius);  // Stronger at center
                    agentsInSmoke[col] = smokeIntensity * currentSmokeOpacity;
                }
            }
        }
        
        /// <summary>
        /// Apply smoke effects to agents
        /// </summary>
        void ApplySmokeEffects()
        {
            foreach (var kvp in agentsInSmoke)
            {
                Collider agentCollider = kvp.Key;
                float smokeIntensity = kvp.Value;
                
                // Apply visibility reduction
                // (This would affect camera/rendering, implemented separately)
                
                // Apply speed reduction
                Rigidbody rb = agentCollider.GetComponent<Rigidbody>();
                if (rb != null)
                {
                    float speedModifier = 1.0f - (speedReduction * smokeIntensity);
                    rb.velocity *= speedModifier;
                }
                
                // Apply panic increase
                EnhancedCrowdAgent enhancedAgent = agentCollider.GetComponent<EnhancedCrowdAgent>();
                if (enhancedAgent != null)
                {
                    float currentPanic = enhancedAgent.GetPanicLevel();
                    enhancedAgent.SetPanicLevel(currentPanic + panicIncrease * smokeIntensity * Time.deltaTime);
                }
                else
                {
                    CrowdAgent agent = agentCollider.GetComponent<CrowdAgent>();
                    if (agent != null)
                    {
                        // Update panic if CrowdAgent has panic property
                        // (Implementation depends on CrowdAgent structure)
                    }
                }
            }
        }
        
        /// <summary>
        /// Get smoke intensity at a position
        /// </summary>
        public float GetSmokeIntensity(Vector3 position)
        {
            float distance = Vector3.Distance(smokeSource.position, position);
            if (distance > smokeRadius)
            {
                return 0f;
            }
            
            float intensity = 1.0f - (distance / smokeRadius);
            return intensity * currentSmokeOpacity;
        }
        
        /// <summary>
        /// Set smoke propagation rate
        /// </summary>
        public void SetPropagationRate(float rate)
        {
            smokePropagationRate = rate;
        }
        
        /// <summary>
        /// Reset smoke
        /// </summary>
        public void ResetSmoke()
        {
            currentSmokeOpacity = 0f;
            agentsInSmoke.Clear();
        }
        
        void OnDrawGizmos()
        {
            if (showSmokeGizmos && smokeSource != null)
            {
                // Draw smoke radius
                Gizmos.color = new Color(0.5f, 0.5f, 0.5f, currentSmokeOpacity);
                Gizmos.DrawSphere(smokeSource.position, smokeRadius);
                
                // Draw smoke source
                Gizmos.color = Color.red;
                Gizmos.DrawWireSphere(smokeSource.position, 0.5f);
            }
        }
    }
}

