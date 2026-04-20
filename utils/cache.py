import os
import hashlib
import pickle
from datetime import datetime, timedelta
from typing import Any, Optional
import tempfile

class PDFCache:
    def __init__(self, cache_dir: str = None, max_age_hours: int = 24):
        self.cache_dir = cache_dir or os.path.join(tempfile.gettempdir(), "umbrella_cache")
        self.max_age = timedelta(hours=max_age_hours)
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _get_cache_key(self, file_path: str, operation: str, params: dict = None) -> str:
        content = f"{file_path}:{os.path.getmtime(file_path)}:{operation}"
        if params:
            content += f":{str(sorted(params.items()))}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, file_path: str, operation: str, params: dict = None) -> Optional[Any]:
        cache_key = self._get_cache_key(file_path, operation, params)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        
        if os.path.exists(cache_file):
            mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
            if datetime.now() - mtime < self.max_age:
                try:
                    with open(cache_file, 'rb') as f:
                        return pickle.load(f)
                except:
                    pass
        return None
    
    def set(self, file_path: str, operation: str, result: Any, params: dict = None):
        cache_key = self._get_cache_key(file_path, operation, params)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(result, f)
        except Exception as e:
            print(f"⚠️ Erreur cache: {e}")
    
    def clear(self, file_path: str = None):
        if file_path:
            file_hash = hashlib.md5(file_path.encode()).hexdigest()
            for f in os.listdir(self.cache_dir):
                if f.startswith(file_hash[:8]):
                    os.remove(os.path.join(self.cache_dir, f))
        else:
            for f in os.listdir(self.cache_dir):
                os.remove(os.path.join(self.cache_dir, f))
    
    def get_stats(self) -> dict:
        files = os.listdir(self.cache_dir)
        total_size = sum(os.path.getsize(os.path.join(self.cache_dir, f)) for f in files)
        
        return {
            "total_files": len(files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "cache_dir": self.cache_dir
        }

# Instance globale
pdf_cache = PDFCache()