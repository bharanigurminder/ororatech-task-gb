import { NextRequest, NextResponse } from 'next/server';
import { LocalJSONDatabase } from '@/lib/database';
import { TenantService } from '@/lib/tenant-service';

const db = new LocalJSONDatabase();
const tenantService = new TenantService(db);

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const tenantId = searchParams.get('tenant_id');

    if (!tenantId) {
      return NextResponse.json(
        { error: 'tenant_id is required' },
        { status: 400 }
      );
    }

    const access = await tenantService.checkDatasetAccess(tenantId, params.id);

    if (!access.has_access) {
      return NextResponse.json(
        { error: access.reason || 'Access denied' },
        { status: 403 }
      );
    }

    const dataset = await db.getDataset(params.id);

    if (!dataset) {
      return NextResponse.json(
        { error: 'Dataset not found' },
        { status: 404 }
      );
    }

    return NextResponse.json({
      success: true,
      dataset,
      access_type: access.access_type
    });

  } catch (error) {
    console.error('Error fetching dataset:', error);
    return NextResponse.json(
      { error: 'Failed to fetch dataset' },
      { status: 500 }
    );
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const body = await request.json();
    const { tenant_id, updates } = body;

    if (!tenant_id) {
      return NextResponse.json(
        { error: 'tenant_id is required' },
        { status: 400 }
      );
    }

    const dataset = await db.getDataset(params.id);

    if (!dataset) {
      return NextResponse.json(
        { error: 'Dataset not found' },
        { status: 404 }
      );
    }

    if (dataset.tenant_id !== tenant_id && dataset.tenant_id !== 'system') {
      return NextResponse.json(
        { error: 'Only dataset owner can update' },
        { status: 403 }
      );
    }

    await db.updateDataset(params.id, updates);

    return NextResponse.json({
      success: true,
      message: 'Dataset updated successfully'
    });

  } catch (error) {
    console.error('Error updating dataset:', error);
    return NextResponse.json(
      { error: 'Failed to update dataset' },
      { status: 500 }
    );
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const tenantId = searchParams.get('tenant_id');

    if (!tenantId) {
      return NextResponse.json(
        { error: 'tenant_id is required' },
        { status: 400 }
      );
    }

    const dataset = await db.getDataset(params.id);

    if (!dataset) {
      return NextResponse.json(
        { error: 'Dataset not found' },
        { status: 404 }
      );
    }

    if (dataset.tenant_id !== tenantId) {
      return NextResponse.json(
        { error: 'Only dataset owner can delete' },
        { status: 403 }
      );
    }

    await db.deleteDataset(params.id);

    return NextResponse.json({
      success: true,
      message: 'Dataset deleted successfully'
    });

  } catch (error) {
    console.error('Error deleting dataset:', error);
    return NextResponse.json(
      { error: 'Failed to delete dataset' },
      { status: 500 }
    );
  }
}