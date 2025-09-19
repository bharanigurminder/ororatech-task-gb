import { NextRequest, NextResponse } from 'next/server';

const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8001';

export async function GET(
  request: NextRequest,
  { params }: { params: { tenantId: string } }
) {
  try {
    const tenantId = params.tenantId;

    // Call FastAPI backend for tenant stats
    const response = await fetch(`${FASTAPI_URL}/tenants/${tenantId}/stats`);

    if (!response.ok) {
      throw new Error(`FastAPI error: ${response.status}`);
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || 'Unknown error from FastAPI');
    }

    return NextResponse.json({
      success: true,
      statistics: data.statistics
    });

  } catch (error) {
    console.error('Error fetching tenant stats:', error);
    return NextResponse.json(
      { error: 'Failed to fetch tenant statistics' },
      { status: 500 }
    );
  }
}