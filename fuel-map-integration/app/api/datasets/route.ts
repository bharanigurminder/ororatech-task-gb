import { NextRequest, NextResponse } from 'next/server';

const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8001';

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

    data.datasets.forEach((dataset: any) => {
      const datasetObj = {
        id: dataset.dataset_id,
        name: dataset.dataset_id,
        type: dataset.dataset_id.toLowerCase().includes('lc24') || dataset.dataset_id.toLowerCase().includes('global') ? 'global_baseline' : 'customer_private',
        classification_system: 'auto-detected',
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

      // Categorize based on type or filename patterns
      if (datasetObj.type === 'global_baseline' ||
          dataset.dataset_id.toLowerCase().includes('lc24') ||
          dataset.dataset_id.toLowerCase().includes('global')) {
        globalDatasets.push(datasetObj);
      } else {
        ownedDatasets.push(datasetObj);
      }
    });

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