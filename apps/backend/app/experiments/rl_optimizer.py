import torch # type: ignore
import torch.nn as nn # type: ignore
import torch.optim as optim # type: ignore
import random
import numpy as np # type: ignore
from collections import deque
from app.sim.core_engine import CoreSimulationEngine, SimConfig # type: ignore

class SignageDQN(nn.Module):
    """Deep Q-Network for predicting optimal signage redirection to minimize bottlenecking."""
    def __init__(self, state_size: int, action_size: int):
        super().__init__()
        self.fc1 = nn.Linear(state_size, 32)
        self.fc2 = nn.Linear(32, 32)
        self.out = nn.Linear(32, action_size)
        
    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.out(x)

class RLOptimizer:
    """Trains a dynamic sign targeting algorithm prioritizing quickest room clear times."""
    def __init__(self, num_exits: int):
        self.state_size = num_exits # Number of queues at each exit
        self.action_size = num_exits # Which exit the sign should point to
        self.model = SignageDQN(self.state_size, self.action_size)
        self.optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        self.criterion = nn.MSELoss()
        self.memory = deque(maxlen=2000)
        self.gamma = 0.95
        self.epsilon = 1.0
        self.epsilon_min = 0.05
        self.epsilon_decay = 0.995

    def get_state(self, engine: CoreSimulationEngine) -> np.ndarray:
        # State: density (number of agents) queued at each exit
        state = np.zeros(self.state_size)
        for i, e in enumerate(engine.exits):
            queue = sum(1 for a in engine.agents if a.status != "evacuated" and 
                        ((e.get("x",0) - a.x)**2 + (e.get("z", e.get("y",0)) - a.z)**2)**0.5 < 5.0)
            state[i] = queue
        return state
        
    def act(self, state: np.ndarray) -> int:
        if np.random.rand() <= self.epsilon:
            return random.randrange(self.action_size)
        with torch.no_grad():
            q_values = self.model(torch.FloatTensor(state)) # type: ignore
            return torch.argmax(q_values).item()
            
    def replay(self, batch_size: int):
        if len(self.memory) < batch_size:
            return
        batch = random.sample(self.memory, batch_size)
        for state, action, reward, next_state, done in batch:
            target = reward
            if not done:
                target = reward + self.gamma * torch.max(self.model(torch.FloatTensor(next_state))).item() # type: ignore
            target_f = self.model(torch.FloatTensor(state)) # type: ignore
            target_f_clone = target_f.clone().detach() # avoids inplace errors
            target_f_clone[action] = target
            
            self.optimizer.zero_grad()
            output = self.model(torch.FloatTensor(state)) # type: ignore
            loss = self.criterion(output, target_f_clone)
            loss.backward()
            self.optimizer.step()
            
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

    @classmethod
    def run_training_episode(cls, episodes: int = 15):
        print(f"Initializing PyTorch RL Signage Training over {episodes} episodes...")
        floor_plan = {
            "building_bounds": {"min_x": 0.0, "max_x": 30.0, "min_y": 0.0, "max_y": 20.0},
            "exits": [
                {"id": "left_exit", "x": 0.0, "y": 10.0, "width": 1.5},
                {"id": "right_exit", "x": 30.0, "y": 10.0, "width": 1.5}
            ],
            "detected_walls": [], "rooms": [], "detected_obstacles": []
        }
        
        agent = cls(num_exits=len(floor_plan["exits"]))
        
        for e in range(episodes):
            config = SimConfig(num_agents=150, routing_policy="guided", seed=42+e)
            engine = CoreSimulationEngine(config)
            engine.initialize_from_floor_plan(floor_plan)
            engine.initialize_agents()
            
            state = agent.get_state(engine)
            total_reward = 0
            
            # Sub-step simulation loops
            while not engine.is_complete() and engine.time < 120.0:
                action = agent.act(state)
                # Apply action: 50% of uncommitted agents suddenly path to the chosen exit
                target_exit_id = engine.exits[action]["id"]
                for sim_agent in engine.agents:
                    if sim_agent.status != "evacuated" and np.random.rand() < 0.1:
                        sim_agent.target_exit = target_exit_id
                        
                # Progress simulation by 1.0 second chunks
                evacuated_before = engine.evacuated_count
                engine.update(1.0)
                evacuated_after = engine.evacuated_count
                
                next_state = agent.get_state(engine)
                # Reward: Highly reward throughput, punish long elapsed time
                reward = (evacuated_after - evacuated_before) * 10.0 - 1.0
                done = engine.is_complete()
                
                agent.memory.append((state, action, reward, next_state, done))
                state = next_state
                total_reward += reward # type: ignore
                
            agent.replay(batch_size=32)
            print(f"Episode {e+1}/{episodes} - Time: {engine.time:.1f}s - Epsilon: {agent.epsilon:.2f} - Reward: {total_reward:.1f}")

if __name__ == "__main__":
    RLOptimizer.run_training_episode()
