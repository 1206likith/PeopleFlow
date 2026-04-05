# PeopleFlow Unity Simulation

Unity project for real-time evacuation visualization.

## Networking
- Primary: `Managers/WebSocketClient.cs`
- Legacy: `Managers/WebSocketManager.cs` (deprecated, HTTP polling stub)

Unity connects to backend via `/ws/unity/{simulation_id}` and streams `simulation_update` messages.

## Setup
1. Open `apps/unity/` in Unity 2022 LTS.
2. Ensure `SimulationManager` and `WebSocketClient` are in the scene.
3. Run backend and start simulation from the web dashboard.

