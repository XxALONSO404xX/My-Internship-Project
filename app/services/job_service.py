"""
Simplified job service stub that maintains API compatibility but doesn't do any real work.
This stub implementation allows code that depends on the job service to continue functioning.
"""
import uuid
import logging
import os
import json
from typing import Dict, Any, Optional, List, Callable, Awaitable
from datetime import datetime

logger = logging.getLogger(__name__)

class JobStatus:
    """Status constants for jobs - maintained for API compatibility"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"
    CANCELLED = "cancelled"

class Job:
    """Simplified stub for a long-running job"""
    
    def __init__(
            self, 
            job_id: str, 
            job_type: str, 
            params: Dict[str, Any],
            owner_id: Optional[str] = None,
            max_runtime: int = 3600
        ):
        self.id = job_id
        self.job_type = job_type
        self.params = params
        self.owner_id = owner_id
        self.status = JobStatus.COMPLETED  # Always mark as completed
        self.progress = 100  # Always mark as 100% complete
        self.result = {"success": True, "message": "Operation completed"}  # Default success result
        self.error = None
        self.created_at = datetime.utcnow().isoformat()
        self.started_at = datetime.utcnow().isoformat()
        self.completed_at = datetime.utcnow().isoformat()
        self.total_items = 1
        self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary"""
        return {
            "job_id": self.id,
            "job_type": self.job_type,
            "status": self.status,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "owner_id": self.owner_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Job':
        """Create job from dictionary"""
        job = cls(
            job_id=data["job_id"],
            job_type=data["job_type"],
            params={},
            owner_id=data.get("owner_id")
        )
        return job

class JobService:
    """Service for managing background jobs"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(JobService, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance
    
    def initialize(self):
        """Initialize the job service"""
        self.jobs = {}
        self.job_handlers = {}
        self.running_tasks = {}
        self.data_file = os.path.join("data", "jobs.json")
        self._monitoring_started = False
        
        # Create data directory if it doesn't exist
        os.makedirs("data", exist_ok=True)
        
        # Load existing jobs
        self._load_jobs()
        
        # The monitoring task will be started later by start_monitoring
        # NOT during module import time to avoid "no running event loop" error
        
        logger.info("Job service initialized")
    
    def _load_jobs(self):
        """Load jobs from disk"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r") as f:
                    data = json.load(f)
                    for job_data in data:
                        # Reconstruct job from saved data
                        job_id = job_data.get("id")
                        if job_id:
                            self.jobs[job_id] = job_data
        except Exception as e:
            logger.error(f"Error loading jobs: {str(e)}")
            # Continue with empty jobs rather than failing startup
            self.jobs = {}
    
    def register_handler(self, job_type: str, handler: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]):
        """Register a handler for a job type (stub)"""
        logger.info(f"Registering handler for job type: {job_type} (stub implementation)")
        self.job_handlers[job_type] = handler
        return True
    
    async def create_job(self, 
                       job_type: str, 
                       params: Dict[str, Any], 
                       owner_id: Optional[str] = None,
                       max_runtime: int = 3600,
                       start_immediately: bool = True) -> str:
        """Create a new job (stub)"""
        job_id = str(uuid.uuid4())
        logger.info(f"Created job {job_id} of type {job_type} (stub implementation)")
        
        # Create a completed job right away
        job = Job(job_id, job_type, params, owner_id)
        self.jobs[job_id] = job.to_dict()
        
        return job_id
    
    async def start_job(self, job_id: str) -> bool:
        """Start a job (stub)"""
        logger.info(f"Starting job {job_id} (stub implementation)")
        return True
    
    async def update_job_progress(self, job_id: str, progress: int, message: Optional[str] = None):
        """Update the progress of a job (stub)"""
        logger.info(f"Updating job {job_id} progress to {progress} (stub implementation)")
        return True
    
    async def update_job_metadata(self, job_id: str, metadata: Dict[str, Any]):
        """Update job metadata (stub)"""
        logger.info(f"Updating job {job_id} metadata (stub implementation)")
        return True
    
    async def update_job_status(self, job_id: str, status: str):
        """Update job status (stub)"""
        logger.info(f"Updating job {job_id} status to {status} (stub implementation)")
        return True
    
    async def complete_job(self, job_id: str, result: Any):
        """Mark a job as completed (stub)"""
        logger.info(f"Completing job {job_id} (stub implementation)")
        return True
    
    async def fail_job(self, job_id: str, error: str):
        """Mark a job as failed (stub)"""
        logger.info(f"Failing job {job_id}: {error} (stub implementation)")
        return True
    
    async def cancel_job(self, job_id: str):
        """Cancel a job (stub)"""
        logger.info(f"Cancelling job {job_id} (stub implementation)")
        return True
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a job by ID (stub)"""
        # Return a default completed job
        if job_id in self.jobs:
            return self.jobs[job_id]
            
        default_job = {
            "job_id": job_id,
            "job_type": "unknown",
            "status": JobStatus.COMPLETED,
            "progress": 100,
            "result": {"message": "Operation completed"},
            "error": None,
            "created_at": datetime.utcnow().isoformat(),
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "owner_id": None
        }
        return default_job
    
    def get_jobs(self, 
               owner_id: Optional[str] = None, 
               status: Optional[str] = None,
               job_type: Optional[str] = None,
               limit: int = 100,
               offset: int = 0) -> List[Dict[str, Any]]:
        """Get jobs with optional filtering (stub)"""
        # Return an empty list or the stored jobs
        return list(self.jobs.values())
    
    def check_job_exists(self, job_type: str, params: Dict[str, Any]) -> Optional[str]:
        """Check if a similar job already exists (stub)"""
        return None
    
    async def start_monitoring(self):
        """Start the job monitoring task (stub)"""
        try:
            logger.info("Job monitoring service disabled in this simplified implementation")
            return True
        except RuntimeError:
            logger.warning("No running event loop available. Job monitoring not started.")
            return False

# Create singleton instance
job_service = JobService()
