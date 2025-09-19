'use client';

import React, { useEffect, useRef, useState, useMemo } from 'react';
import dynamic from 'next/dynamic';

// Import Leaflet components dynamically with SSR disabled
const MapContainer = dynamic(
  () => import('react-leaflet').then(mod => mod.MapContainer),
  { ssr: false }
);

const TileLayer = dynamic(
  () => import('react-leaflet').then(mod => mod.TileLayer),
  { ssr: false }
);

const GeoJSON = dynamic(
  () => import('react-leaflet').then(mod => mod.GeoJSON),
  { ssr: false }
);

const Popup = dynamic(
  () => import('react-leaflet').then(mod => mod.Popup),
  { ssr: false }
);

interface CoverageMapProps {
  tenantId: string;
  height?: string;
}

export default function CoverageMap({ tenantId, height = '400px' }: CoverageMapProps) {
  const [coverageData, setCoverageData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDataset, setSelectedDataset] = useState<string | null>(null);
  const [isClient, setIsClient] = useState(false);
  const [mapKey, setMapKey] = useState(0);

  // Ensure we're on the client side
  useEffect(() => {
    setIsClient(true);
  }, []);

  // Reset map when tenantId changes to prevent initialization conflicts
  useEffect(() => {
    setMapKey(prev => prev + 1);
    setCoverageData(null);
    setError(null);
  }, [tenantId]);

  useEffect(() => {
    if (!isClient) return;

    const loadCoverageData = async () => {
      try {
        setIsLoading(true);
        console.log('Loading coverage data for tenant:', tenantId);
        const response = await fetch(`/api/coverage/${tenantId}`);
        const data = await response.json();

        console.log('Coverage API response:', data);

        if (response.ok) {
          setCoverageData(data);
          console.log('Coverage data loaded successfully:', data);
        } else {
          setError('Failed to load coverage data');
        }
      } catch (err) {
        console.error('Error loading coverage:', err);
        setError(`Error loading coverage: ${err instanceof Error ? err.message : 'Unknown error'}`);
      } finally {
        setIsLoading(false);
      }
    };

    loadCoverageData();
  }, [tenantId, isClient]);

  const getFeatureColor = (feature: any) => {
    const type = feature.properties?.type;
    const priority = feature.properties?.priority || 0;

    if (type === 'customer') {
      return priority > 0 ? '#ef4444' : '#fb923c'; // Red for high priority, orange for normal
    } else {
      return '#3b82f6'; // Blue for global
    }
  };

  const getFeatureStyle = (feature: any) => {
    return {
      color: getFeatureColor(feature),
      weight: 2,
      fillOpacity: 0.3,
      fillColor: getFeatureColor(feature),
    };
  };

  const onFeatureClick = (feature: any, layer: any) => {
    setSelectedDataset(feature.properties.dataset_id);

    const popup = `
      <div class="fuel-popup">
        <h3>${feature.properties.dataset_name}</h3>
        <p><strong>Dataset:</strong> ${feature.properties.dataset_id}</p>
        <p><strong>Type:</strong> ${feature.properties.type}</p>
        <p><strong>Resolution:</strong> ${feature.properties.resolution}m</p>
        <p><strong>Priority:</strong> ${feature.properties.priority}</p>
        <p><strong>Classification:</strong> ${feature.properties.classification_system}</p>
        <p><strong>Status:</strong> ${feature.properties.status}</p>
      </div>
    `;

    layer.bindPopup(popup).openPopup();
  };

  if (!isClient) {
    return (
      <div style={{ height }} className="bg-gray-100 rounded-lg flex items-center justify-center">
        <div className="text-gray-500">Loading map...</div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div style={{ height }} className="bg-gray-100 rounded-lg flex items-center justify-center">
        <div className="flex items-center space-x-2">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
          <span className="text-gray-600">Loading coverage data...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ height }} className="bg-red-50 rounded-lg flex items-center justify-center">
        <div className="text-center">
          <svg className="w-8 h-8 text-red-400 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-red-600 text-sm">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Legend */}
      <div className="flex items-center space-x-6 text-sm">
        <div className="flex items-center space-x-2">
          <div className="w-4 h-4 bg-red-400 rounded"></div>
          <span>Customer Data (High Priority)</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-4 h-4 bg-orange-400 rounded"></div>
          <span>Customer Data</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-4 h-4 bg-blue-400 rounded"></div>
          <span>Global Baseline</span>
        </div>
      </div>

      {/* Map */}
      <div style={{ height }} className="rounded-lg overflow-hidden border">
        <React.Suspense fallback={
          <div style={{ height }} className="bg-gray-100 flex items-center justify-center">
            <span className="text-gray-500">Loading map components...</span>
          </div>
        }>
          <MapContainer
            key={mapKey}
            center={[39.0, -121.0]} // Center on California
            zoom={6}
            style={{ height: '100%', width: '100%' }}
            className="leaflet-container"
          >
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            />

            {coverageData && coverageData.features && coverageData.features.length > 0 && (
              <GeoJSON
                key={`geojson-${mapKey}`}
                data={coverageData}
                style={getFeatureStyle}
                onEachFeature={(feature, layer) => {
                  console.log('Processing feature:', feature);
                  layer.on('click', () => onFeatureClick(feature, layer));
                }}
              />
            )}
          </MapContainer>
        </React.Suspense>
      </div>

      {/* Coverage Statistics */}
      {coverageData && coverageData.features && (
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 mb-2">Coverage Summary</h4>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div className="text-center">
              <div className="text-lg font-semibold text-gray-900">
                {coverageData.features.length}
              </div>
              <div className="text-gray-600">Total Areas</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-semibold text-red-600">
                {coverageData.features.filter((f: any) => f.properties.type === 'customer').length}
              </div>
              <div className="text-gray-600">Customer</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-semibold text-blue-600">
                {coverageData.features.filter((f: any) => f.properties.type === 'global').length}
              </div>
              <div className="text-gray-600">Global</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}