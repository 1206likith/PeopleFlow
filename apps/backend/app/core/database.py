from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
import logging
import uuid
from typing import Any, Optional
import time

logger = logging.getLogger(__name__)

class Database:
    client: Optional[Any] = None
    instrumented: Optional[Any] = None

db = Database()

class MockInsertResult:
    def __init__(self, inserted_id: str):
        self.inserted_id = inserted_id


class MockUpdateResult:
    matched_count = 0
    modified_count = 0


class MockDeleteResult:
    deleted_count = 0


class MockCursor:
    async def to_list(self, *args, **kwargs):
        return []

    def sort(self, *args, **kwargs):
        return self

    def skip(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self


class MockCollection:
    def __init__(self, name: str):
        self._name = name

    async def find_one(self, *args, **kwargs):
        if self._name == "floor_plans":
            return {
                "_id": "mock-default-floor-plan",
                "name": "Mock Floor Plan",
                "detected_walls": [
                    {"x1": 0, "y1": 0, "x2": 100, "y2": 0},
                    {"x1": 100, "y1": 0, "x2": 100, "y2": 100},
                    {"x1": 100, "y1": 100, "x2": 0, "y2": 100},
                    {"x1": 0, "y1": 100, "x2": 0, "y2": 0},
                ],
                "boundaries": [
                    {"x1": 0, "y1": 0, "x2": 100, "y2": 0},
                    {"x1": 100, "y1": 0, "x2": 100, "y2": 100},
                    {"x1": 100, "y1": 100, "x2": 0, "y2": 100},
                    {"x1": 0, "y1": 100, "x2": 0, "y2": 0},
                ],
                "building_bounds": {"min_x": 0, "min_y": 0, "max_x": 100, "max_y": 100},
                "exits": [
                    {"id": "exit-1", "x": 50, "y": 0, "z": 0, "width": 5.0, "capacity": 200},
                    {"id": "exit-2", "x": 50, "y": 100, "z": 100, "width": 5.0, "capacity": 200},
                ],
                "pipeline": "mock-fallback",
                "simulation_ready": True,
            }
        return None

    def find(self, *args, **kwargs):
        return MockCursor()

    async def insert_one(self, *args, **kwargs):
        # Keep mock IDs aligned with demo-mode fallback logic across routes/tests.
        return MockInsertResult(f"mock-{uuid.uuid4().hex[:12]}")

    async def update_one(self, *args, **kwargs):
        return MockUpdateResult()

    async def delete_one(self, *args, **kwargs):
        return MockDeleteResult()


class MockDatabase:
    """Mock database used when MongoDB is unavailable."""
    is_mock = True

    def __getattr__(self, name: str) -> Any:
        return MockCollection(name)


mock_db = MockDatabase()


class InstrumentedCollection:
    def __init__(self, collection: Any, name: str):
        self._collection = collection
        self._name = name

    def _record(self, operation: str, start_time: float, error: bool = False) -> None:
        duration = time.perf_counter() - start_time
        try:
            from app.core.metrics import (
                database_operations_total,
                database_operation_duration_seconds,
                database_operation_errors_total,
            )
            database_operations_total.labels(operation=operation, collection=self._name).inc()
            database_operation_duration_seconds.labels(operation=operation, collection=self._name).observe(duration)
            if error:
                database_operation_errors_total.labels(operation=operation, collection=self._name).inc()
        except Exception:
            pass

    async def find_one(self, *args, **kwargs):
        start = time.perf_counter()
        try:
            result = await self._collection.find_one(*args, **kwargs)
            self._record("find_one", start)
            return result
        except Exception:
            self._record("find_one", start, error=True)
            raise

    def find(self, *args, **kwargs):
        start = time.perf_counter()
        try:
            result = self._collection.find(*args, **kwargs)
            self._record("find", start)
            return result
        except Exception:
            self._record("find", start, error=True)
            raise

    async def insert_one(self, *args, **kwargs):
        start = time.perf_counter()
        try:
            result = await self._collection.insert_one(*args, **kwargs)
            self._record("insert_one", start)
            return result
        except Exception:
            self._record("insert_one", start, error=True)
            raise

    async def insert_many(self, *args, **kwargs):
        start = time.perf_counter()
        try:
            result = await self._collection.insert_many(*args, **kwargs)
            self._record("insert_many", start)
            return result
        except Exception:
            self._record("insert_many", start, error=True)
            raise

    async def update_one(self, *args, **kwargs):
        start = time.perf_counter()
        try:
            result = await self._collection.update_one(*args, **kwargs)
            self._record("update_one", start)
            return result
        except Exception:
            self._record("update_one", start, error=True)
            raise

    async def update_many(self, *args, **kwargs):
        start = time.perf_counter()
        try:
            result = await self._collection.update_many(*args, **kwargs)
            self._record("update_many", start)
            return result
        except Exception:
            self._record("update_many", start, error=True)
            raise

    async def delete_one(self, *args, **kwargs):
        start = time.perf_counter()
        try:
            result = await self._collection.delete_one(*args, **kwargs)
            self._record("delete_one", start)
            return result
        except Exception:
            self._record("delete_one", start, error=True)
            raise

    async def delete_many(self, *args, **kwargs):
        start = time.perf_counter()
        try:
            result = await self._collection.delete_many(*args, **kwargs)
            self._record("delete_many", start)
            return result
        except Exception:
            self._record("delete_many", start, error=True)
            raise

    async def replace_one(self, *args, **kwargs):
        start = time.perf_counter()
        try:
            result = await self._collection.replace_one(*args, **kwargs)
            self._record("replace_one", start)
            return result
        except Exception:
            self._record("replace_one", start, error=True)
            raise

    async def create_index(self, *args, **kwargs):
        start = time.perf_counter()
        try:
            result = await self._collection.create_index(*args, **kwargs)
            self._record("create_index", start)
            return result
        except Exception:
            self._record("create_index", start, error=True)
            raise

    def __getattr__(self, name: str) -> Any:
        return getattr(self._collection, name)


class InstrumentedDatabase:
    def __init__(self, database: Any):
        self._database = database

    @property
    def is_mock(self) -> bool:
        return getattr(self._database, "is_mock", False)

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._database, name)
        if hasattr(attr, "find_one"):
            return InstrumentedCollection(attr, name)
        return attr

    def __getitem__(self, name: str) -> Any:
        attr = self._database[name]
        if hasattr(attr, "find_one"):
            return InstrumentedCollection(attr, name)
        return attr

