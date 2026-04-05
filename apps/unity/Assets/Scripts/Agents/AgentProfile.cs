using System;
using System.Collections.Generic;
using UnityEngine;
using PeopleFlow.UnitySimulation.Config;

namespace PeopleFlow.UnitySimulation.Agents
{
    [Serializable]
    public class AgentProfile
    {
        public string id = "adult";
        public string label = "Adult";
        public float baseSpeed = 1.4f;
        public float maxSpeed = 2.2f;
        public float reactionTime = 1.5f;
        public float panicSusceptibility = 0.6f;
        public float mobility = 1.0f;
        public float compliance = 0.7f;
        public float groupCohesion = 0.4f;
        public float patience = 0.6f;
        public float familiarity = 0.5f;
        public float visionRange = 12f;
        public float hazardAversion = 0.8f;
        public bool staff = false;
        public bool mobilityLimited = false;
        public bool needsAssistance = false;
        public float exitPreferenceEmergency = 0.5f;
        public float exitPreferenceAccessible = 0.5f;
        public float exitPreferenceNearest = 0.6f;
        public float exitPreferenceKnown = 0.5f;

        public AgentProfile Clone()
        {
            return (AgentProfile)MemberwiseClone();
        }

        public static AgentProfile FromConfig(SimulationProfileConfig config)
        {
            if (config == null) return GetDefault("adult");

            var profile = new AgentProfile
            {
                id = string.IsNullOrEmpty(config.id) ? "custom" : config.id,
                label = string.IsNullOrEmpty(config.label) ? (string.IsNullOrEmpty(config.id) ? "Custom" : config.id) : config.label,
                baseSpeed = config.base_speed > 0 ? config.base_speed : 1.4f,
                maxSpeed = config.max_speed > 0 ? config.max_speed : 2.2f,
                reactionTime = config.reaction_time > 0 ? config.reaction_time : 1.5f,
                panicSusceptibility = config.panic_susceptibility > 0 ? config.panic_susceptibility : 0.6f,
                mobility = config.mobility > 0 ? config.mobility : 1.0f,
                compliance = config.compliance > 0 ? config.compliance : 0.7f,
                groupCohesion = config.group_cohesion > 0 ? config.group_cohesion : 0.4f,
                patience = config.patience > 0 ? config.patience : 0.6f,
                familiarity = config.familiarity > 0 ? config.familiarity : 0.5f,
                visionRange = config.vision_range > 0 ? config.vision_range : 12f,
                hazardAversion = config.hazard_aversion > 0 ? config.hazard_aversion : 0.8f,
                staff = config.staff,
                mobilityLimited = config.mobility_limited,
                needsAssistance = config.needs_assistance,
                exitPreferenceEmergency = config.exit_preference_emergency > 0 ? config.exit_preference_emergency : 0.5f,
                exitPreferenceAccessible = config.exit_preference_accessible > 0 ? config.exit_preference_accessible : 0.5f,
                exitPreferenceNearest = config.exit_preference_nearest > 0 ? config.exit_preference_nearest : 0.6f,
                exitPreferenceKnown = config.exit_preference_known > 0 ? config.exit_preference_known : 0.5f
            };

            profile.ClampValues();
            return profile;
        }

        public void ClampValues()
        {
            baseSpeed = Mathf.Clamp(baseSpeed, 0.2f, 3.5f);
            maxSpeed = Mathf.Clamp(maxSpeed, baseSpeed, 6f);
            reactionTime = Mathf.Clamp(reactionTime, 0f, 20f);
            panicSusceptibility = Mathf.Clamp01(panicSusceptibility);
            mobility = Mathf.Clamp(mobility, 0.2f, 2.5f);
            compliance = Mathf.Clamp01(compliance);
            groupCohesion = Mathf.Clamp01(groupCohesion);
            patience = Mathf.Clamp01(patience);
            familiarity = Mathf.Clamp01(familiarity);
            visionRange = Mathf.Clamp(visionRange, 2f, 50f);
            hazardAversion = Mathf.Clamp01(hazardAversion);
            exitPreferenceEmergency = Mathf.Clamp01(exitPreferenceEmergency);
            exitPreferenceAccessible = Mathf.Clamp01(exitPreferenceAccessible);
            exitPreferenceNearest = Mathf.Clamp01(exitPreferenceNearest);
            exitPreferenceKnown = Mathf.Clamp01(exitPreferenceKnown);
        }

        public static AgentProfile GetDefault(string id)
        {
            foreach (var profile in AgentProfileLibrary.GetDefaults())
            {
                if (profile.id == id) return profile.Clone();
            }
            return AgentProfileLibrary.GetDefaults()[0].Clone();
        }
    }

    public static class AgentProfileLibrary
    {
        public static List<AgentProfile> GetDefaults()
        {
            return new List<AgentProfile>
            {
                new AgentProfile
                {
                    id = "adult",
                    label = "Adult",
                    baseSpeed = 1.4f,
                    maxSpeed = 2.4f,
                    reactionTime = 1.2f,
                    panicSusceptibility = 0.55f,
                    compliance = 0.7f,
                    groupCohesion = 0.4f,
                    patience = 0.6f,
                    familiarity = 0.6f,
                    visionRange = 14f,
                    hazardAversion = 0.8f
                },
                new AgentProfile
                {
                    id = "child",
                    label = "Child",
                    baseSpeed = 1.2f,
                    maxSpeed = 2.0f,
                    reactionTime = 1.8f,
                    panicSusceptibility = 0.8f,
                    compliance = 0.5f,
                    groupCohesion = 0.8f,
                    patience = 0.4f,
                    familiarity = 0.4f,
                    visionRange = 10f,
                    hazardAversion = 0.7f
                },
                new AgentProfile
                {
                    id = "staff",
                    label = "Staff",
                    baseSpeed = 1.5f,
                    maxSpeed = 2.6f,
                    reactionTime = 0.6f,
                    panicSusceptibility = 0.3f,
                    compliance = 0.95f,
                    groupCohesion = 0.6f,
                    patience = 0.8f,
                    familiarity = 0.9f,
                    visionRange = 18f,
                    hazardAversion = 0.9f,
                    staff = true,
                    exitPreferenceEmergency = 0.8f,
                    exitPreferenceKnown = 0.9f
                },
                new AgentProfile
                {
                    id = "mobility_limited",
                    label = "Mobility Limited",
                    baseSpeed = 0.8f,
                    maxSpeed = 1.4f,
                    reactionTime = 2.4f,
                    panicSusceptibility = 0.65f,
                    compliance = 0.6f,
                    groupCohesion = 0.7f,
                    patience = 0.9f,
                    familiarity = 0.7f,
                    visionRange = 10f,
                    hazardAversion = 0.85f,
                    mobility = 0.6f,
                    mobilityLimited = true,
                    needsAssistance = true,
                    exitPreferenceAccessible = 0.9f,
                    exitPreferenceEmergency = 0.4f
                }
            };
        }
    }
}
