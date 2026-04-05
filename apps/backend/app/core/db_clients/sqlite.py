import aiosqlite
import json
import logging
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger(__name__)

class SQLiteCursor:
    def __init__(self, items: List[Dict]):
        self._items = items
        self._skip = 0
        self._limit = len(items)
        self._sort_spec: List[tuple[str, int]] = []
        
    def skip(self, limit: int):
        self._skip = limit
        return self
        
    def limit(self, limit: int):
        self._limit = limit
        return self
        
    @staticmethod
    def _normalize_sort_spec(*args) -> List[tuple[str, int]]:
        if not args:
            return []
        if len(args) == 1 and isinstance(args[0], list):
            return [
                (str(field), int(direction))
                for field, direction in args[0]
            ]
        if len(args) >= 2:
            return [(str(args[0]), int(args[1]))]
        return [(str(args[0]), 1)]

    @staticmethod
    def _sort_key(value: Any):
        if value is None:
            return (1, "")
        if isinstance(value, (int, float)):
            return (0, value)
        if isinstance(value, bool):
            return (0, int(value))
        if isinstance(value, (dict, list)):
            return (0, json.dumps(value, sort_keys=True, default=str))
        return (0, str(value))

    def _apply_sort(self, items: List[Dict]) -> List[Dict]:
        sorted_items = list(items)
        for field, direction in reversed(self._sort_spec):
            try:
                sorted_items.sort(
                    key=lambda doc: self._sort_key(doc.get(field)),
                    reverse=direction < 0,
                )
            except TypeError:
                sorted_items.sort(
                    key=lambda doc: self._sort_key(str(doc.get(field))),
                    reverse=direction < 0,
                )
        return sorted_items

    def sort(self, *args, **kwargs):
        self._sort_spec = self._normalize_sort_spec(*args)
        return self
        
    async def to_list(self, length: Optional[int] = None) -> List[Dict]:
        items = self._apply_sort(self._items)
        start = self._skip
        end = self._skip + (length if length is not None else self._limit)
        return items[start:end]

