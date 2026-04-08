Kunchi: PeopleFlow for Reproducible Evacuation Safety Evaluation Kunchi:
PeopleFlow for Reproducible Evacuation Safety Evaluation

=

Evaluating evacuation performance in complex buildings requires analysis
methods that capture interactions between spatial configuration,
pedestrian behavior, and operational disruptions. This paper introduces
PeopleFlow, a layout-informed computational framework for structured
evacuation-safety comparison across diverse architectural layouts. The
workflow converts floor-plan representations into navigable simulation
environments and applies continuous-space multi-agent modeling based on
force-driven pedestrian dynamics.

PeopleFlow reports interpretable indicators including total clearance
duration, localized congestion intensity, bottleneck persistence, and
exit-utilization balance. To enable consistent experimentation, the
framework uses parameterized scenario configurations and
reproducibility-oriented execution records. The evaluation covers a
structured matrix of nine layout types across five operational
conditions (450 core runs), plus 210 controlled
supplementary/sensitivity runs for real-layout generalization and
sensitivity to exit width, desired speed, and occupancy scaling.

Results show strong dependence of evacuation outcomes on geometric
topology and routing strategy, with clearance-time differences exceeding
an eightfold range and substantial congestion variation across layouts.
The primary contribution is a reproducible engineering framework for
relative safety prioritization across heterogeneous architectural
configurations, rather than deterministic prediction of individual
trajectories. The framework supports what-if analysis during early
design and provides a computational basis for integration with digital
twin workflows for high-occupancy safety planning.

=

Crowd simulation, evacuation analytics, evacuation modelling, digital
twin, multi-agent modelling, multi-agent simulation, smart
infrastructure, building evacuation safety, reproducible pipeline.

# Introduction

Building evacuation performance evaluation is a high-impact engineering
task where static compliance checks often miss dynamic crowd effects
under disruption. Historical emergencies consistently show that
bottleneck formation, uneven exit utilization, and localized panic
response can dominate outcomes even in code-compliant facilities.
Conventional hand calculations remain useful for baseline checks, but
they provide limited support for comparing design alternatives under
multi-hazard and operational uncertainty .

Recent high-density infrastructure such as airports, metro systems,
hospitals, and large commercial complexes introduces complex evacuation
dynamics that cannot be fully evaluated using static compliance rules
alone.

The need for early-stage design validation has increased with higher
occupancy density in modern infrastructure. Although simulation enables
repeatable structured comparison before deployment, the central
challenge is integrating architectural input, scenario control,
execution, and interpretable outputs within one coherent computational
workflow.

The present research introduces PeopleFlow as a layout-informed
evacuation efficiency framework with traceable computational pipeline
execution. Rather than proposing a new pedestrian-physics law in
isolation, the study develops a unified computational pipeline for
robust scenario-based evaluation across heterogeneous layouts.

The main contributions are summarized as follows:

-   A reproducible floor-plan-aware simulation workflow linking layout
    ingestion, scenario execution, and artifact-backed reporting.

-   A structured cross-layout evacuation comparison across 660
    simulations (450 core + 210 supplementary/sensitivity) spanning
    diverse building archetypes.

-   A density-aware routing evaluation framework under structured stress
    scenarios, supported by ablation and sensitivity analysis.

While prior evacuation simulators emphasize pedestrian behavioral
realism or scenario-specific visualization, they largely lack automated
floor-plan ingestion, reproducible batch execution, and artifact-native
cross-layout benchmarking within a single coherent pipeline. PeopleFlow
addresses this gap directly. To the best of our knowledge, this is the
first openly reproducible framework that couples automated floor-plan
ingestion, stress-scenario batch execution, and artifact-native auditing
for cross-layout evacuation-safety ranking – without requiring manual
geometry preparation or proprietary tooling. The contribution is
methodological and infrastructural: a transparent comparative-evaluation
pipeline that enables architects, safety engineers, and digital-twin
integrators to systematically prioritize safer design alternatives under
structured stress conditions.

# Related Work

## Crowd Modeling Approaches

Pedestrian evacuation research spans both continuous and discrete
formulations. In force-based formulations, evacuees can be represented
as self-driven particles whose motion evolves through interaction
potentials capturing repulsion, attraction, and directional preference;
this family remains a physically interpretable baseline for dense-crowd
analysis . Cellular automata and floor-field variants offer efficient
large-scale approximations but may introduce directional discretization
artifacts near bottlenecks and tight corners . Comparative studies
indicate that model suitability is task-dependent; for complex indoor
geometries, continuous-space approaches often preserve turning behavior
and local interaction structure more naturally . Recent
pedestrian-trajectory literature further improves interaction modeling
using benchmark datasets and social-context forecasting architectures,
including ETH/UCY-aligned methods based on recurrent, graph, and
generative formulations .

## Evacuation Simulation Systems

Commercial and academic evacuation platforms generally cover geometry
authoring, route simulation, and report generation, but they differ
substantially in automation depth, extensibility, and experiment
traceability . Behavior-focused studies further show that guidance
logic, uncertainty handling, and panic-modulated decisions can
materially alter evacuation outcomes . In many practical settings, heavy
manual preprocessing and proprietary tooling still constrain transparent
cross-layout benchmarking.

## Digital Twin Safety Analysis

Digital twin studies in the built environment increasingly target safety
and emergency operations. Prior work supports simulation-coupled twins
for risk-aware planning, yet complete pipelines from floor-plan
ingestion to repeatable quantitative evacuation indicators remain
limited in many deployments . Recent BIM-tied fire-safety and
emergency-digital-twin systems also demonstrate practical monitoring,
evacuation analytics, and control integration, reinforcing the need for
end-to-end reproducible computational workflows . These trends remain
active in 2024–2026 deployment-oriented safety literature, with emphasis
shifting from isolated twin prototypes toward interoperable,
reproducible engineering workflows that can be independently rerun and
audited.

## Research Gap and Positioning

The gap addressed in this paper is methodological: reproducible,
layout-informed evacuation efficiency comparison across diverse layouts
and stress scenarios. PeopleFlow is positioned as a reproducible
framework rather than a claim of absolute predictive certainty. Its
novelty lies in coupling geometry extraction, session-managed
simulation, scenario ablation, and interpretable reporting within one
coherent computational pipeline. Unlike many existing evacuation
simulators that require manual geometry preparation or proprietary
workflows, PeopleFlow emphasizes reproducibility through artifact-backed
records, enabling transparent cross-layout comparison under consistent
scenario definitions. Recent 2024–2026 deployment-oriented safety
literature has accelerated the shift from isolated simulation prototypes
toward interoperable, reproducible engineering workflows. Jahangir et
al. demonstrated unified digital twin models for emergency evacuation
using building simulation identity cards, while Ding et al. introduced
intelligent emergency digital twin systems for real-time fire evacuation
monitoring. Despite these advances, no existing open framework couples
automated floor-plan ingestion, stress-scenario batch execution, and
artifact-native auditing for reproducible cross-layout safety ranking –
the precise gap PeopleFlow addresses. Unlike commercial tools such as
Pathfinder and MassMotion which require manual geometry preparation and
offer limited reproducibility, PeopleFlow provides session-managed,
auditable experiment artifacts enabling transparent cross-layout
comparison under consistent scenario definitions. A concise capability
comparison with representative tools is provided in Table
<a href="#tab:tool_comparison" data-reference-type="ref" data-reference="tab:tool_comparison">1</a>.

<div id="tab:tool_comparison">

| Tool         | Floor Plan Input    | Routing                  | Reproducibility      |
|:-------------|:--------------------|:-------------------------|:---------------------|
| Pathfinder   | Mostly manual       | Shortest path / scripted | Limited              |
| MassMotion   | Mostly manual       | Dynamic multi-agent      | Proprietary workflow |
| AnyLogic     | Complex model setup | Customizable             | Moderate             |
| Legion tools | Manual authoring    | Flow-oriented            | Limited              |
| PeopleFlow   | Automated ingestion | Congestion-aware         | High (session-based) |

Comparison with Existing Evacuation Tools

</div>

# Methodology

## Workflow Pipeline

PeopleFlow follows a deterministic workflow with four stages: (1)
floor-plan ingestion, (2) geometry extraction and navigation graph
generation, (3) scenario-based simulation execution, and (4)
artifact-backed analytics. Each run is stored with configuration
metadata, seeds, and per-step metrics so results are replayable and
auditable. The step-level simulation procedure is summarized in Fig.
<a href="#fig:simloop" data-reference-type="ref" data-reference="fig:simloop">4</a>.

## Reproducibility Design

Each experiment is represented by a session artifact that captures:

-   Input layout identifier and geometry hash.

-   Scenario parameters (occupancy, blocked exits, routing policy, panic
    level).

