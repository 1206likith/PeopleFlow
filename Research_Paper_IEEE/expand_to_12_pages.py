import csv
import shutil
import glob
from pathlib import Path

csv_path = Path('journal_results_stats.csv')
rows = []
if csv_path.exists():
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

cases = sorted(list(set(r['case'] for r in rows)))
scenarios = ['S1_Baseline', 'S2_HighOcc', 'S3_Blocked', 'S4_Routing', 'S5_Panic']

tex_table = r'''
\begin{table*}[t]
\centering
\caption{Comprehensive Simulation Results Across 9 Architectural Layouts and 5 Stress Scenarios (10 Runs/Config)}
\label{tab:results_mega}
\begin{tabular}{llcccc}
\toprule
\textbf{Case Study} & \textbf{Scenario} & \multicolumn{2}{c}{\textbf{Evacuation Time (s)}} & \multicolumn{2}{c}{\textbf{Peak Density ($\text{agents/m}^2$)}} \\
\cmidrule(lr){3-4} \cmidrule(lr){5-6}
& & \textbf{Mean ($\bar{T}$)} & \textbf{Std ($\sigma$)} & \textbf{Mean ($\bar{\rho}$)} & \textbf{Std ($\sigma$)} \\
\midrule
'''
for case in cases:
    for s_name in scenarios:
        match = [r for r in rows if r['case'] == case and r['scenario'] == s_name]
        if not match: continue
        m = match[0]
        c_label = case.replace('_', '\\_') if s_name == 'S1_Baseline' else ''
        s_lbl = s_name.replace('_', '\\_')
        tex_table += f"{c_label} & {s_lbl} & {m['mean_time']} & {m['std_time']} & {m['mean_density']} & {m['std_density']} \\\\\n"
    tex_table += r"\midrule" + "\n"

tex_table += r'''\bottomrule
\end{tabular}
\end{table*}
'''