async def get_database():
    if db.client is None:
        if settings.IS_DEMO_MODE:
            return mock_db
        raise RuntimeError("Database client is unavailable in production mode")
    if db.instrumented is None:
        db.instrumented = InstrumentedDatabase(db.client[settings.MONGODB_DB_NAME])
    return db.instrumented

async def init_db():
    """Initialize database connection and create indexes with timeout"""
    import asyncio
    try:
        from app.core.config import settings

        if settings.DATABASE_MODE == "sqlite":
            from app.core.db_clients.sqlite import AsyncSQLiteClient
            db.client = AsyncSQLiteClient(settings.SQLITE_URL)
            await db.client._init_collections(
                settings.MONGODB_DB_NAME,
                ["simulations", "simulation_results", "simulation_data", "floor_plans", "simulation_batches", "simulation_sessions"]
            )
            logger.info("Connected to SQLite Database")
            
        elif settings.DATABASE_MODE == "local_file":
            from app.core.db_clients.local_file import AsyncLocalFileClient
            db.client = AsyncLocalFileClient(settings.LOCAL_FILE_DB_PATH)
            logger.info("Connected to Local File Database")
            
        else: # default to mongodb
            # Create client with shorter server selection timeout
            db.client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
                serverSelectionTimeoutMS=2000,  # 2 second timeout
                connectTimeoutMS=2000,
                socketTimeoutMS=2000
            )
            # Test connection with timeout
            try:
                await asyncio.wait_for(db.client.admin.command('ping'), timeout=2.0)
                logger.info("Connected to MongoDB")
            except asyncio.TimeoutError:
                db.client = None
                if settings.IS_DEMO_MODE:
                    logger.warning("MongoDB connection timeout. Running in demo mode.")
                    return
                raise RuntimeError("MongoDB connection timeout in production mode")
            except Exception as e:
                db.client = None
                if settings.IS_DEMO_MODE:
                    logger.warning(f"MongoDB ping failed: {e}. Running in demo mode.")
                    return
                raise RuntimeError(f"MongoDB ping failed in production mode: {e}")
        
        # Create indexes for production performance
        try:
            database = db.client[settings.MONGODB_DB_NAME]
            
            # Simulations collection indexes
            simulations_collection = database.simulations
            await asyncio.wait_for(simulations_collection.create_index("tenant_id"), timeout=1.0)
            await asyncio.wait_for(simulations_collection.create_index("status"), timeout=1.0)
            await asyncio.wait_for(simulations_collection.create_index("created_at"), timeout=1.0)
            await asyncio.wait_for(simulations_collection.create_index([("tenant_id", 1), ("created_at", -1)]), timeout=1.0)
            logger.info("Created indexes for simulations collection")
            
            # Simulation results collection indexes
            results_collection = database.simulation_results
            await asyncio.wait_for(results_collection.create_index("simulation_id"), timeout=1.0)
            await asyncio.wait_for(results_collection.create_index("timestamp"), timeout=1.0)
            await asyncio.wait_for(results_collection.create_index([("simulation_id", 1), ("timestamp", 1)]), timeout=1.0)
            await asyncio.wait_for(results_collection.create_index("created_at", expireAfterSeconds=2592000), timeout=1.0)
            logger.info("Created indexes for simulation_results collection")

            # Simulation data collection indexes
            simulation_data_collection = database.simulation_data
            await asyncio.wait_for(simulation_data_collection.create_index("simulation_id"), timeout=1.0)
            await asyncio.wait_for(simulation_data_collection.create_index("created_at"), timeout=1.0)
            await asyncio.wait_for(
                simulation_data_collection.create_index([("simulation_id", 1), ("created_at", 1)]),
                timeout=1.0,
            )
            logger.info("Created indexes for simulation_data collection")
            
            # Floor plans collection indexes
            floor_plans_collection = database.floor_plans
            await asyncio.wait_for(floor_plans_collection.create_index("tenant_id"), timeout=1.0)
            await asyncio.wait_for(floor_plans_collection.create_index("created_at"), timeout=1.0)
            await asyncio.wait_for(floor_plans_collection.create_index([("tenant_id", 1), ("created_at", -1)]), timeout=1.0)
            logger.info("Created indexes for floor_plans collection")

            # Simulation batch results collection indexes
            batches_collection = database.simulation_batches
            await asyncio.wait_for(batches_collection.create_index("batch_id", unique=True), timeout=1.0)
            await asyncio.wait_for(batches_collection.create_index("tenant_id"), timeout=1.0)
            await asyncio.wait_for(batches_collection.create_index("created_at"), timeout=1.0)
            await asyncio.wait_for(batches_collection.create_index([("tenant_id", 1), ("created_at", -1)]), timeout=1.0)
            logger.info("Created indexes for simulation_batches collection")

            # Simulation sessions collection indexes
            sessions_collection = database.simulation_sessions
            await asyncio.wait_for(sessions_collection.create_index("id", unique=True), timeout=1.0)
            await asyncio.wait_for(sessions_collection.create_index("created_at"), timeout=1.0)
            await asyncio.wait_for(sessions_collection.create_index("state.status"), timeout=1.0)
            logger.info("Created indexes for simulation_sessions collection")
        except asyncio.TimeoutError:
            logger.warning("Index creation timed out, continuing anyway")
        except Exception as e:
            logger.warning(f"Error creating indexes: {e}, continuing anyway")
        
    except Exception as e:
        db.client = None
        if settings.IS_DEMO_MODE:
            logger.warning(f"Failed to connect to MongoDB: {e}")
            logger.warning("Continuing without database - demo mode enabled")
            return
        raise RuntimeError(f"Failed to connect to MongoDB in production mode: {e}")

async def close_db():
    """Close database connection"""
    if db.client:
        db.client.close()
        logger.info("Disconnected from MongoDB")
    db.instrumented = None