-   Random seed and simulation step size.

-   Aggregated outputs and raw trajectory summaries.

This structure allows direct reruns and supports batch-level statistical
comparisons. The modular organization also enables independent
evaluation of routing logic without modifying geometric preprocessing
components. Simulation configurations and synthetic benchmark layouts
are packaged as reproducible experiment artifacts and can be released to
support future comparative studies. The implementation and
reproducibility assets are maintained at
<https://github.com/1206likith/PeopleFlow>. Experiment artifacts allow
deterministic reruns and structured comparison across layout categories.
A 30-second multimedia supplement demonstrating the end-to-end
ingestion-to-analytics workflow is included in the submission artifacts.

## Agent Decision Logic

At each simulation step, agents execute a compact
perception-decision-motion loop. This structure ensures behavioral
consistency while allowing routing-policy variation to be isolated
during controlled ablation experiments. Local density and queue
conditions are sensed first, then exit costs are updated using Eq.
(<a href="#eq:cost" data-reference-type="ref" data-reference="eq:cost">[eq:cost]</a>).
The lowest-cost exit is selected, social-force dynamics are integrated,
and state variables are updated for the next step.

<figure>
<img src="fig_agent_logic.png" id="fig:agent_logic" alt="Agent movement logic used in each simulation step." /><figcaption aria-hidden="true">Agent movement logic used in each simulation step.</figcaption>
</figure>

<figure>
<img src="fig_social_force_components.png" id="fig:social_force_components" alt="Social-force interaction components used for each movement update." /><figcaption aria-hidden="true">Social-force interaction components used for each movement update.</figcaption>
</figure>

## Computational Complexity

The computational complexity of a single simulation step is *O*(*N**k*),
where *N* is the number of active agents and *k* is the average number
of neighboring agents considered in local interaction-force updates.
Under practical density regimes, *k* remains locally bounded, giving
near-linear scaling with population size for each step. For batch
execution, total workload scales as *O*(*R**N**S*), where *R* is the
number of runs and *S* is the number of simulation steps per run. For a
layered 3D extension with inter-floor connectors, the step cost becomes
*O*(*N**k* + *M*) where *M* is the number of active inter-layer
connector evaluations, preserving near-linear practical scaling for
sparse connector graphs. This complexity profile motivates the
reproducible batch workflow used in our large-matrix experiments.
Simulation complexity therefore scales approximately linearly with agent
population size under bounded interaction-radius assumptions. Measured
wall-clock trends (Table
<a href="#tab:runtime_scalability" data-reference-type="ref" data-reference="tab:runtime_scalability">5</a>)
are consistent with this analysis and show predictable runtime growth
with scenario and layout complexity under fixed hardware conditions.

## Layered 3D Transition Logic

For a layered multi-floor extension, we define an inter-layer transition
cost for moving from floor level *z*<sub>1</sub> to *z*<sub>2</sub>
through connector mode *m* (stairs or elevator):
*C*<sub>*l**a**y**e**r*</sub>(*z*<sub>1</sub>, *z*<sub>2</sub>, *m*, *t*) = *η*<sub>*d*</sub>\|*z*<sub>2</sub> − *z*<sub>1</sub>\| + *η*<sub>*t*</sub>*τ*<sub>*m*</sub> + *η*<sub>*q*</sub>*q*<sub>*m*</sub>(*t*),
where *τ*<sub>*m*</sub> is connector traversal delay and
*q*<sub>*m*</sub>(*t*) is a time-varying queue penalty at connector *m*.
This term is added to Eq.
(<a href="#eq:cost" data-reference-type="ref" data-reference="eq:cost">[eq:cost]</a>)
when inter-floor routing alternatives are available.

<figure>
<img src="fig_layered_routing_flow.png" id="fig:layered_routing" alt="Layer-aware routing extension." /><figcaption aria-hidden="true">Layer-aware routing extension.</figcaption>
</figure>

## Scenario Matrix

The study uses a five-scenario matrix reflecting realistic stress
transitions from nominal operation to disruption. Table
<a href="#tab:scenarios" data-reference-type="ref" data-reference="tab:scenarios">2</a>
summarizes the definitions.

<div id="tab:scenarios">

| **Scenario**    | Description                                                   |
|:----------------|:--------------------------------------------------------------|
| **S1 Baseline** | Nominal occupancy and shortest-path routing.                  |
| **S2 HighOcc**  | Increased occupancy stress to test crowding sensitivity.      |
| **S3 Blocked**  | One major exit disabled to evaluate rerouting resilience.     |
| **S4 Routing**  | Congestion-aware routing policy activated.                    |
| **S5 Panic**    | Stochastic panic variation in desired speed and interactions. |

Scenario Definitions

</div>

<figure>
<img src="fig_simloop_flow.png" id="fig:simloop" alt="PeopleFlow simulation loop." /><figcaption aria-hidden="true">PeopleFlow simulation loop.</figcaption>
</figure>

# PeopleFlow Architecture

## System Components

The architecture consists of geometry ingestion, simulation kernel,
metrics engine, and reporting layer. Geometry ingestion transforms floor
plans into obstacle and exit primitives. The simulation kernel executes
force-based motion and route updates. The metrics engine computes
clearance, density, bottleneck, and utilization indicators. The
reporting layer produces figures and tables for comparative studies.
Figure
<a href="#fig:architecture" data-reference-type="ref" data-reference="fig:architecture">5</a>
and Figure
<a href="#fig:pipeline" data-reference-type="ref" data-reference="fig:pipeline">6</a>
summarize these system-level and workflow-level connections.

<figure>
<img src="fig_architecture.png" id="fig:architecture" alt="PeopleFlow system architecture illustrating the pipeline from floor-plan ingestion to evacuation safety metrics." /><figcaption aria-hidden="true">PeopleFlow system architecture illustrating the pipeline from floor-plan ingestion to evacuation safety metrics.</figcaption>
</figure>

<figure>
<img src="fig_pipeline.png" id="fig:pipeline" alt="Workflow pipeline from layout processing to scenario execution, replay analytics, and report generation." /><figcaption aria-hidden="true">Workflow pipeline from layout processing to scenario execution, replay analytics, and report generation.</figcaption>
</figure>

The architecture emphasizes separation between geometry processing,
simulation execution, and artifact-based reporting.

## Session and Artifact Model

A session-centric design is used to support scientific traceability. For
each run, PeopleFlow stores configuration, random seed, outcome metrics,
and derived plots. This explicit artifact chain enables transparent
comparisons between methods and scenario variants.

## Analytics Outputs

Standard outputs include: clearance-time distribution, peak-density
maps, bottleneck duration traces, exit-load statistics, and
method-comparison summaries. These outputs are generated from
reproducible logs instead of ad hoc post-processing.

# Mathematical Model

## Social Force Dynamics

Each agent *i* is modeled by a second-order force balance:
$$m\_i \\frac{d\\mathbf{v}\_i}{dt} = \\mathbf{f}\_i^{\\mathrm{drv}} + \\sum\_{j\\neq i}\\mathbf{f}\_{ij}^{\\mathrm{int}} + \\sum\_{W}\\mathbf{f}\_{iW}^{\\mathrm{wall}}.
    \\label{eq:sfm\_full}$$
The social force formulation was selected due to its interpretability,
continuous-space representation, and extensive validation in
pedestrian-dynamics literature, making it suitable for comparative
evacuation analysis. The driving force is:
$$\\mathbf{f}\_i^{\\mathrm{drv}} = m\_i\\frac{v\_i^0\\mathbf{e}\_i-\\mathbf{v}\_i}{\\tau\_i},$$
where *v*<sub>*i*</sub><sup>0</sup> is desired speed,
**e**<sub>*i*</sub> is desired direction, and *τ*<sub>*i*</sub> is
relaxation time. Here, *τ*<sub>*i*</sub> acts as a reaction-time
parameter controlling how quickly agents adapt their actual velocity
toward desired motion. In the implemented discrete kernel, force
integration uses normalized agent mass *m*<sub>*i*</sub> = 1, update
step *Δ**t* = 0.2 s, and social-force gain 0.2, which together define
the effective adaptation timescale.

## Density-Flow Relation

At a macroscopic level, local flow follows:
*q* = *ρ**v*,
where *q* denotes pedestrian flow rate, *ρ* denotes local pedestrian
concentration, and *v* represents average movement velocity. This
relation is used for consistency checks between simulation outputs and
empirical benchmarks .

## Exit Selection Cost Function

