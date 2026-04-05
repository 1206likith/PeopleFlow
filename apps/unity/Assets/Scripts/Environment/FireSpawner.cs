using UnityEngine;

namespace PeopleFlow.UnitySimulation.Environment
{
    /// <summary>
    /// Spawns and manages fire/danger zones in the environment
    /// </summary>
    public class FireSpawner : MonoBehaviour
    {
        [Header("Fire Settings")]
        public GameObject firePrefab;
        public int numFires = 1;
        public float fireRadius = 10f;
        public float damageRadius = 15f;

        [Header("Spawn Area")]
        public Transform spawnArea;
        public bool randomSpawn = true;

        private GameObject[] activeFires;

        void Start()
        {
            SpawnFires();
            UpdateAgentDistances();
        }

        void Update()
        {
            // Update agent distances to danger periodically
            if (Time.frameCount % 10 == 0) // Every 10 frames
            {
                UpdateAgentDistances();
            }
        }

        /// <summary>
        /// Spawn fire hazards
        /// </summary>
        private void SpawnFires()
        {
            activeFires = new GameObject[numFires];

            for (int i = 0; i < numFires; i++)
            {
                Vector3 spawnPos;

                if (randomSpawn && spawnArea != null)
                {
                    spawnPos = new Vector3(
                        spawnArea.position.x + Random.Range(-spawnArea.localScale.x / 2, spawnArea.localScale.x / 2),
                        spawnArea.position.y,
                        spawnArea.position.z + Random.Range(-spawnArea.localScale.z / 2, spawnArea.localScale.z / 2)
                    );
                }
                else
                {
                    spawnPos = transform.position;
                }

                if (firePrefab != null)
                {
                    GameObject fire = Instantiate(firePrefab, spawnPos, Quaternion.identity);
                    fire.name = $"Fire_{i}";
                    activeFires[i] = fire;
                }
            }
        }

        /// <summary>
        /// Update distance to danger for all agents
        /// </summary>
        private void UpdateAgentDistances()
        {
            var agents = FindObjectsOfType<PeopleFlow.UnitySimulation.Agents.CrowdAgent>();

            foreach (var agent in agents)
            {
                if (agent == null) continue;

                float minDistance = float.MaxValue;

                // Find closest fire
                foreach (var fire in activeFires)
                {
                    if (fire != null)
                    {
                        float distance = Vector3.Distance(agent.transform.position, fire.transform.position);
                        minDistance = Mathf.Min(minDistance, distance);
                    }
                }

                agent.SetDistanceToDanger(minDistance);
            }
        }

        /// <summary>
        /// Get all active fire positions
        /// </summary>
        public Vector3[] GetFirePositions()
        {
            var positions = new System.Collections.Generic.List<Vector3>();
            
            foreach (var fire in activeFires)
            {
                if (fire != null)
                {
                    positions.Add(fire.transform.position);
                }
            }

            return positions.ToArray();
        }
    }
}
