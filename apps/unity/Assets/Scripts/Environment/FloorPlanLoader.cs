using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.AI;
using System;
using PeopleFlow.UnitySimulation.Config;

namespace PeopleFlow.UnitySimulation.Environment
{
    /// <summary>
    /// Loads and renders floor plan from uploaded image
    /// Generates walls and obstacles based on floor plan image
    /// </summary>
    public class FloorPlanLoader : MonoBehaviour
    {
        [Header("Floor Plan Settings")]
        public Material wallMaterial;
        public Material floorMaterial;
        public float wallHeight = 3f;
        public float floorThickness = 0.1f;
        public float pixelsPerUnit = 10f; // Scale factor
        public bool useSegmentWalls = true;
        public float defaultWallThickness = 0.2f;
        
        [Header("Wall Generation")]
        public GameObject wallPrefab;
        public GameObject floorPrefab;
        public Transform wallsParent;
        public Transform floorParent;
        
        [Header("Image Processing")]
        public Texture2D floorPlanTexture;
        public Color wallColor = Color.black;
        public float wallThreshold = 0.5f; // Pixel brightness threshold for walls
        
        private List<GameObject> generatedWalls = new List<GameObject>();
        private List<GameObject> generatedObstacles = new List<GameObject>();
        private GameObject currentFloor;
        
        /// <summary>
        /// Load floor plan from image URL or texture
        /// </summary>
        public void LoadFloorPlan(Texture2D texture, List<Vector3> exits = null)
        {
            if (texture == null)
            {
                Debug.LogWarning("FloorPlanLoader: No texture provided, using default layout");
                CreateDefaultLayout(exits);
                return;
            }
            
            floorPlanTexture = texture;
            GenerateWallsFromTexture(exits);
        }

        /// <summary>
        /// Load floor plan from backend metadata (detected walls, boundaries, etc.)
        /// </summary>
        public void LoadFloorPlanData(FloorPlanMessage data)
        {
            if (data == null)
            {
                LoadFloorPlan(null, null);
                return;
            }

            if (useSegmentWalls && data.detected_walls != null && data.detected_walls.Length > 0)
            {
                ClearExistingWalls();
                CreateFloorFromBounds(data.building_bounds);
                CreateWallsFromSegments(data.detected_walls, data.building_bounds);
                if (data.detected_obstacles != null && data.detected_obstacles.Length > 0)
                {
                    CreateObstacles(data.detected_obstacles, data.building_bounds);
                }
                StartCoroutine(RebuildNavMesh());
                return;
            }

            LoadFloorPlan(null, null);
        }
        
        /// <summary>
        /// Generate walls from floor plan texture
        /// </summary>
        private void GenerateWallsFromTexture(List<Vector3> exits = null)
        {
            ClearExistingWalls();
            
            if (floorPlanTexture == null)
            {
                CreateDefaultLayout();
                return;
            }
            
            // Create floor plane
            CreateFloor();
            
            // Process image to find walls
            int width = floorPlanTexture.width;
            int height = floorPlanTexture.height;
            
            // Convert image to grayscale and find wall pixels
            bool[,] wallMap = new bool[width, height];
            for (int x = 0; x < width; x++)
            {
                for (int y = 0; y < height; y++)
                {
                    Color pixel = floorPlanTexture.GetPixel(x, y);
                    float brightness = pixel.grayscale;
                    wallMap[x, y] = brightness < wallThreshold;
                }
            }
            
            // Generate walls using edge detection
            GenerateWallsFromMap(wallMap, width, height);
            
            // Place exits if provided
            if (exits != null && exits.Count > 0)
            {
                PlaceExits(exits);
            }
            
            // Rebuild NavMesh after walls are created
            StartCoroutine(RebuildNavMesh());
        }
        