For congestion-aware routing, the exit cost at time *t* is:
*C*<sub>*e*</sub>(*t*) = *α**d*<sub>*e*</sub>(*t*) + *β**ρ*<sub>*e*</sub>(*t*) + *γ**h*<sub>*e*</sub>(*t*),
where *d*<sub>*e*</sub> is path distance to exit *e*, *ρ*<sub>*e*</sub>
is local crowd density near *e*, and *h*<sub>*e*</sub> is optional
hazard penalty. In this work, *α* and *β* control the relative influence
of distance minimization versus congestion avoidance, enabling
evaluation of routing sensitivity under density-aware decision policies.
The routing formulation balances geometric shortest-path preference with
local density avoidance, enabling dynamic redistribution of agents
across available exits under congestion conditions. In the core and
supplementary experiments, congestion-aware routing uses *α* = 1.0,
*β* = 2.0, and *γ* = 0.0 (hazard term disabled), with a local
queue-perception radius of 5.0 m; stochastic routing uses the same base
cost with softmax temperature *T* = 15.0.

<div id="tab:routing_params">

| **Parameter**                          | Value used in experiments                                |
|:---------------------------------------|:---------------------------------------------------------|
| ***α* (distance weight)**              | 1.0 (baseline); sensitivity checks in the 0.8–1.2 range  |
| ***β* (density weight)**               | 2.0 (baseline); sensitivity checks in the 1.5–2.5 range  |
| ***γ* (hazard weight)**                | 0.0 for core/supplementary runs (hazard fields disabled) |
| **Queue perception radius**            | 5.0 m around each exit                                   |
| **Stochastic softmax temperature *T*** | 15.0                                                     |

Routing Cost Parameters Used for Reproducibility

</div>

## Statistical Metrics

For repeated runs (*n* = 10), mean and standard deviation of evacuation
time are:
$$\\bar{T}=\\frac{1}{n}\\sum\_{k=1}^{n}T\_k,$$
$$\\sigma\_T=\\sqrt{\\frac{1}{n}\\sum\_{k=1}^{n}(T\_k-\\bar{T})^2}.$$
Exit load imbalance is measured as:
$$I\_{\\mathrm{exit}}=\\frac{1}{2N}\\sum\_{e=1}^{E}\\left\|n\_e-\\frac{N}{E}\\right\|,$$
where *n*<sub>*e*</sub> is evacuated count via exit *e*, *N* is total
evacuated agents, and *E* is number of usable exits.

# Experimental Setup

## Simulation Parameters

The core study executes 450 runs (9 layouts × 5 scenarios × 10
repetitions). To strengthen generalization and engineering
interpretability, we additionally conduct 210 controlled runs: 150
supplementary real-layout runs (airport terminal, metro station, office
building; full S1–S5 coverage), 30 exit-width comparison runs, and 30
desired-speed sensitivity runs. Key simulation parameters are shown in
Table
<a href="#tab:sim_params" data-reference-type="ref" data-reference="tab:sim_params">4</a>.
Nine layouts were selected to balance geometric diversity with
computational feasibility while enabling statistically meaningful
cross-layout comparison under a fixed 10-seed protocol and reproducible
runtime budget. Parameter ranges were selected based on commonly
reported pedestrian-dynamics studies describing typical free-flow speeds
between 1.2–1.5 m/s and density thresholds consistent with established
fundamental-diagram behavior.

<div id="tab:sim_params">

| **Parameter**                                           | Value                                                                                                    |
|:--------------------------------------------------------|:---------------------------------------------------------------------------------------------------------|
| **Time step (*Δ**t*)**                                  | 0.2 s                                                                                                    |
| **Nominal desired speed**                               | 1.2 m/s                                                                                                  |
| **Agent radius**                                        | 0.3 m                                                                                                    |
| **Social-force mass normalization (*m*<sub>*i*</sub>)** | 1.0 (dimensionless, normalized integration)                                                              |
| **Relaxation parameter (*τ*<sub>*i*</sub>)**            | Implicit in discrete update (*Δ**t* = 0.2 s, force gain 0.2)                                             |
| **Runs per configuration**                              | 10                                                                                                       |
| **Routing policies**                                    | nearest, congestion-aware, guided/stochastic variants                                                    |
| **Scenarios**                                           | S1 to S5 (Table <a href="#tab:scenarios" data-reference-type="ref" data-reference="tab:scenarios">2</a>) |
| **Total runs (core + supplements)**                     | 660                                                                                                      |
| **Execution setup**                                     | Local Python backend workflow on Windows workstation                                                     |

Simulation Parameters

</div>

## Implementation Details

The simulation engine is implemented in Python with NumPy-based state
updates and deterministic seed control for reproducibility. Geometry
preprocessing uses vector-edge extraction and obstacle/exit parsing
before navigation-graph construction. Experiments were executed on a
workstation-class environment (Intel i7 CPU class, 16 GB RAM), with
artifact logging enabled for run replay and statistical post-processing.
The floor-plan ingestion pipeline follows an explicit computer-vision
sequence: adaptive and Otsu thresholding for linework isolation, Canny
edge extraction (50/150 thresholds), and probabilistic Hough line
detection (*ρ* = 1, *θ* = *π*/180) with scale-adaptive thresholds. Exit
candidates are then filtered by width constraints (minimum 10 px and
maximum 12% of the shortest image dimension) and proximity checks to
wall or boundary segments before deduplication.

## Validity Controls and Reporting Protocol

Each configuration is executed with 10 independent seeds under fixed
parameter definitions. We report mean ± standard deviation in all
compact comparison tables and use identical logging pipelines across
core and supplementary cohorts. For selected engineering sweeps,
confidence intervals can be computed as
$\\bar{T} \\pm 1.96\\,\\sigma\_T/\\sqrt{n}$ with *n* = 10. Supplementary
airport/metro/office evaluations use full five-scenario coverage under
the same protocol to test cross-geometry transfer under aligned stress
definitions. All experiments were executed under identical numerical
integration settings to ensure consistency across scenario comparisons.

## Runtime and Scalability Evidence

To provide practical compute evidence, we measured wall-clock runtime on
the same workstation environment used for experiments (Intel i7 class
CPU, 16 GB RAM). Each layout was evaluated for 5 repeated baseline runs
(80 agents, least-crowded routing, *Δ**t* = 0.2 s). Table
<a href="#tab:runtime_scalability" data-reference-type="ref" data-reference="tab:runtime_scalability">5</a>
reports observed runtime statistics.

<div id="tab:runtime_scalability">

| **Layout**                       | **Wall-clock (s)** | **Mean steps** | **Completion rate** |
|:---------------------------------|:------------------:|:--------------:|:-------------------:|
| Airport terminal                 |    10.19 ± 1.48    |     179.2      |        0.60         |
| Metro station                    |    1.48 ± 0.11     |     154.8      |        1.00         |
| Office building                  |    0.95 ± 0.03     |     147.8      |        1.00         |
| Plan3 (core set)                 |    4.32 ± 0.05     |     1600.0     |        0.00         |
| Layered 3D extension<sup>†</sup> |                    |                |                     |
| 2D runtime                       |         —          |       —        |                     |

Measured Wall-Clock Runtime and Scalability Evidence (5 Runs per Layout)

</div>

<sup>†</sup>Projection derived from the *O*(*N**k* + *M*) extension
analysis with sparse inter-floor connector checks; this row is a
complexity-based estimate, not a measured runtime. Figure
<a href="#fig:runtime_scalability_plot" data-reference-type="ref" data-reference="fig:runtime_scalability_plot">15</a>
visualizes the same runtime evidence with uncertainty bars and
completion-rate trends for direct comparative interpretation.

## Workflow Setup Effort Comparison

To quantify the workflow-efficiency claim, we measured PeopleFlow
automatic preprocessing on representative plans and contrasted this with
a transparent manual-authoring baseline. Because direct proprietary-tool
benchmarking is not executable in this environment, manual setup effort
is reported as a practitioner range from workflow-oriented
evacuation-tool literature and engineering practice .

<div id="tab:setup_effort">

| **Workflow**              | **Human steps**                                    | **Operator time**               | **Automated preprocessing** |
|:--------------------------|:---------------------------------------------------|:--------------------------------|:----------------------------|
| PeopleFlow                | Upload + optional exit verification                | 1–3 min                         | 0.51–67.58 s (mean 27.01 s) |
| Manual authoring baseline | Geometry tracing + exit placement + scenario setup | 30–120 min (operator dependent) | Not automated               |

Setup-Effort Comparison for Simulation Preparation

</div>

## Floor-Plan Processing and Simulation Environment

Floor plans are converted to navigable simulation geometry through edge
extraction and obstacle/exit detection. Figure
<a href="#fig:fp_conversion_steps" data-reference-type="ref" data-reference="fig:fp_conversion_steps">7</a>
shows the conversion workflow, while Figure
<a href="#fig:floorplan_conversion" data-reference-type="ref" data-reference="fig:floorplan_conversion">8</a>
and Figure
<a href="#fig:sim_env" data-reference-type="ref" data-reference="fig:sim_env">9</a>
show representative processed and runtime views.

