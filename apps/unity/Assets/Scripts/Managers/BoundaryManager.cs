using System.Collections.Generic;
using UnityEngine;
using PeopleFlow.UnitySimulation.Config;

namespace PeopleFlow.UnitySimulation.Managers
{
    /// <summary>
    /// Manages navigable boundary polygons and containment for agents.
    /// </summary>
    public class BoundaryManager : MonoBehaviour
    {
        [Header("Boundary Settings")]
        public bool enforceBoundary = true;
        public float boundaryPadding = 0.2f;
        public bool drawGizmos = true;

        private readonly List<Vector2> polygon = new List<Vector2>();
        private Rect bounds;

        public bool HasBoundary => polygon.Count >= 3;

        public void SetBoundary(SimulationBoundary boundary)
        {
            polygon.Clear();
            if (boundary == null || boundary.points == null || boundary.points.Length < 3)
            {
                bounds = new Rect(-50f, -50f, 100f, 100f);
                return;
            }

            float minX = float.MaxValue;
            float minZ = float.MaxValue;
            float maxX = float.MinValue;
            float maxZ = float.MinValue;

            foreach (var point in boundary.points)
            {
                polygon.Add(new Vector2(point.x, point.y));
                minX = Mathf.Min(minX, point.x);
                minZ = Mathf.Min(minZ, point.y);
                maxX = Mathf.Max(maxX, point.x);
                maxZ = Mathf.Max(maxZ, point.y);
            }

            bounds = Rect.MinMaxRect(minX, minZ, maxX, maxZ);
        }

        public bool IsInside(Vector3 position)
        {
            if (!HasBoundary) return true;
            Vector2 point = new Vector2(position.x, position.z);
            return PointInPolygon(point, polygon);
        }

        public Vector3 ClampToBoundary(Vector3 position)
        {
            if (!HasBoundary) return position;
            if (IsInside(position)) return position;

            Vector2 point = new Vector2(position.x, position.z);
            Vector2 clamped = ClosestPointOnPolygon(point, polygon);
            Vector3 result = new Vector3(clamped.x, position.y, clamped.y);
            if (boundaryPadding > 0f)
            {
                Vector2 inward = (point - clamped).normalized;
                if (inward.sqrMagnitude > 0.001f)
                {
                    result += new Vector3(inward.x, 0f, inward.y) * boundaryPadding;
                }
            }
            return result;
        }

        public Vector3 GetRandomPointInside(float y, int maxAttempts = 64)
        {
            if (!HasBoundary)
            {
                return new Vector3(
                    Random.Range(bounds.xMin, bounds.xMax),
                    y,
                    Random.Range(bounds.yMin, bounds.yMax)
                );
            }

            for (int i = 0; i < Mathf.Max(4, maxAttempts); i++)
            {
                float x = Random.Range(bounds.xMin, bounds.xMax);
                float z = Random.Range(bounds.yMin, bounds.yMax);
                Vector2 point = new Vector2(x, z);
                if (PointInPolygon(point, polygon))
                {
                    return new Vector3(x, y, z);
                }
            }

            Vector2 fallback = polygon[0];
            return new Vector3(fallback.x, y, fallback.y);
        }

        private bool PointInPolygon(Vector2 point, List<Vector2> poly)
        {
            bool inside = false;
            int count = poly.Count;
            for (int i = 0, j = count - 1; i < count; j = i++)
            {
                Vector2 pi = poly[i];
                Vector2 pj = poly[j];

                bool intersect = ((pi.y > point.y) != (pj.y > point.y)) &&
                                 (point.x < (pj.x - pi.x) * (point.y - pi.y) / (pj.y - pi.y + Mathf.Epsilon) + pi.x);
                if (intersect)
                {
                    inside = !inside;
                }
            }
            return inside;
        }

        private Vector2 ClosestPointOnPolygon(Vector2 point, List<Vector2> poly)
        {
            float minDist = float.MaxValue;
            Vector2 closest = point;
            int count = poly.Count;

            for (int i = 0; i < count; i++)
            {
                Vector2 a = poly[i];
                Vector2 b = poly[(i + 1) % count];
                Vector2 projected = ClosestPointOnSegment(point, a, b);
                float dist = (point - projected).sqrMagnitude;
                if (dist < minDist)
                {
                    minDist = dist;
                    closest = projected;
                }
            }

            return closest;
        }

        private Vector2 ClosestPointOnSegment(Vector2 point, Vector2 a, Vector2 b)
        {
            Vector2 ab = b - a;
            float t = Vector2.Dot(point - a, ab) / (ab.sqrMagnitude + Mathf.Epsilon);
            t = Mathf.Clamp01(t);
            return a + ab * t;
        }

        private void OnDrawGizmos()
        {
            if (!drawGizmos || polygon.Count < 2) return;
            Gizmos.color = new Color(0.2f, 0.7f, 1f, 0.6f);
            for (int i = 0; i < polygon.Count; i++)
            {
                Vector2 a = polygon[i];
                Vector2 b = polygon[(i + 1) % polygon.Count];
                Gizmos.DrawLine(new Vector3(a.x, 0.1f, a.y), new Vector3(b.x, 0.1f, b.y));
            }
        }
    }
}