class AsyncSQLiteCollection:
    def __init__(self, db_path: str, name: str):
        self.db_path = db_path
        self.name = name

    async def _execute(self, query: str, parameters: tuple = ()) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(query, parameters)
            await db.commit()

    async def _fetchall(self, query: str, parameters: tuple = ()) -> List[tuple]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(query, parameters) as cursor:
                return await cursor.fetchall()
                
    def _parse_id(self, doc_id: Any) -> str:
        if hasattr(doc_id, "binary"): # ObjectId mock handle
            return str(doc_id)
        return str(doc_id)

    async def insert_one(self, document: Dict[str, Any], *args, **kwargs):
        doc_copy = dict(document)
        if "_id" not in doc_copy:
            doc_copy["_id"] = str(uuid.uuid4())
        
        doc_id = self._parse_id(doc_copy["_id"])
        
        # Serialize keeping _id inside
        doc_json = json.dumps(doc_copy, default=str)
        
        await self._execute(
            f"INSERT INTO {self.name} (id, document) VALUES (?, ?)",
            (doc_id, doc_json)
        )
        
        class InsertResult:
            def __init__(self, inserted_id):
                self.inserted_id = inserted_id
                
        return InsertResult(doc_copy["_id"])
        
    async def insert_many(self, documents: List[Dict], *args, **kwargs):
        class InsertManyResult:
            def __init__(self, inserted_ids):
                self.inserted_ids = inserted_ids
        
        if not documents:
            return InsertManyResult([])
            
        inserted_ids = []
        async with aiosqlite.connect(self.db_path) as db:
            for doc in documents:
                doc_copy = dict(doc)
                if "_id" not in doc_copy:
                    doc_copy["_id"] = str(uuid.uuid4())
                
                doc_id = self._parse_id(doc_copy["_id"])
                doc_json = json.dumps(doc_copy, default=str)
                await db.execute(f"INSERT INTO {self.name} (id, document) VALUES (?, ?)", (doc_id, doc_json))
                inserted_ids.append(doc_copy["_id"])
            await db.commit()
            
        return InsertManyResult(inserted_ids)

    async def find_one(self, filter: Dict[str, Any], *args, **kwargs) -> Optional[Dict]:
        if "_id" in filter:
            doc_id = self._parse_id(filter["_id"])
            rows = await self._fetchall(f"SELECT document FROM {self.name} WHERE id = ?", (doc_id,))
            if rows:
                return json.loads(rows[0][0])
        
        # Fallback for arbitrary filters (slow scan, good enough for local mode)
        rows = await self._fetchall(f"SELECT document FROM {self.name}")
        for row in rows:
            doc = json.loads(row[0])
            match = True
            for k, v in filter.items():
                # basic match
                if str(doc.get(k)) != str(v):
                    match = False
                    break
            if match:
                return doc
                
        return None

    def find(self, filter: Dict[str, Any] = None, *args, **kwargs) -> SQLiteCursor:
        filter = filter or {}
        # Since this evaluates lazily in motor but we can't do perfectly,
        # we will fetch all and filter in memory synchronously here to populate the cursor.
        # This is safe for a local execution.
        # Create a sync wrapper for the fetch (hacky but it allows `.find()` to be sync)
        
        # Actually, because we can't reliably block in an async loop without deadlocking,
        # Motor's .find() returns an AsyncIOMotorCursor. We will simulate that closely:
        class AsyncAioSQLiteCursor(SQLiteCursor):
            def __init__(self, col, flt):
                super().__init__([])
                self.col = col
                self.flt = flt
                self._limit = None
                
            async def to_list(self, length: Optional[int] = None) -> List[Dict]:
                rows = await self.col._fetchall(f"SELECT document FROM {self.col.name}")
                results = []
                for row in rows:
                    doc = json.loads(row[0])
                    match = True
                    for k, v in self.flt.items():
                        if str(doc.get(k)) != str(v):
                            match = False
                            break
                    if match:
                        results.append(doc)

                results = self._apply_sort(results)
                start = self._skip
                end = self._skip + (length if length is not None else (self._limit if self._limit else len(results)))
                return results[start:end]

        return AsyncAioSQLiteCursor(self, filter)

    async def update_one(self, filter: Dict[str, Any], update: Dict[str, Any], *args, **kwargs):
        doc = await self.find_one(filter)
        class UpdateResult:
            matched_count = 0
            modified_count = 0
            
        res = UpdateResult()
        if not doc:
            # Upsert?
            if kwargs.get("upsert"):
                new_doc = filter.copy()
                set_data = update.get("$set", update)
                new_doc.update(set_data)
                await self.insert_one(new_doc)
                res.matched_count = 0
                res.modified_count = 1
            return res
            
        res.matched_count = 1
        
        set_data = update.get("$set", update)
        for k, v in set_data.items():
            doc[k] = v
            
        doc_id = self._parse_id(doc["_id"])
        await self._execute(
            f"UPDATE {self.name} SET document = ? WHERE id = ?",
            (json.dumps(doc, default=str), doc_id)
        )
        res.modified_count = 1
        return res
        
    async def delete_one(self, filter: Dict[str, Any], *args, **kwargs):
        class DeleteResult:
            deleted_count = 0
            
        doc = await self.find_one(filter)
        if doc:
            doc_id = self._parse_id(doc["_id"])
            await self._execute(f"DELETE FROM {self.name} WHERE id = ?", (doc_id,))
            res = DeleteResult()
            res.deleted_count = 1
            return res
        return DeleteResult()
        
    async def create_index(self, *args, **kwargs):
        # SQLite handles this implicitly for the ID field, bypass for custom fields.
        pass

class AsyncSQLiteDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._collections = {}
        
    def __getattr__(self, name: str) -> AsyncSQLiteCollection:
        if name not in self._collections:
            self._collections[name] = AsyncSQLiteCollection(self.db_path, name)
        return self._collections[name]
        
    def __getitem__(self, name: str) -> AsyncSQLiteCollection:
        return self.__getattr__(name)

class AsyncSQLiteClient:
    """A minimal mock of AsyncIOMotorClient backed by SQLite."""
    
    def __init__(self, url: str, **kwargs):
        self.url = url
        # "sqlite+aiosqlite:///./data/peopleflow.db" -> "./data/peopleflow.db"
        self.db_path = url.split("///")[-1] if "///" in url else url
        import os
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self.admin = self.AdminFallback()

    class AdminFallback:
        async def command(self, cmd):
            if cmd == "ping":
                return {"ok": 1.0}

    async def _init_collections(self, db_name: str, collections: List[str]):
        async with aiosqlite.connect(self.db_path) as db:
            for coll in collections:
                await db.execute(f"CREATE TABLE IF NOT EXISTS {coll} (id TEXT PRIMARY KEY, document JSON)")
            await db.commit()

    def __getitem__(self, name: str) -> AsyncSQLiteDatabase:
        return AsyncSQLiteDatabase(self.db_path)
        
    def close(self):
        pass
