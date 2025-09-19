import { NextRequest, NextResponse } from 'next/server';
import { LocalJSONDatabase } from '@/lib/database';
import { TenantService } from '@/lib/tenant-service';

const db = new LocalJSONDatabase();
const tenantService = new TenantService(db);

const FASTAPI_BASE_URL = process.env.FASTAPI_URL || 'http://localhost:8001';

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const file = formData.get('file') as File;
    const tenantId = formData.get('tenant_id') as string;
    const classificationSystem = formData.get('classification_system') as string || 'auto-detect';
    const datasetType = formData.get('dataset_type') as string || 'regional';
    const forceReprocess = formData.get('force_reprocess') === 'true';

    // Validate inputs
    if (!file || !tenantId) {
      return NextResponse.json(
        { error: 'File and tenant_id are required' },
        { status: 400 }
      );
    }

    // Validate tenant
    const isValidTenant = await tenantService.validateTenant(tenantId);
    if (!isValidTenant) {
      return NextResponse.json(
        { error: 'Invalid tenant ID' },
        { status: 403 }
      );
    }

    // Check upload quota
    const estimatedSizeMb = file.size / (1024 * 1024);
    const canUpload = await tenantService.canUploadDataset(tenantId, estimatedSizeMb);

    if (!canUpload.can_upload) {
      return NextResponse.json(
        { error: canUpload.reason },
        { status: 400 }
      );
    }

    // Prepare FormData for FastAPI
    const fastApiFormData = new FormData();
    fastApiFormData.append('file', file);
    fastApiFormData.append('tenant_id', tenantId);
    fastApiFormData.append('classification_system', classificationSystem);
    fastApiFormData.append('dataset_type', datasetType);
    fastApiFormData.append('force_reprocess', forceReprocess.toString());

    // Forward request to FastAPI service with extended timeout for large files
    console.log(`Forwarding request to FastAPI: ${FASTAPI_BASE_URL}/process-fuel-map`);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 600000); // 10 minute timeout

    try {
      const fastApiResponse = await fetch(`${FASTAPI_BASE_URL}/process-fuel-map`, {
        method: 'POST',
        body: fastApiFormData,
        signal: controller.signal,
        headers: {
          // Remove content-type to let browser set it with boundary for multipart/form-data
        },
        // Add specific timeout configurations
        keepalive: false,
        // @ts-ignore - These properties may not be in TypeScript definitions
        timeout: 600000, // 10 minutes
        highWaterMark: 1024 * 1024, // 1MB buffer
      });

      clearTimeout(timeoutId);

      const result = await fastApiResponse.json();

      // If FastAPI processing succeeded, update local database
      if (result.success && result.dataset_id) {
        try {
          await updateLocalDatabase(result, tenantId, datasetType);
          console.log(`Updated local database for dataset: ${result.dataset_id}`);
        } catch (dbError) {
          console.error('Failed to update local database:', dbError);
          // Don't fail the entire request if database update fails
          result.warnings = result.warnings || [];
          result.warnings.push('Failed to update local database');
        }
      }

      // Return result with appropriate status code
      const statusCode = result.success ? 200 : 400;
      return NextResponse.json(result, { status: statusCode });

    } catch (fetchError: any) {
      clearTimeout(timeoutId);

      if (fetchError.name === 'AbortError') {
        return NextResponse.json(
          {
            error: 'Processing timeout - large files may take longer to process',
            details: 'Request timed out after 10 minutes. Please try again or contact support for very large files.'
          },
          { status: 408 }
        );
      }

      throw fetchError; // Re-throw other fetch errors to be handled by outer catch
    }

  } catch (error: any) {
    console.error('Error in process-geospatial endpoint:', error);

    // Handle specific error types
    if (error instanceof TypeError && error.message.includes('fetch')) {
      return NextResponse.json(
        {
          error: 'Failed to connect to geospatial processing service',
          details: 'FastAPI service may not be running'
        },
        { status: 503 }
      );
    }

    return NextResponse.json(
      { error: 'Internal server error during geospatial processing' },
      { status: 500 }
    );
  }
}

async function updateLocalDatabase(processingResult: any, tenantId: string, datasetType: string) {
  const { dataset_id, validation, classification, processing, paths } = processingResult;

  // Determine dataset type and tenant assignment
  const isGlobal = datasetType === 'global';
  const assignedTenantId = isGlobal ? 'system' : tenantId;
  const priority = isGlobal ? 0 : 1; // Global datasets have lower priority
  const type = isGlobal ? 'global_baseline' : 'customer_private';

  // Create dataset entry
  const dataset = {
    id: dataset_id,
    tenant_id: assignedTenantId,
    type: type as const,
    name: isGlobal ? `Global Baseline ${dataset_id}` : `Regional Dataset ${dataset_id}`,
    classification_system: classification.detected_system,
    resolution_meters: validation.resolution || 30,
    original_file: paths.original,
    normalized_cog: paths.cog,
    bbox: validation.bbox,
    pixel_count: validation.pixel_count || 0,
    status: 'processed' as const,
    priority: priority,
    processing: {
      validation_status: validation.warnings?.length > 0 ? 'passed_with_warnings' : 'passed',
      cog_created: processing.success,
      size_reduction: processing.compression_ratio ? `${processing.compression_ratio}%` : 'unknown',
      processing_time_seconds: processing.processing_time_seconds || 0
    },
    created_at: new Date().toISOString()
  };

  // Add to database
  await db.createDataset(dataset);

  // Update spatial coverage if we have bbox
  if (validation.bbox) {
    const [minLon, minLat, maxLon, maxLat] = validation.bbox;

    const spatialCoverage = {
      dataset_id: dataset_id,
      geometry: {
        type: 'Polygon' as const,
        coordinates: [[
          [minLon, minLat],
          [maxLon, minLat],
          [maxLon, maxLat],
          [minLon, maxLat],
          [minLon, minLat]
        ]]
      },
      priority: priority,
      resolution_meters: validation.resolution || 30
    };

    await db.updateSpatialCoverage(assignedTenantId, spatialCoverage);
  }

  // Store class mapping if available
  if (classification.mapping && classification.mapping.mappings) {
    const mappingKey = `${classification.detected_system}_to_FBFM40_${dataset_id}`;

    const classMapping = {
      source_system: classification.detected_system,
      target_system: 'FBFM40',
      mappings: classification.mapping.mappings,
      unmapped_classes: classification.mapping.unmapped_classes || [],
      auto_mapped_count: classification.mapping.auto_mapped_count || 0,
      manual_review_count: classification.mapping.manual_review_count || 0,
      created_at: new Date().toISOString()
    };

    await db.createClassMapping(mappingKey, classMapping);
  }
}

// Health check for FastAPI service
export async function GET() {
  try {
    const response = await fetch(`${FASTAPI_BASE_URL}/health`);
    const healthData = await response.json();

    return NextResponse.json({
      success: true,
      fastapi_service: healthData,
      proxy_status: 'operational'
    });

  } catch (error) {
    return NextResponse.json({
      success: false,
      fastapi_service: { status: 'unreachable' },
      proxy_status: 'error',
      error: 'FastAPI service is not available'
    }, { status: 503 });
  }
}