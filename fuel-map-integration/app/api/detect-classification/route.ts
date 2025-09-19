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

    // Forward to FastAPI classification detection endpoint
    const fastApiFormData = new FormData();
    fastApiFormData.append('file', file);

    const response = await fetch(`${FASTAPI_BASE_URL}/detect-classification`, {
      method: 'POST',
      body: fastApiFormData,
    });

    const result = await response.json();

    return NextResponse.json(result);

  } catch (error) {
    console.error('Error detecting classification:', error);

    if (error instanceof TypeError && error.message.includes('fetch')) {
      return NextResponse.json(
        {
          success: false,
          error: 'Classification detection service is not available'
        },
        { status: 503 }
      );
    }

    return NextResponse.json(
      { success: false, error: 'Failed to detect classification system' },
      { status: 500 }
    );
  }
}

export async function GET() {
  try {
    // Get available classification systems
    const response = await fetch(`${FASTAPI_BASE_URL}/classification-systems`);
    const result = await response.json();

    return NextResponse.json(result);

  } catch (error) {
    console.error('Error getting classification systems:', error);

    return NextResponse.json(
      {
        success: false,
        error: 'Failed to get classification systems'
      },
      { status: 500 }
    );
  }
}