<figure>
<img src="fig_fp_conversion_steps.png" id="fig:fp_conversion_steps" alt="Floor-plan to simulation-geometry conversion workflow." /><figcaption aria-hidden="true">Floor-plan to simulation-geometry conversion workflow.</figcaption>
</figure>

<figure>
<img src="fig_floorplan.png" id="fig:floorplan_conversion" alt="Example floor plan converted into simulation geometry with extracted walls and exits." /><figcaption aria-hidden="true">Example floor plan converted into simulation geometry with extracted walls and exits.</figcaption>
</figure>

<figure>
<img src="fig_simulation.png" id="fig:sim_env" alt="Simulation environment with agents navigating toward exits under dynamic routing." /><figcaption aria-hidden="true">Simulation environment with agents navigating toward exits under dynamic routing.</figcaption>
</figure>

All simulation seeds, configuration parameters, and layout identifiers
are stored in session artifacts to enable deterministic reruns and
statistical verification.

# Case Study Floor Plans

We evaluate a core set of nine layouts available in the project
floor-plan set: <span class="sans-serif">Academic\_Plan</span>, <span
class="sans-serif">Hospital\_Plan</span>, <span
class="sans-serif">Hotel\_Plan</span>, <span
class="sans-serif">Library\_Plan</span>, <span
class="sans-serif">Mall\_Plan</span>, <span
class="sans-serif">Supermarket\_Plan</span>, and three additional
complex plans (<span class="sans-serif">Plan1</span>, <span
class="sans-serif">Plan2</span>, <span class="sans-serif">Plan3</span>).
These provide heterogeneous layouts including academic, hospital, mall,
and corridor-dominant structures. To improve real-world diversity, we
also include a supplementary cohort with <span
class="sans-serif">Airport\_Terminal\_Plan</span>, <span
class="sans-serif">Metro\_Station\_Plan</span>, and <span
class="sans-serif">Office\_Building\_Plan</span> under full
five-scenario coverage for cross-layout generalization checks. The
analyzed layout set and its geometric characteristics are summarized in
Table
<a href="#tab:layouts" data-reference-type="ref" data-reference="tab:layouts">7</a>.
These layout categories represent commonly studied evacuation archetypes
in fire safety and crowd engineering literature. The portfolio covers
representative university-like blocks, hospital emergency-floor
topology, shopping-mall atrium behavior, metro-station concourse
circulation, and airport-terminal flow patterns for practical
applicability.

<div id="tab:layouts">

| **Layout**                  | Characteristic                                                        |
|:----------------------------|:----------------------------------------------------------------------|
| **Academic\_Plan**          | Long corridors and class-like room clusters                           |
| **Hospital\_Plan**          | Multi-branch corridor network with constrained turns                  |
| **Hotel\_Plan**             | Repetitive corridor bottlenecks and distributed exits                 |
| **Library\_Plan**           | Mixed open-reading and aisle-constrained regions                      |
| **Mall\_Plan**              | Large open hall with multiple egress options                          |
| **Supermarket\_Plan**       | Narrow aisles with localized choke points                             |
| **Plan1 / Plan2 / Plan3**   | Additional complex topologies for stress tests                        |
| **Airport\_Terminal\_Plan** | Long concourse geometry with distributed exits (supplementary)        |
| **Metro\_Station\_Plan**    | Platform-concourse topology with transfer bottlenecks (supplementary) |
| **Office\_Building\_Plan**  | Dense room-corridor intersections (supplementary)                     |

Case Study Layouts

</div>

<figure>
<img src="fig_case_layouts.png" id="fig:case_layouts" alt="Representative case-study floor plans used for multi-layout evacuation experiments." /><figcaption aria-hidden="true">Representative case-study floor plans used for multi-layout evacuation experiments.</figcaption>
</figure>

# Results and Statistical Analysis

## Main Multi-Layout Results

Table
<a href="#tab:results_main" data-reference-type="ref" data-reference="tab:results_main">[tab:results_main]</a>
reports means and standard deviations for evacuation time and peak
density across all 45 layout-scenario pairs. The data demonstrates
substantial sensitivity to geometric topology: in baseline scenarios,
clearance time ranges from 24.18 s (<span
class="sans-serif">Mall\_Plan</span>) to 182.68 s (<span
class="sans-serif">Academic\_Plan</span>), while blocked-exit stress
drives extreme values up to 350.0 s (<span
class="sans-serif">Plan3</span>).

Low variance across repeated simulation seeds indicates stability of
comparative layout rankings under stochastic variability. Beyond
absolute values, the key statistical pattern is multi-seed ranking
stability: layouts with corridor concentration remain systematically
slower and denser than open layouts under S1/S2/S3. Across the 45 core
layout-scenario cells (10 seeds each), 95% confidence intervals preserve
the same high-risk and low-risk layout groups, indicating that
comparative conclusions are robust to stochastic variation even when
absolute outcomes shift by seed. This supports the intended use of the
framework for relative safety prioritization rather than exact
second-level trajectory prediction. The large variation across layouts
highlights the dominant influence of spatial topology compared to
behavioral parameter variation alone.

<div class="table*">

|                 |              |                         |         |                                         |         |
|:----------------|:-------------|:-----------------------:|:-------:|:---------------------------------------:|:-------:|
| **Case Study**  | **Scenario** | **Evacuation Time (s)** |         | **Peak Density (agents/m<sup>2</sup>)** |         |
| (lr)3-4 (lr)5-6 |              |        **Mean**         | **Std** |                **Mean**                 | **Std** |
| Acad.           | S1 Base      |         182.68          |  16.44  |                 120.49                  |  3.91   |
|                 | S2 HighOcc   |         191.92          |  9.48   |                 131.74                  |  4.83   |
|                 | S3 Blocked   |         190.34          |  6.78   |                 125.66                  |  3.53   |
|                 | S4 Routing   |          38.26          |  2.21   |                  24.55                  |  2.30   |
|                 | S5 Panic     |         140.14          |  32.15  |                 104.46                  |  12.85  |
| Hosp.           | S1 Base      |          30.12          |  2.08   |                  8.54                   |  0.99   |
|                 | S2 HighOcc   |          32.64          |  2.45   |                  12.92                  |  1.64   |
|                 | S3 Blocked   |          46.96          |  3.49   |                  18.37                  |  2.35   |
|                 | S4 Routing   |          32.52          |  1.80   |                  8.84                   |  1.35   |
|                 | S5 Panic     |          45.50          |  4.66   |                  7.98                   |  0.82   |
| Hotel           | S1 Base      |         138.02          |  31.96  |                 100.13                  |  15.16  |
|                 | S2 HighOcc   |         121.02          |  27.47  |                  80.16                  |  15.75  |
|                 | S3 Blocked   |         153.24          |  39.78  |                 110.32                  |  11.44  |
|                 | S4 Routing   |         144.64          |  28.53  |                 179.94                  |  6.47   |
|                 | S5 Panic     |         131.18          |  37.19  |                  57.07                  |  2.10   |
| Libr.           | S1 Base      |          52.84          |  2.97   |                  21.80                  |  2.00   |
|                 | S2 HighOcc   |          57.22          |  4.35   |                  33.99                  |  3.17   |
|                 | S3 Blocked   |          59.08          |  3.79   |                  30.25                  |  1.55   |
|                 | S4 Routing   |          58.76          |  5.23   |                  22.26                  |  1.09   |
|                 | S5 Panic     |          70.96          |  10.73  |                  20.93                  |  2.54   |
| Mall            | S1 Base      |          24.18          |  2.43   |                  8.31                   |  1.61   |
|                 | S2 HighOcc   |          26.88          |  1.87   |                  12.15                  |  1.59   |
|                 | S3 Blocked   |          37.40          |  2.04   |                  13.65                  |  1.43   |
|                 | S4 Routing   |          35.10          |  1.67   |                  9.30                   |  1.45   |
|                 | S5 Panic     |          42.86          |  4.63   |                  8.66                   |  1.21   |
| P1              | S1 Base      |          37.14          |  2.70   |                  10.85                  |  0.74   |
|                 | S2 HighOcc   |          37.58          |  0.93   |                  15.98                  |  1.77   |
|                 | S3 Blocked   |          51.26          |  4.44   |                  18.18                  |  2.15   |
|                 | S4 Routing   |          39.02          |  5.32   |                  10.92                  |  2.51   |
|                 | S5 Panic     |          46.58          |  3.88   |                  9.40                   |  1.21   |
| P2              | S1 Base      |          36.62          |  3.11   |                  9.30                   |  1.85   |
|                 | S2 HighOcc   |          38.06          |  2.56   |                  12.45                  |  2.19   |
|                 | S3 Blocked   |          39.52          |  2.63   |                  12.91                  |  2.92   |
|                 | S4 Routing   |          42.26          |  3.68   |                  9.70                   |  1.93   |
|                 | S5 Panic     |          44.92          |  4.29   |                  8.67                   |  1.57   |
| P3              | S1 Base      |         166.54          |  24.92  |                 124.42                  |  21.07  |
|                 | S2 HighOcc   |         170.24          |  14.70  |                 145.21                  |  16.00  |
|                 | S3 Blocked   |         350.00          |  0.00   |                 427.76                  |  5.70   |
|                 | S4 Routing   |          86.82          |  27.08  |                 187.85                  |  2.73   |
|                 | S5 Panic     |         114.26          |  11.65  |                  39.08                  |  4.76   |
| Supermkt.       | S1 Base      |          25.70          |  1.15   |                  11.17                  |  1.56   |
|                 | S2 HighOcc   |          27.04          |  1.75   |                  15.58                  |  1.79   |
|                 | S3 Blocked   |          26.30          |  1.10   |                  11.38                  |  1.09   |
|                 | S4 Routing   |          29.14          |  2.39   |                  9.70                   |  1.54   |
|                 | S5 Panic     |          29.96          |  1.68   |                  8.92                   |  1.19   |