        /// <summary>
        /// Generate walls from wall map using edge detection
        /// </summary>
        private void GenerateWallsFromMap(bool[,] wallMap, int width, int height)
        {
            float scaleX = width / pixelsPerUnit;
            float scaleZ = height / pixelsPerUnit;
            float offsetX = -scaleX / 2f;
            float offsetZ = -scaleZ / 2f;
            
            // Create walls along edges
            for (int x = 0; x < width; x++)
            {
                for (int y = 0; y < height; y++)
                {
                    if (wallMap[x, y])
                    {
                        // Check if this is an edge pixel
                        bool isEdge = false;
                        if (x == 0 || x == width - 1 || y == 0 || y == height - 1)
                            isEdge = true;
                        else if (!wallMap[x - 1, y] || !wallMap[x + 1, y] || 
                                 !wallMap[x, y - 1] || !wallMap[x, y + 1])
                            isEdge = true;
                        
                        if (isEdge)
                        {
                            CreateWallSegment(
                                new Vector3(offsetX + (x / pixelsPerUnit), wallHeight / 2f, offsetZ + (y / pixelsPerUnit)),
                                1f / pixelsPerUnit,
                                wallHeight
                            );
                        }
                    }
                }
            }
        }
        
        /// <summary>
        /// Create a wall segment
        /// </summary>
        private void CreateWallSegment(Vector3 position, float width, float height)
        {
            GameObject wall;
            
            if (wallPrefab != null)
            {
                wall = Instantiate(wallPrefab, position, Quaternion.identity);
            }
            else
            {
                wall = GameObject.CreatePrimitive(PrimitiveType.Cube);
                wall.transform.position = position;
                wall.transform.localScale = new Vector3(width, height, width);
                
                if (wallMaterial != null)
                {
                    wall.GetComponent<Renderer>().material = wallMaterial;
                }
            }
            
            wall.name = "Wall";
            wall.isStatic = true;
            wall.tag = "Obstacle";
            
            if (wallsParent != null)
            {
                wall.transform.SetParent(wallsParent);
            }
            else
            {
                wall.transform.SetParent(transform);
            }
            
            generatedWalls.Add(wall);
        }
        
        /// <summary>
        /// Create floor plane
        /// </summary>
        private void CreateFloor()
        {
            if (currentFloor != null)
            {
                Destroy(currentFloor);
            }
            
            GameObject floor;
            
            if (floorPrefab != null)
            {
                floor = Instantiate(floorPrefab, Vector3.zero, Quaternion.identity);
            }
            else
            {
                floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
                floor.transform.position = Vector3.zero;
                
                if (floorPlanTexture != null)
                {
                    float scaleX = floorPlanTexture.width / pixelsPerUnit;
                    float scaleZ = floorPlanTexture.height / pixelsPerUnit;
                    floor.transform.localScale = new Vector3(scaleX / 10f, 1f, scaleZ / 10f);
                    
                    if (floorMaterial != null)
                    {
                        floor.GetComponent<Renderer>().material = floorMaterial;
                        floor.GetComponent<Renderer>().material.mainTexture = floorPlanTexture;
                    }
                }
            }
            
            floor.name = "Floor";
            floor.isStatic = true;
            
            if (floorParent != null)
            {
                floor.transform.SetParent(floorParent);
            }
            else
            {
                floor.transform.SetParent(transform);
            }
            
            currentFloor = floor;
        }

        private void CreateFloorFromBounds(BuildingBounds bounds)
        {
            if (currentFloor != null)
            {
                Destroy(currentFloor);
            }

            GameObject floor;
            if (floorPrefab != null)
            {
                floor = Instantiate(floorPrefab, Vector3.zero, Quaternion.identity);
            }
            else
            {
                floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
            }

            float width = bounds != null ? bounds.width : 0f;
            float height = bounds != null ? bounds.height : 0f;
            if (width <= 0f || height <= 0f)
            {
                width = 100f;
                height = 100f;
            }

            floor.transform.position = Vector3.zero;
            floor.transform.localScale = new Vector3((width / pixelsPerUnit) / 10f, 1f, (height / pixelsPerUnit) / 10f);

            if (floorMaterial != null)
            {
                var renderer = floor.GetComponent<Renderer>();
                if (renderer != null)
                {
                    renderer.material = floorMaterial;
                }
            }

            floor.name = "Floor";
            floor.isStatic = true;

            if (floorParent != null)
            {
                floor.transform.SetParent(floorParent);
            }
            else
            {
                floor.transform.SetParent(transform);
            }

            currentFloor = floor;
        }

