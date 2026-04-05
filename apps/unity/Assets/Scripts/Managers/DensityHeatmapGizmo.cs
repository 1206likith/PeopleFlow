using System.Collections.Generic;
using UnityEngine;

namespace PeopleFlow.UnitySimulation.Managers
{
    /// <summary>
    /// Draws a density heatmap gizmo for quick crowd visualization.
    /// </summary>
    public class DensityHeatmapGizmo : MonoBehaviour
    {
        public bool drawHeatmap = true;
        public int maxCells = 1000;
        public float maxDensity = 20f;
        public float cellHeight = 0.1f;
        public Gradient densityGradient;

        private Mesh cellMesh;
        private Material cellMaterial;
        private Matrix4x4[] matrices;
        private Vector4[] colors;
        private MaterialPropertyBlock propertyBlock;

        void Awake()
        {
            // Create a simple quad mesh
            GameObject tempQuad = GameObject.CreatePrimitive(PrimitiveType.Quad);
            cellMesh = tempQuad.GetComponent<MeshFilter>().sharedMesh;
            Destroy(tempQuad);

            Shader shader = Shader.Find("Sprites/Default");
            if (shader != null) {
                cellMaterial = new Material(shader);
                cellMaterial.enableInstancing = true;
            }

            matrices = new Matrix4x4[1023]; // Max per draw call
            colors = new Vector4[1023];
            propertyBlock = new MaterialPropertyBlock();
            
            if (densityGradient == null || densityGradient.colorKeys.Length == 0)
            {
                Reset();
            }
        }

        void Reset()
        {
            densityGradient = new Gradient();
            densityGradient.SetKeys(
                new[]
                {
                    new GradientColorKey(Color.green, 0f),
                    new GradientColorKey(Color.yellow, 0.5f),
                    new GradientColorKey(Color.red, 1f),
                },
                new[]
                {
                    new GradientAlphaKey(0.1f, 0f),
                    new GradientAlphaKey(0.6f, 1f),
                }
            );
        }

        void Update()
        {
            if (!drawHeatmap) return;
            if (SimulationManager.Instance == null) return;
            if (cellMesh == null || cellMaterial == null) return;

            List<SimulationManager.DensityCellSnapshot> cells = SimulationManager.Instance.GetDensityHeatmap(maxCells);
            int count = Mathf.Min(cells.Count, 1023);
            if (count == 0) return;

            float size = Mathf.Max(0.2f, SimulationManager.Instance.densityCellSize);

            for (int i = 0; i < count; i++)
            {
                var cell = cells[i];
                float t = Mathf.Clamp01(cell.count / Mathf.Max(1f, maxDensity));
                Color color = densityGradient != null ? densityGradient.Evaluate(t) : Color.Lerp(Color.green, Color.red, t);
                
                Vector3 pos = new Vector3(cell.x, cellHeight, cell.z);
                matrices[i] = Matrix4x4.TRS(pos, Quaternion.Euler(90, 0, 0), new Vector3(size, size, 1));
                colors[i] = color;
            }

            propertyBlock.SetVectorArray("_Color", colors);
            Graphics.DrawMeshInstanced(cellMesh, 0, cellMaterial, matrices, count, propertyBlock);
        }
    }
}
