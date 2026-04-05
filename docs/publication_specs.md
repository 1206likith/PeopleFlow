# PeopleFlow Simulation: Mathematical Foundations & Assumptions

## 1. Governing Model Equations

The crowd behavior is modeled primarily via a modified continuous-space **Social Force Model (SFM)** combined with discrete topological graph routing logic. The continuous updating of agent $i$'s velocity $\vec{v}_i$ is governed by:

$$
m_i \frac{d\vec{v}_i}{dt} = \vec{f}_i^{driving} + \sum_{j \neq i} \vec{f}_{ij}^{repulsive} + \sum_{w} \vec{f}_{iw}^{wall} + \vec{f}_i^{fluctuation}
$$

### 1.1 Driving Force
The driving force pushes the agent towards their targeted exit waypoint on the macro-graph path:
$$
\vec{f}_i^{driving} = \frac{v_i^0 \vec{e}_i - \vec{v}_i}{\tau}
$$
Where:
- $v_i^0$ is the desired walking speed (typically $1.2$ to $1.4$ m/s).
- $\vec{e}_i$ is the unit vector pointing to the next topological target.
- $\tau$ is the relaxation time (approx. $0.5$ s).

### 1.2 Inter-Personal Repulsion
Pedestrians maintain distance from others exponentially:
$$
\vec{f}_{ij}^{repulsive} = A_i \exp\left(\frac{r_{ij} - d_{ij}}{B_i}\right) \vec{n}_{ij}
$$
Where:
- $A_i \approx 2000$ N is the repulsion strength.
- $B_i \approx 0.08$ m is the fall-off distance.
- $r_{ij}$ is the sum of pedestrian radii.

## 2. Policy Definitions

Three comparison policies operate on top of the physical layer:
1. **Nearest Exit**: Agents compute standard Euclidean $L^2$ distance to available exit topological nodes and target the absolute minimum.
2. **Least Crowded**: A cost function $C(x) = D(x) + \alpha Q(x)$ where $D$ is distance and $Q$ is perceived queue density.
3. **Guided Evacuation**: Simulates explicit assignments typical of trained staff interventions, dividing the initial population into fixed exit sub-flows.

## 3. Assumptions and Limitations
1. **Homogeneous Space**: Terrain is considered flat without staircases in this specific testing module.
2. **Perfect Observation**: Under the discrete graph layer, agents inherently 'know' the topological routes to exits. In real life, panic causes smoke-induced myopia which is modeled separately using delay factors (`pre_evacuation_delay`).
3. **Capacity Constraints**: We rely on SFPE handbook max limit of $1.32$ persons/meter/second to calibrate queue processing rates.

## 4. Validation Results
Testing the parameters against reference models demonstrates:
- Evacuation curves consistently yield asymptotic long-tail distributions associated with queueing theory at bottleneck conditions.
- Maximum flow constraints organically throttle continuous throughput, aligning dynamically with literature bounds (`SFPEBenchmarks` tests resolve to `True`).