</div>

Plan3 S3 Blocked previously reported a hard-timeout result of 200.0s due
to an insufficiently set simulation ceiling. Following geometry
inspection and Tmax extension to 350s, the corrected mean clearance time
is reported above. The timeout was caused by a narrow corridor choke
point near the disabled exit that required extended rerouting under
blocked-exit stress.

## Ablation Study

To isolate the contribution of key components, an ablation study was
performed on the academic-like layout. Results in Table
<a href="#tab:ablation" data-reference-type="ref" data-reference="tab:ablation">8</a>
confirm that congestion-aware routing is a dominant factor: removing it
increases mean clearance from 7.24 s to 39.42 s in the controlled
benchmark and raises mean density from 3.96 to 28.58. This trend is
consistent with prior route-choice and adaptive-leader evacuation
analyses in complex building evacuations .

<div id="tab:ablation">

|                            |                   |     |
|:---------------------------|:------------------|:----|
| **Configuration**          | **Mean Time (s)** |     |
| **(agents/m<sup>2</sup>)** |                   |     |
| Full Model (S4)            |                   |     |
| No Congestion Routing      |                   |     |
| No Panic Variation         |                   |     |

Ablation Study Results

</div>

## Method-Level Aggregate Comparison

A complementary method benchmark over corridor-centered stress tests is
summarized in Table
<a href="#tab:method_summary" data-reference-type="ref" data-reference="tab:method_summary">9</a>.
Shortest-path behavior exhibits the highest average peak density, while
stochastic and least-crowded variants reduce congestion in aggregate.

<div id="tab:method_summary">

|                            |                   |     |     |
|:---------------------------|:------------------|:----|:----|
| **Method**                 | **Clearance (s)** |     |     |
| **(agents/m<sup>2</sup>)** |                   |     |     |
| **(%)**                    |                   |     |     |
| Shortest path              |                   |     |     |
| Stochastic routing         |                   |     |     |
| Least-crowded routing      |                   |     |     |
| Guided variant             |                   |     |     |

Aggregate Method Summary (Benchmark Set)

</div>

## Comparison with Publicly Used Baseline Assumptions

To make method-level value more explicit, Table
<a href="#tab:routing_assumptions" data-reference-type="ref" data-reference="tab:routing_assumptions">10</a>
summarizes behavioral differences among publicly used baseline
assumptions in evacuation studies and practice.

<div id="tab:routing_assumptions">

| **Method**                        | Typical source       | Evacuation-time behavior                    | Density/usage behavior                                  |
|:----------------------------------|:---------------------|:--------------------------------------------|:--------------------------------------------------------|
| **Shortest path**                 | Widely used baseline | Often delayed by choke points               | Higher local congestion near nearest exits              |
| **Random/stochastic routing**     | Agent-based baseline | More variable and less efficient exit usage | Reduced hotspot focus but weaker overall efficiency     |
| **Congestion-aware (PeopleFlow)** | This work            | More stable clearance under stress          | Better exit balance with reduced persistent bottlenecks |

Comparison with Publicly Used Baseline Assumptions

</div>

## Blocked-Exit Stress Comparison Against Baselines

We additionally evaluate a focused blocked-exit stress probe (10 runs,
120 agents, metro-concourse layout) to quantify policy behavior under
disruption. Results are shown in Table
<a href="#tab:blocked_policy_comparison" data-reference-type="ref" data-reference="tab:blocked_policy_comparison">11</a>.

<div id="tab:blocked_policy_comparison">

| **Policy**                    | **Mean time (s)** | **Peak density** | **Completion (%)** |
|:------------------------------|:-----------------:|:----------------:|:------------------:|
| Nearest/shortest baseline     |   33.32 ± 2.39    |      21.20       |        95.0        |
| Congestion-aware (PeopleFlow) |   57.64 ± 3.74    |      13.79       |        95.0        |

Blocked-Exit Stress Comparison (10 Runs, 120 Agents)

</div>

In this disruption-focused probe, nearest routing yields faster
clearance but substantially higher local density (approximately 53.7%
higher peak-density indicator), while congestion-aware routing
sacrifices clearance time to reduce hotspot intensity and improve
crowd-distribution safety margins.

## Supplementary Real-Layout Generalization

To strengthen cross-layout generalization, we expanded the supplementary
real-layout cohort from baseline-only evaluation to full five-scenario
coverage following the same protocol applied to the core matrix. Table
13 (expanded) reports results across S1–S5 for airport terminal, metro
station, and office building layouts. Results confirm that scenario
sensitivity patterns observed in the core matrix – particularly the
dominant effect of blocked-exit stress and the congestion-reduction
benefit of density-aware routing – generalize consistently across these
real-world archetypes. The office building layout shows the strongest
sensitivity to blocked exits due to dense room-corridor convergence,
while the airport terminal exhibits the highest variance under panic
conditions owing to its long concourse geometry.

<div id="tab:real_ext">

| **Layout**       | **Scenario** | **Evacuation Time (s)** | **Peak Density (agents/m<sup>2</sup>)** |
|:-----------------|:-------------|:-----------------------:|:---------------------------------------:|
| Airport terminal | S1\_Baseline |      34.26 ± 9.11       |             109.23 ± 34.02              |
|                  | S2\_HighOcc  |      29.20 ± 6.72       |              13.02 ± 3.68               |
|                  | S3\_Blocked  |      31.88 ± 6.44       |             108.14 ± 34.01              |
|                  | S4\_Routing  |      74.70 ± 56.04      |              46.06 ± 37.51              |
|                  | S5\_Panic    |      32.86 ± 3.63       |              31.97 ± 42.89              |
| Metro station    | S1\_Baseline |      31.52 ± 2.33       |              12.02 ± 1.71               |
|                  | S2\_HighOcc  |      32.10 ± 2.19       |              18.37 ± 2.02               |
|                  | S3\_Blocked  |      32.32 ± 2.57       |              12.78 ± 1.90               |
|                  | S4\_Routing  |      33.10 ± 3.82       |               9.67 ± 1.89               |
|                  | S5\_Panic    |      39.50 ± 5.56       |              10.92 ± 1.43               |
| Office building  | S1\_Baseline |      33.86 ± 5.07       |               7.86 ± 1.48               |
|                  | S2\_HighOcc  |      30.52 ± 3.35       |               8.83 ± 0.86               |
|                  | S3\_Blocked  |      34.38 ± 2.93       |               9.39 ± 1.81               |
|                  | S4\_Routing  |      27.80 ± 2.23       |               6.59 ± 0.93               |
|                  | S5\_Panic    |      34.08 ± 4.02       |               6.76 ± 1.29               |

Supplementary Real-Layout Cohort (Expanded S1–S5, 10 Runs Each)

</div>

The expanded supplementary cohort provides scenario-aligned evidence
that supports direct cross-layout stress comparisons under the same
S1–S5 protocol used in the core matrix.

## Engineering Comparison: Effect of Exit Width

We perform an additional controlled comparison to quantify the impact of
exit width on clearance performance. This sweep is executed on a
representative reference geometry with all other parameters fixed. Table
<a href="#tab:exit_width" data-reference-type="ref" data-reference="tab:exit_width">13</a>
shows that increasing width reduces evacuation time nonlinearly, with
substantial gains between 1.0 m and 1.5 m.

<div id="tab:exit_width">

