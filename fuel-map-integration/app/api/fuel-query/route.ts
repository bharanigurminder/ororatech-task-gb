import { NextRequest, NextResponse } from 'next/server';
import { LocalJSONDatabase } from '@/lib/database';
import { SpatialQueryService } from '@/lib/spatial-query';
import { TenantService } from '@/lib/tenant-service';

const db = new LocalJSONDatabase();
const spatialQuery = new SpatialQueryService(db);
const tenantService = new TenantService(db);

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const lat = parseFloat(searchParams.get('lat') || '0');
    const lon = parseFloat(searchParams.get('lon') || '0');
    const tenantId = searchParams.get('tenant_id') || '';

    if (!tenantId) {
      return NextResponse.json(
        { error: 'tenant_id is required' },
        { status: 400 }
      );
    }

    if (isNaN(lat) || isNaN(lon)) {
      return NextResponse.json(
        { error: 'Invalid coordinates' },
        { status: 400 }
      );
    }

    const isValid = await tenantService.validateTenant(tenantId);
    if (!isValid) {
      return NextResponse.json(
        { error: 'Invalid tenant ID' },
        { status: 403 }
      );
    }

    try {
      const result = await db.queryFuelData(lat, lon, tenantId);

      return NextResponse.json({
        success: true,
        coordinates: { lat, lon },
        data: result,
        timestamp: new Date().toISOString()
      });

    } catch (queryError) {
      return NextResponse.json({
        success: false,
        coordinates: { lat, lon },
        error: 'No fuel data available for this location',
        fallback_to_global: true,
        timestamp: new Date().toISOString()
      });
    }

  } catch (error) {
    console.error('Error querying fuel data:', error);
    return NextResponse.json(
      { error: 'Failed to query fuel data' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { bbox, tenant_id, grid_resolution = 10 } = body;

    if (!tenant_id || !bbox) {
      return NextResponse.json(
        { error: 'tenant_id and bbox are required' },
        { status: 400 }
      );
    }

    if (!Array.isArray(bbox) || bbox.length !== 4) {
      return NextResponse.json(
        { error: 'bbox must be an array of [minLon, minLat, maxLon, maxLat]' },
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

    const dataSource = await spatialQuery.findBestDataSource(bbox, tenant_id);

    const results = await spatialQuery.queryBbox(bbox, tenant_id, grid_resolution);

    return NextResponse.json({
      success: true,
      bbox,
      grid_resolution,
      data_source: dataSource,
      results,
      point_count: results.length,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error querying bbox:', error);
    return NextResponse.json(
      { error: 'Failed to query bbox' },
      { status: 500 }
    );
  }
}