using UnityEngine;
using UnityEngine.AI;

namespace PeopleFlow.UnitySimulation.Environment
{
    /// <summary>
    /// Manages obstacles in the environment - marks them as Navigation Static
    /// </summary>
    public class ObstacleController : MonoBehaviour
    {
        [Header("Obstacle Settings")]
        public bool markAsNavigationStatic = true;
        public bool markChildrenAsStatic = true;

        void Start()
        {
            SetupObstacles();
        }

        /// <summary>
        /// Setup obstacles for NavMesh
        /// </summary>
        private void SetupObstacles()
        {
            // Note: Navigation Static flag should be set in Unity Editor
            // This script just ensures objects are properly configured
            // In Editor: Select object → Inspector → Static → Navigation Static
            
            if (markAsNavigationStatic)
            {
                gameObject.isStatic = true;
            }

            if (markChildrenAsStatic)
            {
                foreach (Transform child in transform)
                {
                    child.gameObject.isStatic = true;
                }
            }
        }

        /// <summary>
        /// Add obstacle at runtime
        /// </summary>
        public void AddObstacle(GameObject obstacle)
        {
            if (obstacle != null)
            {
                obstacle.transform.SetParent(transform);
                obstacle.isStatic = true;
                
                // Note: NavMesh must be rebaked after adding obstacles
                // This typically requires NavMeshBuilder API or manual baking in Editor
            }
        }

        /// <summary>
        /// Remove obstacle
        /// </summary>
        public void RemoveObstacle(GameObject obstacle)
        {
            if (obstacle != null)
            {
                Destroy(obstacle);
                // Re-bake NavMesh if needed
            }
        }
    }
}
