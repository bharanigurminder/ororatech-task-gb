import { NextRequest, NextResponse } from 'next/server';

const FASTAPI_BASE_URL = process.env.FASTAPI_URL || 'http://localhost:8001';

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const file = formData.get('file') as File;

    if (!file) {
      return NextResponse.json(
        { error: 'File is required' },
        { status: 400 }
      );
    }

    // Validate file type
    if (!file.name.toLowerCase().endsWith('.tif') && !file.name.toLowerCase().endsWith('.tiff')) {
      return NextResponse.json(
        { error: 'Only GeoTIFF files (.tif, .tiff) are supported' },
        { status: 400 }
      );
    }

    // Forward to FastAPI validation endpoint
    const fastApiFormData = new FormData();
    fastApiFormData.append('file', file);

    const response = await fetch(`${FASTAPI_BASE_URL}/validate-file`, {
      method: 'POST',
      body: fastApiFormData,
    });

    const result = await response.json();

    return NextResponse.json(result);

  } catch (error) {
    console.error('Error validating GeoTIFF:', error);

    if (error instanceof TypeError && error.message.includes('fetch')) {
      return NextResponse.json(
        {
          success: false,
          error: 'Geospatial validation service is not available'
        },
        { status: 503 }
      );
    }

    return NextResponse.json(
      { success: false, error: 'Failed to validate file' },
      { status: 500 }
    );
  }
}