import { NextRequest, NextResponse } from 'next/server';
import { LocalJSONDatabase } from '@/lib/database';
import { TenantService } from '@/lib/tenant-service';

const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8001';
const db = new LocalJSONDatabase();
const tenantService = new TenantService(db);

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const tenantId = searchParams.get('tenant_id') || 'tenant_001';

    // Call FastAPI backend
    const response = await fetch(`${FASTAPI_URL}/datasets?tenant_id=${tenantId}`);

    if (!response.ok) {
      throw new Error(`FastAPI error: ${response.status}`);
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || 'Unknown error from FastAPI');
    }

    // Transform FastAPI response to match frontend expectations
    const ownedDatasets: any[] = [];
    const globalDatasets: any[] = [];

    // Handle the new format where datasets are already categorized
    if (data.datasets.owned) {
      data.datasets.owned.forEach((dataset: any) => {
        const datasetObj = {
          id: dataset.dataset_id,
          name: dataset.name || dataset.dataset_id,
          type: 'customer_private',
          classification_system: dataset.classification_system || 'auto-detected',
          resolution_meters: 30,
          status: dataset.status,
          priority: 1,
          pixel_count: Math.floor(dataset.file_size_mb * 1024 * 256), // rough estimate
          created_at: new Date(dataset.created_at * 1000).toISOString(),
          processing: {
            validation_status: 'valid',
            cog_created: true,
            size_reduction: `${dataset.file_size_mb}MB`,
            processing_time_seconds: 0
          }
        };
        ownedDatasets.push(datasetObj);
      });
    }

    if (data.datasets.global) {
      data.datasets.global.forEach((dataset: any) => {
        const datasetObj = {
          id: dataset.dataset_id,
          name: dataset.name || dataset.dataset_id,
          type: 'global_baseline',
          classification_system: dataset.classification_system || 'auto-detected',
          resolution_meters: 30,
          status: dataset.status,
          priority: 0,
          pixel_count: Math.floor(dataset.file_size_mb * 1024 * 256), // rough estimate
          created_at: new Date(dataset.created_at * 1000).toISOString(),
          processing: {
            validation_status: 'valid',
            cog_created: true,
            size_reduction: `${dataset.file_size_mb}MB`,
            processing_time_seconds: 0
          }
        };
        globalDatasets.push(datasetObj);
      });
    }

    const datasets = {
      owned: ownedDatasets,
      shared: [],
      global: globalDatasets
    };

    return NextResponse.json({
      success: true,
      tenant_id: tenantId,
      datasets
    });

  } catch (error) {
    console.error('Error fetching datasets:', error);
    return NextResponse.json(
      { error: 'Failed to fetch datasets' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { tenant_id, dataset } = body;

    if (!tenant_id || !dataset) {
      return NextResponse.json(
        { error: 'tenant_id and dataset are required' },
        { status: 400 }
      );
    }

    const isValid = await tenantService.validateTenant(tenant_id);
    if (!isValid) {
      return NextResponse.json(
        { error: 'Invalid tenant ID' },
        { status: 403 }
      );
    }

    const estimatedSizeMb = (dataset.pixel_count * 4) / (1024 * 1024);
    const canUpload = await tenantService.canUploadDataset(tenant_id, estimatedSizeMb);

    if (!canUpload.can_upload) {
      return NextResponse.json(
        { error: canUpload.reason },
        { status: 400 }
      );
    }

    dataset.tenant_id = tenant_id;
    dataset.created_at = new Date().toISOString();
    dataset.status = dataset.status || 'processing';

    await db.createDataset(dataset);

    return NextResponse.json({
      success: true,
      dataset_id: dataset.id,
      message: 'Dataset created successfully'
    });

  } catch (error) {
    console.error('Error creating dataset:', error);
    return NextResponse.json(
      { error: 'Failed to create dataset' },
      { status: 500 }
    );
  }
}