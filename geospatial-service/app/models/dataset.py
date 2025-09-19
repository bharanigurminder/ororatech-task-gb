from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

class ClassificationSystem(str, Enum):
    FBFM40 = "FBFM40"
    SENTINEL_FUEL_2024 = "SENTINEL_FUEL_2024"
    LANDFIRE_US = "LANDFIRE_US"
    UNKNOWN = "UNKNOWN"

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ValidationResult(BaseModel):
    is_valid: bool
    success: bool = False
    format: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    bands: Optional[int] = None
    dtype: Optional[str] = None
    crs: Optional[str] = None
    transform: Optional[List[float]] = None
    bbox: Optional[List[float]] = None
    bounds: Optional[List[float]] = None
    resolution: Optional[float] = None
    pixel_count: Optional[int] = None
    detected_classes: Optional[List[int]] = None
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)

class ClassMappingRule(BaseModel):
    target: int
    confidence: float
    name: str

class ClassMapping(BaseModel):
    source_system: str
    target_system: str = "FBFM40"
    mapping_required: bool
    auto_mappable: bool = False
    direct_mapping: bool = False
    mappings: Dict[int, int] = Field(default_factory=dict)
    confidence_scores: Dict[int, float] = Field(default_factory=dict)
    unmapped_classes: List[int] = Field(default_factory=list)
    auto_mapped_count: int = 0
    manual_review_count: int = 0

class COGResult(BaseModel):
    success: bool
    output_path: Optional[str] = None
    original_size_mb: Optional[float] = None
    cog_size_mb: Optional[float] = None
    compression_ratio: Optional[float] = None
    cog_validation: Optional[Dict[str, Any]] = None
    processing_time_seconds: Optional[float] = None
    error: Optional[str] = None

class ProcessingRequest(BaseModel):
    tenant_id: str = Field(..., description="Tenant identifier")
    classification_system: str = Field(default="auto-detect", description="Classification system or auto-detect")
    force_reprocess: bool = Field(default=False, description="Force reprocessing even if file exists")

class ProcessingResult(BaseModel):
    success: bool
    dataset_id: Optional[str] = None
    validation: Optional[ValidationResult] = None
    classification: Optional[Dict[str, Any]] = None
    processing: Optional[COGResult] = None
    paths: Optional[Dict[str, str]] = None
    error: Optional[str] = None
    processing_time_seconds: Optional[float] = None

class HealthCheck(BaseModel):
    status: str
    gdal_version: Optional[str] = None
    rasterio_version: Optional[str] = None
    available_drivers: Optional[List[str]] = None
    memory_usage_mb: Optional[float] = None