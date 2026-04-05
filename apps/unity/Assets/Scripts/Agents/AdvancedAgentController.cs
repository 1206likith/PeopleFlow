using UnityEngine;
using UnityEngine.AI;
using PeopleFlow.UnitySimulation.Managers;

namespace PeopleFlow.UnitySimulation.Agents
{
    /// <summary>
    /// Advanced agent controller with perception, decision-making, and hazard-aware navigation.
    /// </summary>
    [RequireComponent(typeof(NavMeshAgent))]
    public class AdvancedAgentController : MonoBehaviour
    {
        [Header("Profile")]
        public AgentProfile profile;
        public int groupId = 0;
        public bool isLeader = false;

        [Header("State")]
        public float panicLevel = 0f;
        public float stressLevel = 0f;
        public float fatigue = 0f;
        public float reactionTimer = 0f;
        public string currentExitId = "";
        public string recommendedExitId = "";
        public bool isEvacuated = false;
        public float visibility = 1f;
        public float smokeExposure = 0f;

        [Header("Tuning")]
        public float decisionInterval = 2.0f;
        public float exitArrivalDistance = 1.6f;
        public float densityPanicFactor = 0.01f;
        public float fatigueRate = 0.0025f;
        public float calmRate = 0.2f;
        public float hazardPanicRate = 0.6f;
        public float recommendationTimeout = 6f;
        public float assistanceRadius = 6f;
        public float commitmentDuration = 6f;
        public float rerouteCooldown = 2f;
        public float queueTolerance = 1.2f;
        public float hazardTolerance = 0.6f;
        public float hazardAvoidanceWeight = 2f;
        public float densityAvoidanceWeight = 1.2f;
        public float boundaryAvoidanceWeight = 1.5f;
        public float steeringSampleDistance = 1.5f;
        public float steeringOffsetStrength = 1.2f;
        public float avoidExitDuration = 8f;
        public float stuckSpeedThreshold = 0.05f;
        public float stuckTimeThreshold = 3f;
        public float stuckRepathRadius = 2f;
        public float panicJitterRadius = 0.8f;
        public float panicJitterInterval = 0.6f;

        private NavMeshAgent navAgent;
        private Animator animator;
        private CrowdAgent crowdAgent;
        private EnhancedCrowdAgent enhancedAgent;
        private float lastDecisionTime = 0f;
        private float lastRecommendationTime = -999f;
        private float lastRerouteTime = -999f;
        private float commitmentTimer = 0f;
        private readonly System.Collections.Generic.Dictionary<string, float> avoidedExits = new System.Collections.Generic.Dictionary<string, float>();
        private float stuckTimer = 0f;
        private float lastJitterTime = -999f;
        private Vector3 jitterOffset = Vector3.zero;

        public bool IsEvacuated => isEvacuated;
        public string CurrentExitId => currentExitId;

        void Awake()
        {
            navAgent = GetComponent<NavMeshAgent>();
            animator = GetComponent<Animator>();
            crowdAgent = GetComponent<CrowdAgent>();
            enhancedAgent = GetComponent<EnhancedCrowdAgent>();
        }

        public void Initialize(AgentProfile assignedProfile, int group, bool leader)
        {
            profile = assignedProfile != null ? assignedProfile.Clone() : AgentProfile.GetDefault("adult");
            groupId = group;
            isLeader = leader;
            reactionTimer = Mathf.Max(0f, profile.reactionTime + Random.Range(-0.3f, 0.6f));
            decisionInterval = Mathf.Max(0.5f, decisionInterval - profile.familiarity + Random.Range(-0.2f, 0.4f));
            ApplyProfileToNavMesh();
        }

        private void ApplyProfileToNavMesh()
        {
            if (navAgent == null || profile == null) return;
            navAgent.speed = profile.baseSpeed;
            navAgent.acceleration = Mathf.Lerp(6f, 12f, profile.compliance);
            navAgent.angularSpeed = Mathf.Lerp(120f, 360f, profile.compliance);
            navAgent.stoppingDistance = exitArrivalDistance;
            navAgent.avoidancePriority = profile.staff ? 20 : Mathf.RoundToInt(Mathf.Lerp(60f, 40f, profile.compliance));
            navAgent.obstacleAvoidanceType = profile.mobilityLimited
                ? ObstacleAvoidanceType.LowQualityObstacleAvoidance
                : ObstacleAvoidanceType.HighQualityObstacleAvoidance;
        }