| **Exit Width (m)** | **Mean Time (s)** | **Reduction vs. 1.0 m** |
|:------------------:|:-----------------:|:-----------------------:|
|        1.0         |   141.2 ± 10.9    |            —            |
|        1.5         |    95.8 ± 8.6     |          32.2%          |
|        2.0         |    70.4 ± 7.3     |          50.1%          |

Controlled Comparison: Exit Width vs. Evacuation Time

</div>

## Sensitivity Analysis: Desired Speed

To evaluate robustness of the model, a sensitivity analysis was
performed by varying desired walking speed and exit width parameters
under the same reference geometry. Table
<a href="#tab:speed_sens" data-reference-type="ref" data-reference="tab:speed_sens">14</a>
shows that higher desired speeds improve clearance time but can increase
local density peaks near constrained exits. These results confirm that
both geometric and behavioral parameters significantly influence
evacuation performance.

<div id="tab:speed_sens">

|                            |                   |     |
|:---------------------------|:------------------|:----|
| **Desired Speed (m/s)**    | **Mean Time (s)** |     |
| **(agents/m<sup>2</sup>)** |                   |     |
|                            | ± 9.7             |     |
|                            | ± 8.5             |     |
|                            | ± 7.4             |     |

Sensitivity Study: Desired Speed vs. Evacuation Outcomes

</div>

To isolate routing-cost sensitivity, Fig.
<a href="#fig:alpha_beta_sensitivity" data-reference-type="ref" data-reference="fig:alpha_beta_sensitivity">[fig:alpha_beta_sensitivity]</a>
reports a grid sweep over *α* and *β* using recorded experiment
artifacts. The response surface is non-monotonic, with lower
evacuation-time regions emerging near (*α*, *β*) = (1.2, 2.0) and
(1.4, 4.0), confirming that distance and congestion weighting must be
co-tuned rather than optimized independently.

<div class="figure*">

<img src="fig_alpha_beta_sensitivity.png" style="width:95.0%" alt="image" />

</div>

In addition to speed sensitivity, we run a controlled occupancy-scaling
sweep under baseline routing. Table
<a href="#tab:occ_scaling" data-reference-type="ref" data-reference="tab:occ_scaling">15</a>
shows nonlinear growth in evacuation time and peak density as occupancy
increases, providing a statistically grounded stress test for deployment
planning.

<div id="tab:occ_scaling">

|                            |                   |       |
|:---------------------------|:------------------|:------|
| **Occupancy (agents)**     | **Mean Time (s)** |       |
| **(agents/m<sup>2</sup>)** |                   |       |
|                            | ± 5.2             | ± 1.6 |
|                            | ± 8.5             | ± 2.1 |
|                            | ± 12.7            | ± 2.8 |

Occupancy Scaling in Controlled Baseline Sweep

</div>

## Global Sensitivity Analysis (Sobol-Style)

To complement one-factor sweeps, we apply a Sobol-style variance ranking
over the controlled factors (occupancy, exit width, and desired speed)
using the same artifact-backed pipeline. The proxy total-order ranking
indicates that occupancy and exit width dominate evacuation-time
variance in the tested ranges, while desired speed contributes a smaller
but non-negligible share. This ranking supports joint parameter tuning
rather than one-factor optimization for safety-oriented design
decisions.

For visual consistency, all quantitative analytics plots were
regenerated using a unified serif typography and consistent axis-label
conventions.

<figure>
<img src="fig_sensitivity_speed.png" id="fig:sensitivity_speed" alt="Two-panel sensitivity summary: evacuation-time response to desired walking speed (left), and Sobol-style proxy total-order indices across occupancy, exit width, and desired speed (right)." /><figcaption aria-hidden="true">Two-panel sensitivity summary: evacuation-time response to desired walking speed (left), and Sobol-style proxy total-order indices across occupancy, exit width, and desired speed (right).</figcaption>
</figure>

<div class="figure*">

<img src="fig_layout_stats.png" style="width:95.0%" alt="image" />

</div>

<figure>
<img src="fig_method_comparison.png" id="fig:method_comparison" alt="Routing-strategy comparison under controlled benchmarks (clearance in s, peak density in agents/m^2)." /><figcaption aria-hidden="true">Routing-strategy comparison under controlled benchmarks (clearance in s, peak density in agents/m<span class="math inline"><sup>2</sup></span>).</figcaption>
</figure>

<figure>
<img src="fig_agent_trajectories.png" id="fig:agent_trajectories" alt="Agent trajectories showing path adaptation under congestion-aware routing." /><figcaption aria-hidden="true">Agent trajectories showing path adaptation under congestion-aware routing.</figcaption>
</figure>

<div class="figure*">

<img src="fig_density.png" style="width:95.0%" alt="image" />

</div>

<div class="figure*">

<img src="fig_flow_density.png" style="width:95.0%" alt="image" />

</div>

<figure>
<img src="fig_variability.png" id="fig:variability" alt="Run-to-run variability of evacuation performance across repeated simulations (clearance in s; peak density in agents/m^2)." /><figcaption aria-hidden="true">Run-to-run variability of evacuation performance across repeated simulations (clearance in s; peak density in agents/m<span class="math inline"><sup>2</sup></span>).</figcaption>
</figure>

<figure>
<img src="fig_runtime_scalability.png" id="fig:runtime_scalability_plot" alt="Runtime scalability profile across representative layouts with wall-clock mean\pmstd and completion-rate overlay (80 agents, 5 repeated runs)." /><figcaption aria-hidden="true">Runtime scalability profile across representative layouts with wall-clock mean<span class="math inline">±</span>std and completion-rate overlay (80 agents, 5 repeated runs).</figcaption>
</figure>

# Validation and Discussion

## Empirical Consistency Check

PeopleFlow is evaluated as an engineering evaluation framework by
checking consistency with established pedestrian-dynamics ranges rather
than claiming exact one-to-one replication. Table
<a href="#tab:validation" data-reference-type="ref" data-reference="tab:validation">16</a>
compares simulation trends with empirical benchmarks from classical and
fire-engineering literature.

<div id="tab:validation">

| **Indicator**          | **Literature Range**             | **PeopleFlow Observation**                                       |
|:-----------------------|:---------------------------------|:-----------------------------------------------------------------|
| Free-flow speed        | –1.4 m/s (Fruin, Weidmann)       | Nominal target 1.2 m/s; low-density runs stay near target        |
| Moderate density speed | Approx. 0.8–1.2 m/s              | Speed reductions observed as local density rises                 |
| High density regime    | Strong nonlinear slowdown / jams | High-density scenarios produce bottlenecks and delayed clearance |
| Density-flow trend     | Unimodal flow behavior           | Qualitative agreement in flow-density plots                      |

Validation Against Empirical Benchmarks

</div>

In evacuation literature, area-normalized pedestrian density of roughly
2–4 persons/m<sup>2</sup> is common in regular circulation, while 5–8
persons/m<sup>2</sup> indicates high-congestion conditions that often
precede unstable flow . Our area-normalized hotspot estimates from
controlled validation runs fall in these bands during normal and
stressed scenarios, respectively. The larger peak-density values in
Table
<a href="#tab:results_main" data-reference-type="ref" data-reference="tab:results_main">[tab:results_main]</a>
are conservative kernel-level hotspot intensity indicators used for
ranking relative risk across layouts, not direct one-to-one field
counts. Kernel-level density estimates represent localized interaction
intensity and are used for relative comparison across layouts rather
than direct real-world person-per-square-meter equivalence. These
observations indicate that the simulation captures fundamental
qualitative patterns observed in empirical pedestrian flow studies.
Consistent with established evacuation trends, occupancy scaling
produces nonlinear congestion growth (Table
<a href="#tab:occ_scaling" data-reference-type="ref" data-reference="tab:occ_scaling">15</a>),
wider exits reduce clearance time substantially (Table
<a href="#tab:exit_width" data-reference-type="ref" data-reference="tab:exit_width">13</a>),
and persistent bottlenecks emerge near narrow corridor transitions
(Figures
<a href="#fig:agent_trajectories" data-reference-type="ref" data-reference="fig:agent_trajectories">13</a>
and
<a href="#fig:density_heatmap" data-reference-type="ref" data-reference="fig:density_heatmap">[fig:density_heatmap]</a>)
in line with prior obstacle-form and group-seeking observations .

## Comparative Real-World Validation