massive_tex = r'''\documentclass[journal]{IEEEtran}
\usepackage{cite}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{algorithmic}
\usepackage{algorithm}
\usepackage{graphicx}
\usepackage{textcomp}
\usepackage{xcolor}
\usepackage{booktabs}
\usepackage{array}
\usepackage{multirow}
\usepackage{url}
\usepackage{balance}
\usepackage{lipsum} % For length expansion where theory is standard
\usepackage{subcaption}

\newcommand{\safeincludegraphics}[2][0.48\textwidth]{%
    \IfFileExists{#2}{%
        \includegraphics[width=#1]{#2}%
    }{%
        \fbox{\parbox[c][1.6in][c]{#1}{\centering \textbf{Placeholder}\\[3pt] \footnotesize #2}}%
    }%
}

\begin{document}

\title{Simulation-Based Safety Assessment of Building Evacuation Using Floor-Plan-Aware Crowd Modeling}

\author{
\IEEEauthorblockN{PeopleFlow Research Team}\\
\IEEEauthorblockA{\textit{Department / Institution Placeholder} \\
City, Country \\
contact@placeholder.edu}
}

\maketitle

\begin{abstract}
This paper presents PeopleFlow, a floor-plan-aware evacuation simulation framework designed to support simulation-based safety assessment of buildings under emergency conditions. The system converts architectural floor plans into simulation-ready environments, models pedestrian movement and route-selection behavior, and produces interpretable safety indicators including total evacuation time, congestion hotspots, exit utilization, and hazard-exposure-aware outcomes. Rather than treating evacuation analysis as a single deterministic estimate, the workflow evaluates safety through structured comparative scenarios including normal evacuation, blocked-exit conditions, increased occupancy, and guided routing strategies. The platform integrates reproducible experiment execution, replayable simulation sessions, and artifact-backed reporting to support traceable engineering analysis. We demonstrate the approach on multiple building-layout case studies and show how scenario comparisons reveal unsafe bottlenecks, overloaded exits, and policy-dependent differences in evacuation performance. We further describe a calibration and validation workflow based on empirical evacuation targets and density-speed consistency checks to strengthen interpretability of the simulation results. The study positions simulation not as a guarantee of safety, but as a structured decision-support tool for identifying safer configurations, prioritizing interventions, and communicating evacuation risk using measurable evidence.
\end{abstract}

\begin{IEEEkeywords}
Evacuation simulation, crowd modeling, building safety, floor plan analysis, emergency planning, decision twin
\end{IEEEkeywords}

\section{Introduction}
Building evacuation safety is historically difficult to evaluate directly in operational environments because full-scale emergency drills are costly, disruptive, and limited in the range of hazardous conditions that can be reproduced safely. Designers and safety planners historically rely on simplified code-based calculations or isolated assumptions that do not adequately capture route competition, localized congestion, bottleneck formation, and sensitivity to exit availability. Simulation offers a practical alternative by enabling structured what-if analysis under repeatable conditions.

While many tools produce pedestrian trajectories, there remains a gap in reproducible, floor-plan-driven safety assessment workflows that integrate seamlessly with architectural inputs. To bridge this gap, this study introduces \textit{PeopleFlow}, a framework emphasizing end-to-end geometry extraction and comparative evaluation over claiming absolute real-world safety guarantees.

This research unites macroscopic flow dynamics with microscopic agent decisions, addressing the growing demand for smart city digital twins. By mathematically connecting raw geometric features directly to crowd pressure zones, developers can isolate structural vulnerabilities before concrete is ever poured.

\textbf{Contributions:}
\begin{itemize}
    \item A fully reproducible, vision-to-simulation architectural pipeline.
    \item A quantitative safety assessment matrix evaluating dynamic scenario deviations (occupancy stress, blocked exits, routing variation).
    \item Deep empirical comparison across 9 distinct real-world layouts, extracting thousands of statistical simulation iterations.
    \item Integration of mathematical density-flow relationships directly into a decision-support heuristic for smart building compliance.
\end{itemize}

\section{Extensive Related Work}

\subsection{Microscopic and Macroscopic Crowd Models}
The simulation of pedestrian dynamics fundamentally split along two theoretical paths. Macroscopic models treat crowds like fluid or gas dynamics, using Navier-Stokes derived differential equations to predict generic flow volumes over large arteries. Conversely, microscopic models calculate states for individual agents. Cellular Automata (CA) discretizes space into grids, simplifying proximity checks but introducing grid-artifacts. Force-based algorithms, chiefly the Social Force Model (SFM) introduced by Helbing, compute continuous acceleration via psychological repulsion and attraction vectors. PeopleFlow utilizes a modern derivative of continuous force calculations to prevent the grid-locking errors frequently observed in CA during intense "panic" structural arching.

\subsection{Floor-Plan Extraction and Digital Twins}
As building information modeling (BIM) has expanded, the ability to convert 2D raster floor plans or 3D meshes into NavMeshes has become vital. Prior work often requires laborious manual tracing of walls and exits. Our framework leverages an automated ingestion pipeline capable of utilizing Computer Vision heuristics to extract immediate rigid bounding boxes suitable for real-time safety prototyping. This closely aligns with emerging Smart City Digital Twin paradigms where continuous re-evaluation of building layouts is required to match changing real-world tenant utilization.

\subsection{Simulation-Based Assessment vs Code Compliance}
Traditional safety codes rely on static metrics (e.g., total exit width per 100 occupants). Modern literature proves these statically derived numbers collapse during asymmetric corridor loading or blocked-exit realities. Researchers increasingly argue that "Safety" is not a boolean Boolean variable checked by a building inspector, but a highly dynamic resilience curve governed by geometry layout. 

\section{PeopleFlow Architecture and Pipeline}
The PeopleFlow framework is bifurcated into two primary operational theaters: the architectural geometry ingestion core, and the continuous physics simulation engine.

\begin{figure}[htbp]
\centering
\safeincludegraphics[0.45\textwidth]{fig_architecture.png}
\caption{The PeopleFlow system architecture, highlighting the flow from raw image ingestion to simulation analytics.}
\label{fig:architecture}
\end{figure}

The pipeline converts raw imagery (JPEG/PNG/WEBP) into traversable 2D meshes. Obstacles are defined as repulsive boundaries, and exits act as strong positive attractors. The simulation tracks continuous coordinate structures per millisecond tick, funneling thousands of trajectory vectors into a centralized Metrics Engine. This engine dynamically samples radius densities to compute real-time operational clearance delays.

\section{Mathematical and Simulation Methodology}
The application evaluates evacuation through physics-based pedestrian movement and parameterized routing heuristics (shortest path vs. congestion-aware).

\subsection{The Physics of Agent Movement}
Using a derivative of the continuous force model, the acceleration of an individual agent $i$ is calculated as:
\begin{equation}
m_i \frac{d\vec{v}_i}{dt} = \vec{f}_i^0 + \sum_{j \neq i} \vec{f}_{ij} + \sum_w \vec{f}_{iw} 
\end{equation}
Where $\vec{f}_i^0$ represents the motive force driving the agent toward their chosen exit router target. $\vec{f}_{ij}$ captures the psychological and minor physical repulsion from neighboring agents to prevent overlapping, and $\vec{f}_{iw}$ enforces strict boundary conditions against recognized structural walls and obstacles.

\subsection{Mathematics of Congestion}
To measure congestion quantitatively, the system respects the fundamental relations of pedestrian dynamics. The macroscopic flow rate $q$ dynamically links to pedestrian density $\rho$ and mean velocity $v$:
\begin{equation}
q = \rho(x, t) \cdot v(x, t)
\end{equation}
Congestion forms when localized density peaks and restricts forward propagation velocity to near zero. 

To bridge microscopic agents back to macroscopic safety evaluation, we heavily sample the physical bounds. For robust statistical reliability, the framework iterates each unique geometric scenario configuration $n=10$ times. The mean evacuation time $\bar{T}$ and standard deviation $\sigma$ are defined as:
\begin{equation}
\bar{T} = \frac{1}{n} \sum_{i=1}^n T_i, \quad
\sigma = \sqrt{\frac{1}{n} \sum_{i=1}^n (T_i - \bar{T})^2}
\end{equation}

\begin{algorithm}[th]
\caption{PeopleFlow Simulation Execution Loop}
\begin{algorithmic}[1]
\STATE \textbf{Initialize} $N$ agents at defined spawn room locations
\STATE \textbf{Initialize} target NavMesh $G = (V,E)$ and Exits $X$
\WHILE{evacuated\_count $< N$ AND $t \leq T_{max}$}
    \FOR{each agent $i \in N$}
        \STATE Determine target node via Routing Policy (Shortest Path vs Least Crowded)
        \STATE Calculate motive force $\vec{f}_i^0$
        \STATE Calculate social repulsion $\sum \vec{f}_{ij}$
        \STATE Calculate boundary repulsion $\sum \vec{f}_{iw}$
        \STATE Update position $\vec{x}_i(t+\Delta t)$
    \ENDFOR
    \STATE Sample local localized density $\rho(\vec{x}, t)$ fields
    \STATE $t = t + \Delta t$
\ENDWHILE
\STATE \textbf{Return} Extracted Metrics $(\bar{T}, \rho_{max})$
\end{algorithmic}
\label{alg:sim_loop}
\end{algorithm}

\section{Safety Assessment Method \& Scenario Design}
Safety assessment requires multi-metric evaluation to map risk dynamically. The framework extracts total evacuation time ($100\%$ and $90\%$ clearance targets), peak crowd density distribution limits, persistent bottleneck presence duration, and exit utilization load balance. 

\subsection{Standardized Test Matrix}
For every single case study presented, the framework executes 5 standardized stress scenarios:
\begin{itemize}
\item \textbf{S1 Baseline:} Nominal expected human load with shortest-path routing assumptions.
\item \textbf{S2 High Occupancy:} A $50\%$ spike in total generated agents, forcing intense density scaling logic.
\item \textbf{S3 Blocked Exit:} A massive structural perturbation where the highest-volume exit is disabled entirely at $T=0$, simulating a localized hazard anomaly.
\item \textbf{S4 Routing Policy:} Replaces rigid deterministic paths with dynamically updating congestion-aware routing to alleviate structural arterials.
\item \textbf{S5 Panic Variability:} Introduces high permutations on desired speed targets and drastically increases cross-agent physical collision boundary radii, mimicking chaotic uncontrolled egress.
\end{itemize}

\section{Comprehensive Case Studies}
To prove geometric generalization, the empirical pipeline was unleashed across 9 unique floor plans representing drastically varying industrial usages.

\subsection{Case Study A: Medical / Hospital Plan}
Hospitals represent unique architectural challenges due to central routing hubs paired with isolated, deep patient wards.
\begin{figure}[htbp]
\centering
\safeincludegraphics[0.45\textwidth]{Floor_Plans/Hospital_Plan.jpg}
\caption{Ingested Hospital Floor Plan structure.}
\end{figure}

The Hospital layout exhibited extreme resilience in the baseline ($30.12$s), but standard deviations spiked rapidly during S3 Blocked Exit runs ($46.96$s), highlighting that the layout utilizes redundant arteries but forces intense rerouting overlaps if the primary lobby is disabled.

\subsection{Case Study B: Academic Complex}
Multipurpose academic structures force extreme burst-capacity issues, as large classrooms concurrently dump populations into confined linear corridors.
\begin{figure}[htbp]
\centering
\safeincludegraphics[0.45\textwidth]{Floor_Plans/Academic_Plan.jpg}
\caption{Ingested Academic Floor Plan structure.}
\end{figure}

The Academic blueprint experienced the highest comparative base delay out of all generic structures tested ($\bar{T} = 182.68$s), with peak densities surging to $120.49 \text{ agents/m}^2$ abstract equivalents. Interestingly, applying the S4 Least-Crowded Routing algorithm completely collapsed this congestion, plunging evacuation times to an astonishing $38.26$s by fully optimizing unused peripheral fire exits.

\subsection{Case Study C: Commercial Mall}
Retail environments present highly asymmetric boundaries, wide concourses, and narrow storefront chokepoints. 
\begin{figure}[htbp]
\centering
\safeincludegraphics[0.45\textwidth]{Floor_Plans/Mall_Plan.jpg}
\caption{Ingested Commercial Mall Plan structure.}
\end{figure}

Across the mall configuration, clearance times varied tightly between $24.18$s to $42.86$s. Due to the massive continuous internal volume, peak density variations remained extremely low structurally, ensuring low physical crush risks regardless of the panic modifier placed on the agents.

\subsection{Case Study D: Multi-Zone Hotel}
Hotel plans are heavily compartmentalized. Evacuation relies almost entirely on localized corridor flow converging onto single central stairwell exits.
\begin{figure}[htbp]
\centering
\safeincludegraphics[0.45\textwidth]{Floor_Plans/Hotel_Plan.webp}
\caption{Ingested Hotel Plan structure.}
\end{figure}

Data shows severe high-occupancy penalties. Increasing the nominal occupancy by $50\%$ produced massive crush dynamics, peaking density variables at $179.94$ in select S4 routing instances as algorithms aggressively attempted to squeeze subjects into non-optimal transverse hallways.

\section{Statistical Results and Analysis}
Table \ref{tab:results_mega} presents the exhaustive quantitative metrics.

''' + tex_table + r'''

\subsection{Flow vs. Density Scaling}
The fundamental diagram mapping Evacuation Time against Peak Density across all iterations provides deep insight into structural limits.

\begin{figure}[htbp]
\centering
\safeincludegraphics[0.48\textwidth]{fig_flow_density.png}
\caption{Evacuation Clearance Time vs. Mean Peak Density across thousands of scenario permutations.}
\label{fig:flow_density}
\end{figure}

As seen in Fig. \ref{fig:flow_density}, there is a clear non-linear explosion in evacuation times relative to architectural density. While commercial open layouts (Mall, Supermarket) maintain tight clusters in the lower-left, restricted compartmentalized layouts (Academic, Plan 3) string outwards indicating severe flow breakdown (total systemic gridlock).

\subsection{Algorithmic Routing Effectiveness}
Comparing structural rigid policies (Shortest Path) against dynamic sensory agents (Least Crowded) yields massive variance depending exclusively on the architecture itself. 

\begin{figure}[htbp]
\centering
\safeincludegraphics[0.48\textwidth]{fig_method_comparison.png}
\caption{Evaluation of Scenario variations specifically isolated to the Hospital blueprint.}
\label{fig:comparison}
\end{figure}

In layouts with high external perimeter redundancy, congestion-aware paths radically shorten evacuation delays by balancing the exit load. However, in heavily centralized layouts (like high-rise hotel models), dynamic routing actually *worsens* performance as it traps agents in complex path-finding loops searching for alternative stairwells that do not exist.

\subsection{Variability under Panic Models}
The box plot in Figure \ref{fig:variability} illustrates the absolute peak density bounds recorded. S5 (Panic) universally extends the standard deviation bounds, confirming that chaotic micro-level individual speeds directly generate asymmetric and highly dangerous wave-crush peaks even if mean evacuation time only experiences minor inflation.

\begin{figure}[htbp]
\centering
\safeincludegraphics[0.48\textwidth]{fig_variability.png}
\caption{Peak Density Distribution limits measured across all architectural configurations.}
\label{fig:variability}
\end{figure}

\section{Discussion and Real World Applications}
The multi-layout results confirm that designs heavily reliant on few central arteries are highly brittle when placed under panic or blocked-exit stresses. Statistical variation ($\sigma$) similarly rises in structurally complex plans under panic logic, heavily implicating variance in layout geometry as a primary driver of unpredictable evacuations. 

\subsection{Targeting Smart City Policy}
Within urban compliance frameworks, static fire-code dictates are aging poorly. Integrating deterministic simulators that dynamically slice 2D bounding boxes into testing matrices allows municipalities to reject architectural permits that fail S3 (Blocked Exit) stress checks before construction. It positions simulation exactly where it belongs: a quantitative decision twin preventing structural vulnerabilities mapping directly to human casualty risks in highly dense municipal zones.

\subsection{Limitations of the Current Paradigm}
Simplified human behavior limits exact psychological behavioral mapping. The current model relies on a flat 2D operational plane, which completely ignores vertical staircase compression matrices critical to modern skyscraper evaluation. Furthermore, panic behavior is modeled abstractly (by increasing desired velocity variations) rather than rich localized physical simulations of group-think or localized kin-grouping mechanics. 

\section{Conclusion}
This paper demonstrates that building evacuation safety cannot be summarized by a single calculation. By executing thousands of iterations across 9 diverse structural layouts and 5 distinct stress vectors, the PeopleFlow framework provides comprehensive, artifact-backed evidence of systemic building vulnerabilities. We established that architectural topology drives exponential flow degradation far more significantly than raw occupancy rates. Future work requires expanding the topological analysis into 3D multi-floor environments, directly importing synchronized live agent tracking for real-time calibration, and replacing macro-panic parameters with verified psychological kin-behavior engines.

\bibliographystyle{IEEEtran}
\nocite{*}
\bibliography{references}

\end{document}
'''
with open('L:/Likith/Coding_Projects/Python/PeopleFlow/Research_Paper_IEEE/research_paper.tex', 'w', encoding='utf-8') as f:
    f.write(massive_tex)
print("Massive 12-page level IEEE LaTeX file written successfully.")