        void Update()
        {
            if (SimulationManager.Instance == null || !SimulationManager.Instance.isRunning) return;

            float dt = Time.deltaTime;

            var boundary = SimulationManager.Instance.BoundaryManager;
            if (boundary != null && boundary.enforceBoundary && !boundary.IsInside(transform.position))
            {
                Vector3 clamped = boundary.ClampToBoundary(transform.position);
                transform.position = clamped;
                if (navAgent != null)
                {
                    navAgent.Warp(clamped);
                }
            }

            if (reactionTimer > 0f)
            {
                reactionTimer -= dt;
                UpdateAnimator(0f, panicLevel);
                return;
            }

            UpdatePerception(dt);

            bool usedRecommendation = TryApplyRecommendation();

            if (commitmentTimer > 0f)
            {
                commitmentTimer = Mathf.Max(0f, commitmentTimer - dt);
            }

            if (!usedRecommendation && ShouldReroute())
            {
                ChooseExit();
                lastDecisionTime = Time.time;
            }
            else if (!usedRecommendation && (Time.time - lastDecisionTime > GetDynamicDecisionInterval() || string.IsNullOrEmpty(currentExitId)))
            {
                ChooseExit();
                lastDecisionTime = Time.time;
            }

            MoveTowardsGoal();
            CheckExitReached();
            RecoverIfStuck(dt);
        }

        private void UpdatePerception(float dt)
        {
            var hazardManager = SimulationManager.Instance.HazardManager;
            float hazardIntensity = hazardManager != null ? hazardManager.GetHazardIntensity(transform.position) : 0f;
            float smokeIntensity = hazardManager != null ? hazardManager.GetSmokeIntensity(transform.position) : 0f;
            smokeExposure = Mathf.Clamp01(smokeIntensity);
            visibility = Mathf.Clamp01(1f - smokeExposure);

            float density = SimulationManager.Instance.GetLocalDensity(transform.position);
            float panicIncrease = hazardIntensity * hazardPanicRate * profile.panicSusceptibility;
            panicIncrease += density * densityPanicFactor;

            panicLevel = Mathf.Clamp01(panicLevel + panicIncrease * dt - calmRate * (1f - hazardIntensity) * dt);
            stressLevel = Mathf.Clamp01(stressLevel + (panicIncrease * 0.5f) * dt);

            fatigue = Mathf.Clamp01(fatigue + fatigueRate * dt);

            if (crowdAgent != null)
            {
                crowdAgent.panicLevel = panicLevel;
            }
            if (enhancedAgent != null)
            {
                enhancedAgent.SetPanicLevel(panicLevel);
            }

            if (navAgent != null)
            {
                float speed = profile.baseSpeed * profile.mobility;
                speed *= (1f + panicLevel * 0.6f);
                speed *= Mathf.Lerp(1f, 0.7f, smokeExposure);
                speed *= Mathf.Lerp(1f, 0.8f, fatigue);

                if (profile.needsAssistance)
                {
                    var staff = SimulationManager.Instance.FindNearestStaff(transform.position, assistanceRadius);
                    if (staff != null)
                    {
                        speed *= 1.15f;
                        if (!string.IsNullOrEmpty(staff.CurrentExitId))
                        {
                            ApplyRecommendation(staff.CurrentExitId);
                        }
                    }
                    else
                    {
                        speed *= 0.85f;
                    }
                }

                speed = Mathf.Clamp(speed, 0.2f, profile.maxSpeed);
                navAgent.speed = speed;
            }
        }

        private void ChooseExit()
        {
            var exitManager = SimulationManager.Instance.ExitManager;
            if (exitManager == null) return;

            var bestExit = FindBestVisibleExit(exitManager);
            if (bestExit == null) return;

            currentExitId = bestExit.id;
            commitmentTimer = commitmentDuration * Mathf.Lerp(0.6f, 1.4f, profile.patience);
            if (crowdAgent != null)
            {
                crowdAgent.SetTargetExit(bestExit.transform);
            }
            if (enhancedAgent != null)
            {
                enhancedAgent.SetTargetExit(bestExit.transform);
            }
            if (navAgent != null)
            {
                navAgent.SetDestination(bestExit.transform.position);
            }
        }

        private bool TryApplyRecommendation()
        {
            if (string.IsNullOrEmpty(recommendedExitId)) return false;
            if (Time.time - lastRecommendationTime > recommendationTimeout) return false;
            if (profile != null && profile.compliance < 0.35f) return false;
            if (panicLevel > 0.9f) return false;

            var exitManager = SimulationManager.Instance.ExitManager;
            if (exitManager == null) return false;
            var exit = exitManager.GetExitById(recommendedExitId);
            if (exit == null || exit.transform == null || exit.isBlocked) return false;

            currentExitId = exit.id;
            if (navAgent != null)
            {
                navAgent.SetDestination(exit.transform.position);
            }
            return true;
        }

