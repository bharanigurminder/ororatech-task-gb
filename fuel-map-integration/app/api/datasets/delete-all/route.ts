import { NextRequest, NextResponse } from 'next/server';

const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8001';

export async function DELETE(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const tenantId = searchParams.get('tenant_id') || 'tenant_001';

    // Call FastAPI backend to delete all datasets
    const response = await fetch(`${FASTAPI_URL}/datasets/delete-all?tenant_id=${tenantId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error(`FastAPI error: ${response.status}`);
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || 'Unknown error from FastAPI');
    }

    return NextResponse.json({
      success: true,
      message: data.message,
      deleted_count: data.deleted_count,
      deleted_size_mb: data.deleted_size_mb
    });

  } catch (error) {
    console.error('Error deleting all datasets:', error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to delete datasets'
      },
      { status: 500 }
    );
  }
}