        private void CreateWallsFromSegments(WallData[] walls, BuildingBounds bounds)
        {
            if (walls == null) return;

            foreach (var wall in walls)
            {
                Vector3 p1 = MapToWorld(wall.x1, wall.y1, bounds);
                Vector3 p2 = MapToWorld(wall.x2, wall.y2, bounds);
                float length = Vector3.Distance(p1, p2);
                float thickness = wall.thickness > 0f ? wall.thickness / pixelsPerUnit : defaultWallThickness;
                if (length < 0.1f) continue;

                GameObject wallObj;
                if (wallPrefab != null)
                {
                    wallObj = Instantiate(wallPrefab, Vector3.zero, Quaternion.identity);
                }
                else
                {
                    wallObj = GameObject.CreatePrimitive(PrimitiveType.Cube);
                }

                Vector3 center = (p1 + p2) / 2f;
                wallObj.transform.position = center + new Vector3(0f, wallHeight / 2f, 0f);
                wallObj.transform.rotation = Quaternion.LookRotation(p2 - p1);
                wallObj.transform.localScale = new Vector3(thickness, wallHeight, length);
                wallObj.name = "Wall";
                wallObj.tag = "Obstacle";
                wallObj.isStatic = true;

                if (wallMaterial != null)
                {
                    var renderer = wallObj.GetComponent<Renderer>();
                    if (renderer != null)
                    {
                        renderer.material = wallMaterial;
                    }
                }

                if (wallsParent != null)
                {
                    wallObj.transform.SetParent(wallsParent);
                }
                else
                {
                    wallObj.transform.SetParent(transform);
                }

                generatedWalls.Add(wallObj);
            }
        }

        private void CreateObstacles(ObstacleData[] obstacles, BuildingBounds bounds)
        {
            foreach (var obstacle in obstacles)
            {
                Vector3 position = MapToWorld(obstacle.x, obstacle.z > 0f ? obstacle.z : obstacle.y, bounds);
                GameObject obj = GameObject.CreatePrimitive(PrimitiveType.Cube);
                obj.transform.position = position + new Vector3(0f, obstacle.height / pixelsPerUnit / 2f, 0f);
                obj.transform.localScale = new Vector3(
                    Mathf.Max(0.2f, obstacle.width / pixelsPerUnit),
                    Mathf.Max(0.2f, obstacle.height / pixelsPerUnit),
                    Mathf.Max(0.2f, obstacle.depth / pixelsPerUnit)
                );
                obj.name = "Obstacle";
                obj.tag = "Obstacle";
                obj.isStatic = true;
                obj.transform.SetParent(transform);
                generatedObstacles.Add(obj);
            }
        }

        private Vector3 MapToWorld(float px, float py, BuildingBounds bounds)
        {
            if (bounds == null)
            {
                return new Vector3(px / pixelsPerUnit, 0f, py / pixelsPerUnit);
            }

            float centerX = (bounds.min_x + bounds.max_x) / 2f;
            float centerY = (bounds.min_y + bounds.max_y) / 2f;
            float worldX = (px - centerX) / pixelsPerUnit;
            float worldZ = (py - centerY) / pixelsPerUnit;
            return new Vector3(worldX, 0f, worldZ);
        }
        