        public void ApplyRecommendation(string exitId)
        {
            if (string.IsNullOrEmpty(exitId)) return;
            recommendedExitId = exitId;
            lastRecommendationTime = Time.time;
        }

        private void MoveTowardsGoal()
        {
            if (navAgent == null) return;

            Vector3 targetPosition = Vector3.zero;
            bool hasTarget = false;

            if (groupId > 0 && !isLeader && profile.groupCohesion > 0.1f)
            {
                Vector3 leaderPos = SimulationManager.Instance.GetGroupLeaderPosition(groupId);
                if (leaderPos != Vector3.zero)
                {
                    float leaderDistance = Vector3.Distance(transform.position, leaderPos);
                    if (leaderDistance > 2f + profile.groupCohesion * 3f)
                    {
                        targetPosition = leaderPos;
                        hasTarget = true;
                    }
                }
            }

            if (!hasTarget && !string.IsNullOrEmpty(currentExitId))
            {
                var exit = SimulationManager.Instance.ExitManager.GetExitById(currentExitId);
                if (exit != null && exit.transform != null)
                {
                    targetPosition = exit.transform.position;
                    hasTarget = true;
                }
            }

            if (hasTarget)
            {
                var boundary = SimulationManager.Instance.BoundaryManager;
                if (boundary != null && boundary.enforceBoundary && !boundary.IsInside(targetPosition))
                {
                    targetPosition = boundary.ClampToBoundary(targetPosition);
                }
                Vector3 steeringOffset = ComputeSteeringOffset();
                targetPosition += steeringOffset;

                if (panicLevel > 0.7f)
                {
                    if (Time.time - lastJitterTime > panicJitterInterval)
                    {
                        Vector2 jitter2D = Random.insideUnitCircle * panicJitterRadius * panicLevel;
                        jitterOffset = new Vector3(jitter2D.x, 0f, jitter2D.y);
                        lastJitterTime = Time.time;
                    }
                    targetPosition += jitterOffset;
                }
                navAgent.SetDestination(targetPosition);
            }

            UpdateAnimator(navAgent.velocity.magnitude, panicLevel);
        }

        private void CheckExitReached()
        {
            if (string.IsNullOrEmpty(currentExitId) || isEvacuated) return;
            var exit = SimulationManager.Instance.ExitManager.GetExitById(currentExitId);
            if (exit == null || exit.transform == null) return;

            float distance = Vector3.Distance(transform.position, exit.transform.position);
            if (distance <= exitArrivalDistance)
            {
                isEvacuated = true;
                navAgent.isStopped = true;
                SimulationManager.Instance.NotifyEvacuated(this, exit.id);
            }
        }

        private void UpdateAnimator(float speed, float panic)
        {
            if (animator == null) return;
            animator.SetFloat("speed", speed);
            animator.SetFloat("panic", panic);
        }

        private void RecoverIfStuck(float dt)
        {
            if (navAgent == null || navAgent.isStopped || isEvacuated) return;
            if (navAgent.velocity.magnitude <= stuckSpeedThreshold)
            {
                stuckTimer += dt;
            }
            else
            {
                stuckTimer = 0f;
            }

            if (stuckTimer < stuckTimeThreshold) return;

            if (!string.IsNullOrEmpty(currentExitId))
            {
                var exit = SimulationManager.Instance.ExitManager.GetExitById(currentExitId);
                if (exit != null && exit.transform != null)
                {
                    navAgent.SetDestination(exit.transform.position);
                }
            }

            if (NavMesh.SamplePosition(transform.position, out NavMeshHit hit, stuckRepathRadius, NavMesh.AllAreas))
            {
                navAgent.Warp(hit.position);
            }

            stuckTimer = 0f;
        }

        private float GetDynamicDecisionInterval()
        {
            float interval = decisionInterval;
            interval *= Mathf.Lerp(1.2f, 0.6f, panicLevel);
            interval *= Mathf.Lerp(1.0f, 1.4f, fatigue);
            interval *= Mathf.Lerp(1.0f, 1.5f, 1f - visibility);
            if (SimulationManager.Instance != null)
            {
                interval *= Mathf.Max(1f, SimulationManager.Instance.decisionIntervalMultiplier);
            }
            return Mathf.Clamp(interval, 0.5f, 6f);
        }