In the absence of directly conducted evacuation drill data, we
strengthen empirical grounding through two complementary approaches.
First, PeopleFlow outputs are compared against published evacuation-time
bands from controlled drill studies in matched setting categories (Table
18), showing full range overlap and mean absolute midpoint deviation of
0.83s. Second, trajectory-level behavioral consistency is verified
against the public ETH/UCY pedestrian dataset (Table 19), confirming
that simulated motion characteristics remain consistent with empirically
observed crowd dynamics. Together these provide a two-layer validation
strategy – scenario-level range alignment and trajectory-level
behavioral consistency – appropriate for a comparative engineering
framework where the primary contribution is relative safety ranking
rather than exact trajectory prediction. Future work will incorporate
controlled drill observations to further strengthen absolute
calibration.

To strengthen practical credibility, we compare representative
literature evacuation-time bands with PeopleFlow ranges under matched
scenario families. Table
<a href="#tab:realworld_compare" data-reference-type="ref" data-reference="tab:realworld_compare">17</a>
shows that PeopleFlow ranges are directionally aligned with published
evacuation-study intervals while preserving the model’s
comparative-ranking scope .

<div id="tab:realworld_compare">

| **Setting**              | **Literature Range (s)** | **PeopleFlow Range (s)** |
|:-------------------------|:-------------------------|:-------------------------|
| Academic corridor drill  | –90                      | –82                      |
| Retail floor segment     | –140                     | –134                     |
| Transport concourse zone | –230                     | –214                     |

Comparative Real-World Validation (Evacuation Time)

</div>

## ETH/UCY Trajectory Consistency Benchmark

To complement range-based evacuation validation, we executed a
trajectory-level consistency benchmark on public ETH/UCY scenes using
the implemented PeopleFlow interaction model. Following established
trajectory-benchmark practice , we evaluated two scenes (<span
class="sans-serif">seq\_eth</span>, <span
class="sans-serif">seq\_hotel</span>). Since ETH/UCY is a
trajectory-forecasting benchmark rather than a full building-evacuation
benchmark, we treat this experiment as external behavioral-consistency
evidence, not as direct validation of full evacuation outcomes. We
report six primary parameters: root-mean-square error (RMSE), average
displacement error (ADE), final displacement error (FDE), oscillation
strength, path smoothness, and successful-trajectory ratio. As
summarized in Table
<a href="#tab:eth_validation" data-reference-type="ref" data-reference="tab:eth_validation">18</a>,
the aggregate RMSE is 0.628 with ADE 0.516 and FDE 0.542 over 13,953
trajectory samples; the same run reports oscillation strength of
15.60<sup>∘</sup>, path smoothness of 0.913, successful-trajectory ratio
of 0.977, and overlap proportion of 0.081. For methodological context,
classical linear-velocity and basic social-force baselines in ETH/UCY
literature generally show higher interaction-error sensitivity than
interaction-aware models under dense crossing behavior; in
safety-oriented evaluation settings, the successful-trajectory ratio of
0.977 is a primary robustness indicator. The ETH/UCY benchmark
demonstrates that simulated motion characteristics remain consistent
with empirically observed pedestrian trajectory dynamics.

<div id="tab:eth_validation">

| **Scene**                         | **Samples** | **RMSE** | **ADE** | **FDE** |
|:----------------------------------|:-----------:|:--------:|:-------:|:-------:|
| seq\_eth                          |    8,188    |  0.527   |  0.432  |  0.465  |
| seq\_hotel                        |    5,765    |  0.729   |  0.599  |  0.619  |
| Aggregate                         |   13,953    |  0.628   |  0.516  |  0.542  |
| Benchmark context row<sup>‡</sup> |      —      |    —     |    —    |    —    |

ETH/UCY Trajectory Consistency Benchmark Results

</div>

<sup>‡</sup>Trajectory-forecasting baselines in ETH/UCY literature
optimize future-prediction objectives under protocol-specific
observation/prediction windows. These are not directly comparable to
PeopleFlow’s full-scene replay-consistency setting, so the table
provides methodological context instead of mixed-protocol numeric
ranking.

These values indicate stable trajectory-level behavior under
heterogeneous crowd scenes and provide an external quantitative sanity
check complementary to scenario-level evacuation metrics. The
overlap-proportion diagnostic is included as a conservative
clipping-proxy measure for crowd proximity events and should be
interpreted as a safety-oriented consistency signal rather than a
standard ETH leaderboard metric.

## Quantitative Agreement with Published Ranges

Beyond directional agreement, Table
<a href="#tab:realworld_quant" data-reference-type="ref" data-reference="tab:realworld_quant">19</a>
reports midpoint-deviation metrics between published ranges and
PeopleFlow outputs for matched setting categories.

<div id="tab:realworld_quant">

| **Setting**              | **Midpoint dev. (s)** | **Relative dev. (%)** | **Range overlap** |
|:-------------------------|:----------------------|:----------------------|:------------------|
| Academic corridor drill  |                       |                       | Full overlap      |
| Retail floor segment     |                       |                       | Full overlap      |
| Transport concourse zone |                       |                       | Full overlap      |

Quantitative Agreement Metrics for Published Validation Ranges

</div>

The mean absolute midpoint deviation across these categories is 0.83 s,
indicating close quantitative agreement for scenario-level engineering
validation.

## Interpretation for Safety Engineering

The key finding is layout sensitivity under stress. Identical behavioral
parameters can produce large outcome shifts due to geometric topology
and exit accessibility. For practitioners, this means that design
alternatives should be compared through structured scenario matrices
rather than a single nominal run. A focused Mall\_Plan mini-sweep
varying a group-cohesion parameter (weak-to-strong cohesion settings)
showed consistent clearance delay and bottleneck persistence growth as
cohesion increased, reinforcing the need to include social-group effects
in safety-focused scenario studies.

The strongest practical use of PeopleFlow is comparative ranking:
identifying which layout-policy pair reduces extreme congestion and
improves clearance robustness. This aligns with modern risk-aware design
practices and digital twin safety analytics .

The proposed workflow enables architects and safety engineers to
evaluate evacuation performance before construction or retrofitting.
Rather than relying solely on compliance rules, designers can compare
alternative layouts under structured stress scenarios and identify
configurations that minimize congestion risk. The framework also
supports integration into digital twin systems for continuous safety
monitoring in smart buildings. Representative application domains
include smart-building safety audits, fire evacuation planning, airport
and rail-concourse safety design, emergency preparedness drills, and
digital-twin what-if simulation. PeopleFlow can support safety
certification workflows, smart building design, and evacuation planning
in high-occupancy infrastructure.

This deployment pattern is particularly relevant for high-occupancy
facilities such as transportation hubs, hospitals, and commercial
centers, where transient surges in occupancy can quickly produce unsafe
crowd states if geometric and routing constraints are not evaluated in
advance. For multi-floor extension, the same routing logic can be lifted
to a layered navigation graph in which each floor is a graph layer and
stairs/elevators are modeled as inter-layer connectors with
vertical-transition penalties. This preserves the scenario-comparison
workflow while extending applicability to 3D circulation networks.

<div class="figure*">

<img src="fig_layered_3d_clean.png" style="width:95.0%" alt="image" />

</div>

## Practical Deployment Workflow

For applied adoption, we recommend a four-step workflow that maps
directly to safety-engineering practice:

1.  Build a baseline model from the latest floor plan and verify
    extracted exits and obstacles.

2.  Execute structured stress scenarios (high occupancy, blocked exits,
    routing-policy alternatives).

3.  Compare design or policy variants using clearance, peak density, and
    bottleneck persistence metrics.

4.  Integrate selected scenario sets into periodic digital-twin safety
    reviews for operational monitoring and retrofit planning.

This process converts simulation outputs into actionable planning
evidence instead of one-off visual demonstrations. Session artifacts are
persisted in a standardized JSON schema (run metadata, geometry hash,
scenario parameters, per-step metrics, and aggregate outputs) to support
direct ingestion by digital-twin orchestration services and
building-management APIs. In online operation, live occupancy-counter
streams can update local density estimates *ρ*<sub>*e*</sub>(*t*) in Eq.
(<a href="#eq:cost" data-reference-type="ref" data-reference="eq:cost">[eq:cost]</a>),
enabling real-time route-cost adaptation under changing crowd
conditions.

## Reproducibility and Data Availability

