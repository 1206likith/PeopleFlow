import aiofiles
import json
import logging
from typing import Any, Dict, List, Optional
import uuid
import os

logger = logging.getLogger(__name__)

class LocalFileCursor:
    def __init__(self, items: List[Dict]):
        self._items = items
        self._skip = 0
        self._limit = len(items)
        
    def skip(self, limit: int):
        self._skip = limit
        return self
        
    def limit(self, limit: int):
        self._limit = limit
        return self
        
    def sort(self, *args, **kwargs):
        return self
        
    async def to_list(self, length: Optional[int] = None) -> List[Dict]:
        start = self._skip
        end = self._skip + (length if length is not None else self._limit)
        return self._items[start:end]

class AsyncLocalFileCollection:
    def __init__(self, db_dir: str, name: str):
        self.db_dir = db_dir
        self.name = name
        self.file_path = os.path.join(self.db_dir, f"{self.name}.json")
        os.makedirs(self.db_dir, exist_ok=True)
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w") as f:
                json.dump([], f)

    async def _read_all(self) -> List[Dict]:
        try:
            async with aiofiles.open(self.file_path, "r") as f:
                content = await f.read()
                return json.loads(content) if content else []
        except Exception:
            return []

    async def _write_all(self, data: List[Dict]) -> None:
        async with aiofiles.open(self.file_path, "w") as f:
            await f.write(json.dumps(data, default=str))

    def _parse_id(self, doc_id: Any) -> str:
        if hasattr(doc_id, "binary"): # ObjectId mock handle
            return str(doc_id)
        return str(doc_id)

    def _matches_filter(self, doc: Dict, filter: Dict) -> bool:
        for k, v in filter.items():
            if str(doc.get(k)) != str(v):
                return False
        return True

    async def insert_one(self, document: Dict[str, Any], *args, **kwargs):
        docs = await self._read_all()
        doc_copy = dict(document)
        if "_id" not in doc_copy:
            doc_copy["_id"] = str(uuid.uuid4())
        
        doc_copy["_id"] = self._parse_id(doc_copy["_id"])
        docs.append(doc_copy)
        await self._write_all(docs)
        
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
            
        docs = await self._read_all()
        inserted_ids = []
        for doc in documents:
            doc_copy = dict(doc)
            if "_id" not in doc_copy:
                doc_copy["_id"] = str(uuid.uuid4())
            doc_copy["_id"] = self._parse_id(doc_copy["_id"])
            docs.append(doc_copy)
            inserted_ids.append(doc_copy["_id"])
            
        await self._write_all(docs)
        return InsertManyResult(inserted_ids)

    async def find_one(self, filter: Dict[str, Any], *args, **kwargs) -> Optional[Dict]:
        docs = await self._read_all()
        for doc in docs:
            if self._matches_filter(doc, filter):
                return doc
        return None

    def find(self, filter: Dict[str, Any] = None, *args, **kwargs) -> LocalFileCursor:
        filter = filter or {}
        class AsyncLocalFileCursor(LocalFileCursor):
            def __init__(self, col, flt):
                self.col = col
                self.flt = flt
                self._skip = 0
                self._limit = None
                
            async def to_list(self, length: Optional[int] = None) -> List[Dict]:
                docs = await self.col._read_all()
                results = [d for d in docs if self.col._matches_filter(d, self.flt)]
                
                start = self._skip
                end = self._skip + (length if length is not None else (self._limit if self._limit else len(results)))
                return results[start:end]

        return AsyncLocalFileCursor(self, filter)

    async def update_one(self, filter: Dict[str, Any], update: Dict[str, Any], *args, **kwargs):
        docs = await self._read_all()
        
        class UpdateResult:
            matched_count = 0
            modified_count = 0
            
        res = UpdateResult()
        matched = False
        
        for idx, doc in enumerate(docs):
            if self._matches_filter(doc, filter):
                res.matched_count = 1
                set_data = update.get("$set", update)
                for k, v in set_data.items():
                    doc[k] = v
                docs[idx] = doc
                matched = True
                res.modified_count = 1
                break
                
        if not matched and kwargs.get("upsert"):
            new_doc = filter.copy()
            set_data = update.get("$set", update)
            new_doc.update(set_data)
            if "_id" not in new_doc:
                new_doc["_id"] = str(uuid.uuid4())
            docs.append(new_doc)
            res.modified_count = 1
            
        await self._write_all(docs)
        return res
        
    async def delete_one(self, filter: Dict[str, Any], *args, **kwargs):
        docs = await self._read_all()
        
        class DeleteResult:
            deleted_count = 0
            
        new_docs = []
        deleted = False
        for doc in docs:
            if not deleted and self._matches_filter(doc, filter):
                deleted = True
                continue
            new_docs.append(doc)
            
        if deleted:
            await self._write_all(new_docs)
            res = DeleteResult()
            res.deleted_count = 1
            return res
            
        return DeleteResult()
        
    async def create_index(self, *args, **kwargs):
        pass

class AsyncLocalFileDatabase:
    def __init__(self, db_dir: str):
        self.db_dir = db_dir
        self._collections = {}
        
    def __getattr__(self, name: str) -> AsyncLocalFileCollection:
        if name not in self._collections:
            self._collections[name] = AsyncLocalFileCollection(self.db_dir, name)
        return self._collections[name]
        
    def __getitem__(self, name: str) -> AsyncLocalFileCollection:
        return self.__getattr__(name)

class AsyncLocalFileClient:
    """A minimal mock of AsyncIOMotorClient backed by Local JSON files."""
    
    def __init__(self, db_dir: str, **kwargs):
        self.db_dir = db_dir
        os.makedirs(self.db_dir, exist_ok=True)
        self.admin = self.AdminFallback()

    class AdminFallback:
        async def command(self, cmd):
            if cmd == "ping":
                return {"ok": 1.0}

    def __getitem__(self, name: str) -> AsyncLocalFileDatabase:
        db_path = os.path.join(self.db_dir, name)
        return AsyncLocalFileDatabase(db_path)
        
    def close(self):
        pass