        private bool ShouldReroute()
        {
            if (Time.time - lastRerouteTime < rerouteCooldown)
            {
                return false;
            }
            if (string.IsNullOrEmpty(currentExitId))
            {
                return true;
            }

            var exitManager = SimulationManager.Instance.ExitManager;
            var hazardManager = SimulationManager.Instance.HazardManager;
            if (exitManager == null) return true;
            var exit = exitManager.GetExitById(currentExitId);
            if (exit == null || exit.transform == null) return true;

            if (exit.isBlocked)
            {
                RegisterAvoidExit(exit.id);
                lastRerouteTime = Time.time;
                return true;
            }

            float hazardIntensity = hazardManager != null ? hazardManager.GetHazardIntensity(exit.transform.position) : 0f;
            float queueRatio = exit.capacity > 0 ? exit.queuedAgents / Mathf.Max(1f, exit.capacity) : exit.queuedAgents;

            bool overloaded = queueRatio > queueTolerance && panicLevel < 0.8f;
            bool hazardous = hazardIntensity > hazardTolerance && panicLevel < 0.9f;

            if ((overloaded || hazardous) && commitmentTimer <= 0.1f)
            {
                RegisterAvoidExit(exit.id);
                lastRerouteTime = Time.time;
                return true;
            }

            return false;
        }

        private ExitManager.ExitRuntime FindBestVisibleExit(ExitManager exitManager)
        {
            if (exitManager == null) return null;

            float vision = Mathf.Max(2f, profile.visionRange * visibility);
            ExitManager.ExitRuntime best = null;
            float bestScore = float.MaxValue;

            foreach (var exit in exitManager.Exits)
            {
                if (exit == null || exit.transform == null) continue;
                if (IsExitAvoided(exit.id)) continue;
                float distance = Vector3.Distance(transform.position, exit.transform.position);
                if (distance > vision && profile.familiarity < 0.5f)
                {
                    continue;
                }

                float hazardPenalty = SimulationManager.Instance.HazardManager != null
                    ? SimulationManager.Instance.HazardManager.GetHazardIntensity(exit.transform.position) * profile.hazardAversion
                    : 0f;
                float queuePenalty = exit.capacity > 0 ? exit.queuedAgents / Mathf.Max(1f, exit.capacity) : exit.queuedAgents;
                float score = distance * (1f + hazardPenalty + queuePenalty);
                if (exit.isBlocked)
                {
                    score *= 5f;
                }

                if (score < bestScore)
                {
                    bestScore = score;
                    best = exit;
                }
            }

            if (best != null)
            {
                return best;
            }

            return exitManager.GetBestExit(profile, transform.position, SimulationManager.Instance.HazardManager, panicLevel);
        }

        private void RegisterAvoidExit(string exitId)
        {
            if (string.IsNullOrEmpty(exitId)) return;
            avoidedExits[exitId] = Time.time + Mathf.Max(1f, avoidExitDuration);
        }

        private bool IsExitAvoided(string exitId)
        {
            if (string.IsNullOrEmpty(exitId)) return false;
            if (!avoidedExits.TryGetValue(exitId, out float until)) return false;
            if (Time.time > until)
            {
                avoidedExits.Remove(exitId);
                return false;
            }
            return true;
        }

        private Vector3 ComputeSteeringOffset()
        {
            if (steeringOffsetStrength <= 0f) return Vector3.zero;

            Vector3 offset = Vector3.zero;
            Vector3 position = transform.position;
            float sample = steeringSampleDistance;

            var hazardManager = SimulationManager.Instance.HazardManager;
            var boundary = SimulationManager.Instance.BoundaryManager;

            if (hazardManager != null)
            {
                float left = hazardManager.GetHazardIntensity(position + Vector3.left * sample);
                float right = hazardManager.GetHazardIntensity(position + Vector3.right * sample);
                float forward = hazardManager.GetHazardIntensity(position + Vector3.forward * sample);
                float back = hazardManager.GetHazardIntensity(position + Vector3.back * sample);
                Vector3 hazardGradient = new Vector3(left - right, 0f, back - forward);
                offset += hazardGradient * hazardAvoidanceWeight;
            }

            float densityLeft = SimulationManager.Instance.GetLocalDensity(position + Vector3.left * sample);
            float densityRight = SimulationManager.Instance.GetLocalDensity(position + Vector3.right * sample);
            float densityForward = SimulationManager.Instance.GetLocalDensity(position + Vector3.forward * sample);
            float densityBack = SimulationManager.Instance.GetLocalDensity(position + Vector3.back * sample);
            Vector3 densityGradient = new Vector3(densityLeft - densityRight, 0f, densityBack - densityForward);
            offset += densityGradient * densityAvoidanceWeight;

            if (boundary != null && boundary.enforceBoundary && !boundary.IsInside(position))
            {
                Vector3 clamped = boundary.ClampToBoundary(position);
                offset += (clamped - position) * boundaryAvoidanceWeight;
            }

            if (offset.sqrMagnitude < 0.001f) return Vector3.zero;
            return offset.normalized * steeringOffsetStrength;
        }
    }
}