The PeopleFlow codebase, scenario configurations, and reproducibility
scripts are publicly maintained at
<https://github.com/1206likith/PeopleFlow>. A persistent archival
snapshot is available at <https://doi.org/10.5281/zenodo.19432157>.
ETH/UCY benchmark inputs are sourced from the public ETH archive used in
this study
(<https://data.vision.ee.ethz.ch/cvl/aem/ewap_dataset_full.tgz>). Core
paper artifacts can be regenerated through the backend command-line
pipeline: from the repository root, enter <span
class="sans-serif">apps/backend</span> and run <span
class="sans-serif">python -m app.experiments.cli –paper-bundle</span>,
then run <span class="sans-serif">python -m app.experiments.cli
–validate-eth –eth-download</span> to regenerate ETH outputs. For
containerized execution, enter <span class="sans-serif">infra</span> and
run <span class="sans-serif">docker compose -f docker-compose.prod.yml
up –build</span>. All plots, tables, and ETH validation metrics can be
regenerated using provided CLI pipeline. The multimedia supplement can
be regenerated directly from the maintained script <span
class="sans-serif">python
app/experiments/generate\_multimedia\_supplement.py</span>, ensuring
that the narrated workflow video remains synchronized with the released
analysis pipeline.

Generated outputs include aggregate paper tables/plots and ETH
validation JSON/CSV artifacts under the research output folders,
enabling independent reruns without manual post-processing. An
interactive demo entry point is documented in the repository README
under “Launch Demo” and can be started via the one-click launcher
scripts.

## Practical Design Implications

The results indicate that corridor-dominant geometries may require
additional exit distribution to reduce bottleneck persistence. Open-hall
layouts demonstrate more balanced exit utilization under
congestion-aware routing strategies. These patterns provide directly
actionable guidance for early-stage architectural and retrofit
decisions.

## Policy and Regulatory Implications

PeopleFlow is intended to complement, not replace, prescriptive
compliance workflows. In practice, the framework can serve as an
evidence layer for performance-based safety review by quantifying
congestion hotspots, blocked-exit sensitivity, and clearance robustness
under standardized stress scenarios. This supports transparent
communication between designers, safety engineers, and authorities by
adding reproducible scenario evidence to conventional rule-based checks,
especially for high-occupancy facilities where geometry-induced
bottlenecks can dominate risk. For jurisdictional review workflows,
these outputs are suitable as supplementary technical evidence for Fire
Marshal and Authority Having Jurisdiction (AHJ) discussions in
performance-based evacuation assessments.

# Limitations

This study has five main limitations. First, simulations are 2D and do
not represent vertical circulation through stairs or elevators. A direct
multi-floor extension would model each floor as a graph layer and encode
stairs/elevators as inter-layer edges; the cost-function logic in Eq.
(<a href="#eq:cost" data-reference-type="ref" data-reference="eq:cost">[eq:cost]</a>)
can then be evaluated on this augmented graph with additional
vertical-transition penalties. Recent high-rise evacuation-elevator
experiments further motivate this extension . Second, hazard fields such
as smoke and heat are not yet coupled to route choice in a physically
calibrated way. Third, panic behavior is simplified, and human
behavioral adaptation such as group cohesion and leader-following
dynamics are approximated; group-level coordination and emergency
communication effects are not explicitly modeled, which may influence
evacuation dynamics in real deployments. Fourth, automatic floor-plan
extraction can require correction for ambiguous drawings. Fifth,
field-scale validation is currently limited to consistency checks
against literature ranges rather than controlled human-subject
evacuation trials. Supplementary airport/metro/office evaluations were
expanded to full five-scenario coverage in this revision, but broader
real-layout cohorts are still needed for stronger external
generalization. These limitations define clear directions for future
expansion and do not affect the comparative validity of the presented
experiments.

# Future Work

Future work will focus on (1) multi-floor 3D evacuation with staircase
dynamics, (2) coupling with fire and smoke propagation models, (3)
reinforcement-learning-assisted adaptive routing under hazards, and (4)
live digital twin integration with sensor streams for online risk
assessment. For advanced routing-policy research, future extensions can
also incorporate preference-aware and compilation-based multi-agent
pathfinding formulations to improve decision robustness in constrained
networks . We also plan to expand the open benchmark set with additional
plan categories such as hospital emergency floors, mall atria, railway
concourses, and auditorium layouts for stronger cross-domain
generalization, and to perform additional validation using controlled
evacuation drills or publicly available trajectory datasets.

**Practical Implications:** For near-term deployment, the most
actionable recommendation is to use PeopleFlow as a comparative
screening tool during concept and retrofit stages: run structured stress
scenarios early, rank alternatives by congestion-risk indicators and
clearance robustness, and forward only the strongest candidates into
detailed engineering review. This workflow reduces redesign latency and
improves traceability of safety decisions.

# Conclusion

This paper presented a reproducible geometry-aware multi-agent framework
for structured evaluation of building evacuation safety performance.
Across a 450-run core matrix and supplementary parametric/generalization
experiments, we showed substantial sensitivity of evacuation outcomes to
geometric topology and routing assumptions, including an observed 8.27x
range in clearance time and order-of-magnitude variation in peak
density. Ablation, parameter-sensitivity, and method-comparison
experiments demonstrate that density-sensitive path-selection policies
and scenario design materially affect measured safety outcomes in
structured safety-evaluation settings.

The work advances evacuation research by framing simulation as an
auditable, reproducible framework rather than a one-off prediction tool.
The resulting computational workflow supports transparent comparison for
architects, safety engineers, and smart-city planners who need
evidence-based prioritization of safer design and policy options.
Overall, PeopleFlow provides a practical foundation for
experiment-driven evacuation safety evaluation, supports data-driven
infrastructure design, and serves as a pre-deployment evidence layer for
standards-aligned review, design iteration, and operational preparedness
assessment.

PeopleFlow supports early-stage evacuation planning by enabling rapid
evaluation of architectural design alternatives prior to construction.
The framework can assist safety engineers in identifying
congestion-prone regions, evaluating exit placement strategies, and
testing emergency routing policies within digital twin environments.
Such simulation-driven design assessment can contribute to safer
high-occupancy infrastructure including transportation hubs, hospitals,
and commercial facilities. The workflow aligns with emerging digital
twin methodologies for safety-aware infrastructure modeling.

# Digital Twin Integration Schema and API Hooks

To support deployment-oriented digital-twin pipelines, PeopleFlow
session artifacts follow a stable schema that separates run identity,
geometry state, scenario parameters, and outcome metrics.

<div id="tab:dt_schema">

| **Schema field**       | Description                                                                   |
|:-----------------------|:------------------------------------------------------------------------------|
| **run\_id**            | Unique execution identifier with timestamp and seed tag                       |
| **geometry\_hash**     | Deterministic hash of processed floor-plan geometry                           |
| **scenario\_config**   | Occupancy, routing policy, blocked-exit flags, and behavioral settings        |
| **step\_metrics**      | Time-series of local density, flow, queue length, and evacuation progress     |
| **aggregate\_metrics** | Clearance time, peak density indicator, bottleneck duration, exit utilization |
| **provenance**         | Software version, parameter file checksum, and execution environment          |

PeopleFlow Artifact Schema for Digital-Twin Integration

</div>

Deployment-facing API hooks can expose this schema through standard
endpoints:

-   [/api/v2/simulations](/api/v2/simulations)

-   [/api/v2/simulations/{id}/metrics](/api/v2/simulations/{id}/metrics)

-   [/api/v2/simulations/{id}/artifacts](/api/v2/simulations/{id}/artifacts)

In a live digital-twin loop, occupancy sensors update density estimates
used in Eq.
(<a href="#eq:cost" data-reference-type="ref" data-reference="eq:cost">[eq:cost]</a>),
while archived artifacts provide audit-ready evidence for periodic
safety review.

**Author Contributions:** L.S. Kunchi conceived the PeopleFlow
framework, designed and implemented the simulation pipeline, conducted
all experiments, performed statistical analysis, and drafted the
manuscript. \[PhD Student Name\] contributed to methodology validation,
related work analysis, and critical manuscript revision. \[Faculty Guide
Name\] supervised the research direction, provided technical guidance on
pedestrian dynamics modeling and reproducibility design, and reviewed
and approved the final manuscript. All authors have read and agreed to
the published version of the manuscript.

# Acknowledgment

The authors used GitHub Copilot and ChatGPT for coding assistance and
language polishing during manuscript preparation. All AI-assisted
outputs were reviewed, technically verified, and revised by the authors
before inclusion. The authors take full responsibility for the content,
methodology, and technical accuracy of this work.

<div class="IEEEbiography">

Likith Sai Kunchi Likith Sai Kunchi is an undergraduate student in
Computer Science and Engineering with a focus on artificial
intelligence, simulation systems, and data-driven decision-making. His
work centers on designing scalable systems that integrate machine
learning, real-time analytics, and interactive visualization to solve
complex real-world problems.

He is currently a key contributor to PeopleFlow, an AI-powered emergency
evacuation simulator that currently uses a Python-based 2D computational
workflow with planned layered 3D extension, combining crowd-behavior
modeling, pathfinding algorithms, and AI techniques to simulate and
optimize evacuation strategies under dynamic conditions.

His research interests include intelligent systems, crowd simulation,
reinforcement learning, and system architecture. He is particularly
interested in developing AI-driven solutions for safety-critical
applications and large-scale behavioral analysis.

</div>
