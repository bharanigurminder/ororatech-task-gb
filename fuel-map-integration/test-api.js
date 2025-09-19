#!/usr/bin/env node

const API_BASE = 'http://localhost:3002/api';

async function testAPI() {
  console.log('🧪 Testing Fuel Map Integration API\n');

  // Test 1: Get tenant stats
  console.log('1️⃣  Testing Tenant Stats...');
  try {
    const res = await fetch(`${API_BASE}/tenants/tenant_001/stats`);
    const data = await res.json();
    console.log('✅ Tenant Stats:', JSON.stringify(data, null, 2));
  } catch (error) {
    console.log('❌ Failed:', error.message);
  }

  // Test 2: List datasets for tenant
  console.log('\n2️⃣  Testing Dataset List...');
  try {
    const res = await fetch(`${API_BASE}/datasets?tenant_id=tenant_001`);
    const data = await res.json();
    console.log('✅ Datasets:', JSON.stringify(data, null, 2));
  } catch (error) {
    console.log('❌ Failed:', error.message);
  }

  // Test 3: Query fuel data at specific point
  console.log('\n3️⃣  Testing Point Query (Northern California)...');
  try {
    const res = await fetch(
      `${API_BASE}/fuel-query?lat=39.5&lon=-122.5&tenant_id=tenant_001`
    );
    const data = await res.json();
    console.log('✅ Fuel Query Result:', JSON.stringify(data, null, 2));
  } catch (error) {
    console.log('❌ Failed:', error.message);
  }

  // Test 4: Query fuel data outside customer coverage
  console.log('\n4️⃣  Testing Point Query (Nevada - Global Fallback)...');
  try {
    const res = await fetch(
      `${API_BASE}/fuel-query?lat=39.0&lon=-119.0&tenant_id=tenant_001`
    );
    const data = await res.json();
    console.log('✅ Fuel Query Result:', JSON.stringify(data, null, 2));
  } catch (error) {
    console.log('❌ Failed:', error.message);
  }

  // Test 5: Get coverage GeoJSON
  console.log('\n5️⃣  Testing Coverage Map...');
  try {
    const res = await fetch(`${API_BASE}/coverage/tenant_001`);
    const data = await res.json();
    console.log('✅ Coverage GeoJSON:', {
      type: data.type,
      feature_count: data.features.length,
      first_feature: data.features[0]
    });
  } catch (error) {
    console.log('❌ Failed:', error.message);
  }

  // Test 6: Query bbox
  console.log('\n6️⃣  Testing BBox Query...');
  try {
    const res = await fetch(`${API_BASE}/fuel-query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        bbox: [-123, 39, -122, 40],
        tenant_id: 'tenant_001',
        grid_resolution: 3
      })
    });
    const data = await res.json();
    console.log('✅ BBox Query Result:', {
      success: data.success,
      point_count: data.point_count,
      primary_source: data.data_source?.primary_source?.dataset_id
    });
  } catch (error) {
    console.log('❌ Failed:', error.message);
  }

  // Test 7: Find coverage gaps
  console.log('\n7️⃣  Testing Coverage Gap Analysis...');
  try {
    const res = await fetch(`${API_BASE}/coverage/tenant_001`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        bbox: [-125, 37, -120, 42]
      })
    });
    const data = await res.json();
    console.log('✅ Gap Analysis:', data.statistics);
  } catch (error) {
    console.log('❌ Failed:', error.message);
  }

  // Test 8: Get specific dataset
  console.log('\n8️⃣  Testing Dataset Details...');
  try {
    const res = await fetch(
      `${API_BASE}/datasets/dataset_001?tenant_id=tenant_001`
    );
    const data = await res.json();
    console.log('✅ Dataset Details:', {
      id: data.dataset?.id,
      name: data.dataset?.name,
      access_type: data.access_type
    });
  } catch (error) {
    console.log('❌ Failed:', error.message);
  }

  // Test 9: Test access control
  console.log('\n9️⃣  Testing Access Control...');
  try {
    const res = await fetch(
      `${API_BASE}/datasets/dataset_001?tenant_id=tenant_002`
    );
    const data = await res.json();
    console.log('✅ Access Control:', {
      status: res.status,
      error: data.error
    });
  } catch (error) {
    console.log('❌ Failed:', error.message);
  }

  console.log('\n✨ API Tests Complete!');
}

testAPI().catch(console.error);