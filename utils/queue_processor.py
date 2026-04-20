import asyncio
import os
import json
import time
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum
import threading

class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class BatchTask:
    task_id: str
    status: TaskStatus
    total_files: int
    processed_files: int
    current_file: str
    results: List[str]
    errors: List[str]
    created_at: float
    updated_at: float

class BatchQueueProcessor:
    """Processeur batch avec file d'attente pour Render free"""
    
    def __init__(self, max_concurrent=1):  # Force à 1 pour éviter le crash
        self.tasks: Dict[str, BatchTask] = {}
        self.queue = asyncio.Queue()
        self.worker_running = False
        self.max_concurrent = max_concurrent
        
    async def start_worker(self):
        """Démarre le worker en arrière-plan"""
        if self.worker_running:
            return
        self.worker_running = True
        asyncio.create_task(self._worker_loop())
        print("✅ Queue worker démarré")
    
    async def _worker_loop(self):
        """Boucle principale du worker"""
        while self.worker_running:
            try:
                # Récupère la tâche suivante
                task_info = await self.queue.get()
                task_id = task_info["task_id"]
                processing_func = task_info["func"]
                files = task_info["files"]
                temp_dir = task_info["temp_dir"]
                
                # Traite la tâche
                await self._process_task(task_id, processing_func, files, temp_dir)
                
                self.queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Erreur worker: {e}")
                await asyncio.sleep(1)
    
    async def _process_task(self, task_id: str, processing_func, files: List, temp_dir: str):
        """Traite une tâche fichier par fichier"""
        task = self.tasks.get(task_id)
        if not task:
            return
        
        all_results = []
        
        for idx, file in enumerate(files):
            # Mise à jour du statut
            task.status = TaskStatus.PROCESSING
            task.current_file = file.filename
            task.processed_files = idx
            task.updated_at = time.time()
            
            try:
                # Traite un fichier à la fois
                result = await asyncio.to_thread(processing_func, file, temp_dir, idx)
                
                if result:
                    if isinstance(result, list):
                        all_results.extend(result)
                    else:
                        all_results.append(result)
                    
                print(f"✅ [{idx+1}/{len(files)}] Traité: {file.filename}")
                
            except Exception as e:
                error_msg = f"Erreur {file.filename}: {str(e)}"
                task.errors.append(error_msg)
                print(f"❌ {error_msg}")
            
            # Petit délai pour libérer la RAM
            await asyncio.sleep(0.5)
        
        # Finalisation
        task.results = all_results
        task.status = TaskStatus.COMPLETED if all_results else TaskStatus.FAILED
        task.updated_at = time.time()
        
        print(f"🎉 Batch {task_id} terminé: {len(all_results)} fichiers générés")
    
    async def add_batch(self, task_id: str, files: List, processing_func, temp_dir: str) -> str:
        """Ajoute un batch à la queue"""
        
        # Créer la tâche
        task = BatchTask(
            task_id=task_id,
            status=TaskStatus.PENDING,
            total_files=len(files),
            processed_files=0,
            current_file="",
            results=[],
            errors=[],
            created_at=time.time(),
            updated_at=time.time()
        )
        
        self.tasks[task_id] = task
        
        # Ajouter à la queue
        await self.queue.put({
            "task_id": task_id,
            "func": processing_func,
            "files": files,
            "temp_dir": temp_dir
        })
        
        return task_id
    
    def get_status(self, task_id: str) -> Dict:
        """Récupère le statut d'une tâche"""
        task = self.tasks.get(task_id)
        if not task:
            return {"error": "Task not found"}
        
        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "total_files": task.total_files,
            "processed_files": task.processed_files,
            "current_file": task.current_file,
            "progress": int((task.processed_files / task.total_files) * 100) if task.total_files > 0 else 0,
            "errors": task.errors,
            "completed": task.status == TaskStatus.COMPLETED,
            "results_count": len(task.results)
        }
    
    def get_results(self, task_id: str) -> List[str]:
        """Récupère les résultats d'une tâche"""
        task = self.tasks.get(task_id)
        return task.results if task else []
    
    def cleanup_task(self, task_id: str):
        """Nettoie une tâche terminée"""
        if task_id in self.tasks:
            del self.tasks[task_id]

# Instance globale
batch_processor = BatchQueueProcessor(max_concurrent=1)