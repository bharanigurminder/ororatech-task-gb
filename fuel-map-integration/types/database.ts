export interface Tenant {
  id: string;
  name: string;
  email: string;
  created_at: string;
}

export interface Dataset {
  id: string;
  tenant_id: string;
  type: 'global_baseline' | 'customer_private';
  name: string;
  classification_system: string;
  resolution_meters: number;
  file_path?: string;
  original_file?: string;
  normalized_cog?: string;
  bbox: [number, number, number, number];
  pixel_count: number;
  status: 'active' | 'processed' | 'processing' | 'failed';
  priority: number;
  processing?: {
    validation_status: string;
    cog_created: boolean;
    size_reduction: string;
    processing_time_seconds: number;
  };
  created_at: string;
  updated_at?: string;
}

export interface ClassMapping {
  source_system: string;
  target_system: string;
  mappings: Record<string, {
    target: number;
    confidence: number;
    name: string;
  }>;
  unmapped_classes: number[];
  auto_mapped_count: number;
  manual_review_count: number;
  created_at: string;
}

export interface SpatialCoverage {
  dataset_id: string;
  geometry: {
    type: 'Polygon';
    coordinates: number[][][];
  };
  priority: number;
  resolution_meters: number;
}

export interface SystemConfig {
  canonical_system: string;
  default_resolution: number;
  supported_formats: string[];
  max_file_size_mb: number;
  processing_timeout_seconds: number;
}

export interface Database {
  tenants: Record<string, Tenant>;
  datasets: Record<string, Dataset>;
  class_mappings: Record<string, ClassMapping>;
  spatial_coverage: Record<string, SpatialCoverage[]>;
  system_config: SystemConfig;
}

export interface AccessControl {
  tenant_datasets: Record<string, {
    private_datasets: string[];
    shared_datasets: string[];
    global_access: boolean;
  }>;
  dataset_permissions: Record<string, {
    owner: string;
    visibility: 'private' | 'public';
    allowed_tenants: string[];
    public_access: boolean;
  }>;
}

export interface FuelQueryResult {
  fuel_class: number;
  source_dataset: string;
  resolution_meters: number;
  priority: number;
  data_source: string;
}

export interface DataSourcePlan {
  primary_source: SpatialCoverage | null;
  fallback_areas: SpatialCoverage[];
  resolution_strategy: 'highest_available' | 'consistent' | 'performance';
}