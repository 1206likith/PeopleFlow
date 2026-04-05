# Offline Deployment for PeopleFlow

This guide explains how to set up and run PeopleFlow in a fully offline, high-performance environment using your computer's GPU.

## Prerequisites
1. **Docker & Docker Compose**: Installed on your machine.
2. **NVIDIA GPU Drivers**: Ensure your host machine has the latest drivers installed.
3. **NVIDIA Container Toolkit**: Required for Docker to access your GPU.
   - [Installation Guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)

## Setup and Launch

1. **Verify GPU Access**:
   Run `nvidia-smi` in your terminal to ensure the drivers are correctly installed.

2. **Configure Environment**:
   Copy the example environment file if needed, but defaults are set in the compose file.
   ```bash
   cp infra/deployment/environment.example.env .env
   ```

3. **Build and Start**:
   From the project root:
   ```bash
   docker-compose -f infra/deployment/docker-compose.offline.yml up --build -d
   ```

4. **Access the Application**:
   - **Frontend**: http://localhost
   - **API Docs**: http://localhost/api/v2/docs

## Architecture
- **Backend**: Python FastAPI with CUDA support, running high-performance simulations.
- **Frontend**: React application served via Nginx.
- **Database**: Local MongoDB instance for persistent state.
- **Cache**: Local Redis for real-time WebSocket signals and caching.

## Performance Tuning
To monitor GPU utilization while the simulation is running:
```bash
docker exec -it peopleflow-backend-1 nvidia-smi -l 1
```