        /// <summary>
        /// Place exit markers
        /// </summary>
        private void PlaceExits(List<Vector3> exitPositions)
        {
            foreach (var exitPos in exitPositions)
            {
                GameObject exit = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                exit.transform.position = exitPos;
                exit.transform.localScale = new Vector3(2f, 0.5f, 2f);
                exit.name = "Exit";
                exit.tag = "Exit";
                
                // Make exit green
                Renderer renderer = exit.GetComponent<Renderer>();
                Material exitMat = new Material(Shader.Find("Standard"));
                exitMat.color = Color.green;
                renderer.material = exitMat;
                
                // Add exit marker
                exit.transform.SetParent(transform);

                if (PeopleFlow.UnitySimulation.Managers.SimulationManager.Instance != null &&
                    PeopleFlow.UnitySimulation.Managers.SimulationManager.Instance.ExitManager != null)
                {
                    PeopleFlow.UnitySimulation.Managers.SimulationManager.Instance.ExitManager.RegisterExit(exit.transform);
                }
            }
        }
        
        /// <summary>
        /// Create default layout if no floor plan
        /// </summary>
        private void CreateDefaultLayout(List<Vector3> exits = null)
        {
            ClearExistingWalls();
            CreateFloor();
            
            // Create simple room with 4 walls
            float roomSize = 50f;
            float wallThickness = 0.5f;
            
            // North wall
            CreateWall(new Vector3(0, wallHeight / 2f, roomSize / 2f), 
                      new Vector3(roomSize, wallHeight, wallThickness));
            
            // South wall
            CreateWall(new Vector3(0, wallHeight / 2f, -roomSize / 2f), 
                      new Vector3(roomSize, wallHeight, wallThickness));
            
            // East wall
            CreateWall(new Vector3(roomSize / 2f, wallHeight / 2f, 0), 
                      new Vector3(wallThickness, wallHeight, roomSize));
            
            // West wall
            CreateWall(new Vector3(-roomSize / 2f, wallHeight / 2f, 0), 
                      new Vector3(wallThickness, wallHeight, roomSize));
            
            // Place exits if provided
            if (exits != null && exits.Count > 0)
            {
                PlaceExits(exits);
            }
            
            StartCoroutine(RebuildNavMesh());
        }
        
        /// <summary>
        /// Create a wall
        /// </summary>
        private void CreateWall(Vector3 position, Vector3 scale)
        {
            GameObject wall = GameObject.CreatePrimitive(PrimitiveType.Cube);
            wall.transform.position = position;
            wall.transform.localScale = scale;
            wall.name = "Wall";
            wall.isStatic = true;
            wall.tag = "Obstacle";
            
            if (wallMaterial != null)
            {
                wall.GetComponent<Renderer>().material = wallMaterial;
            }
            
            if (wallsParent != null)
            {
                wall.transform.SetParent(wallsParent);
            }
            else
            {
                wall.transform.SetParent(transform);
            }
            
            generatedWalls.Add(wall);
        }
        
        /// <summary>
        /// Clear existing walls
        /// </summary>
        private void ClearExistingWalls()
        {
            foreach (var wall in generatedWalls)
            {
                if (wall != null) Destroy(wall);
            }
            generatedWalls.Clear();

            foreach (var obstacle in generatedObstacles)
            {
                if (obstacle != null) Destroy(obstacle);
            }
            generatedObstacles.Clear();
            
            if (currentFloor != null)
            {
                Destroy(currentFloor);
                currentFloor = null;
            }
        }
        
        /// <summary>
        /// Rebuild NavMesh after walls are created
        /// </summary>
        private IEnumerator RebuildNavMesh()
        {
            yield return new WaitForSeconds(0.1f);
            
            // Note: NavMesh baking typically requires NavMeshBuilder API
            // For now, this is a placeholder - NavMesh should be baked in Editor
            // or using NavMeshBuilder.BuildNavMesh() at runtime
            Debug.Log("FloorPlanLoader: NavMesh should be rebuilt. Use NavMeshBuilder in production.");
        }
        
        void OnDestroy()
        {
            ClearExistingWalls();
        }
    }
}

