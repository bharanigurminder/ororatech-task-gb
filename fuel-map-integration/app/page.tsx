'use client';

import React, { useState } from 'react';
import FileUploadZone from '@/components/FileUploadZone';
import ProcessingResults from '@/components/ProcessingResults';
import CoverageMap from '@/components/CoverageMap';
import DatasetDashboard from '@/components/DatasetDashboard';
import ClassMappingReview from '@/components/ClassMappingReview';

export default function Home() {
  const [activeTab, setActiveTab] = useState<'upload' | 'datasets' | 'coverage' | 'query'>('upload');
  const [processingResult, setProcessingResult] = useState<any>(null);
  const [selectedDataset, setSelectedDataset] = useState<any>(null);
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const tenantId = 'tenant_001'; // In a real app, this would come from auth

  const handleUploadSuccess = (result: any) => {
    setProcessingResult(result);
    setNotification({
      type: 'success',
      message: `Dataset ${result.dataset_id} processed successfully!`
    });

    // Clear notification after 5 seconds
    setTimeout(() => setNotification(null), 5000);
  };

  const handleUploadError = (error: string) => {
    setNotification({
      type: 'error',
      message: error
    });

    // Clear notification after 5 seconds
    setTimeout(() => setNotification(null), 5000);
  };

  const handleDatasetSelect = (dataset: any) => {
    setSelectedDataset(dataset);
    setActiveTab('coverage'); // Switch to coverage view when dataset is selected
  };

  const clearResults = () => {
    setProcessingResult(null);
    setSelectedDataset(null);
  };

  return (
    <div className="space-y-8">
      {/* Notification */}
      {notification && (
        <div className={`fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 ${
          notification.type === 'success'
            ? 'bg-green-100 border border-green-200 text-green-800'
            : 'bg-red-100 border border-red-200 text-red-800'
        }`}>
          <div className="flex items-center">
            {notification.type === 'success' ? (
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            )}
            {notification.message}
          </div>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: 'upload', label: 'Upload', icon: '⬆️' },
            { id: 'datasets', label: 'Datasets', icon: '📊' },
            { id: 'coverage', label: 'Coverage', icon: '🗺️' },
            { id: 'query', label: 'Query', icon: '🔍' }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="space-y-8">
        {activeTab === 'upload' && (
          <div className="space-y-8">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 mb-2">Upload Fuel Map</h1>
              <p className="text-gray-600">
                Upload GeoTIFF fuel map files for processing with GDAL and automatic classification.
              </p>
            </div>

            <FileUploadZone
              tenantId={tenantId}
              onUploadSuccess={handleUploadSuccess}
              onUploadError={handleUploadError}
            />

            {processingResult && (
              <ProcessingResults
                result={processingResult}
                onClose={clearResults}
              />
            )}

            {processingResult?.classification?.mapping && (
              <div>
                <h2 className="text-xl font-semibold text-gray-900 mb-4">Class Mapping Review</h2>
                <ClassMappingReview
                  mappingData={processingResult.classification.mapping}
                  readonly={true}
                />
              </div>
            )}
          </div>
        )}

        {activeTab === 'datasets' && (
          <div>
            <div className="mb-8">
              <h1 className="text-2xl font-bold text-gray-900 mb-2">Dataset Management</h1>
              <p className="text-gray-600">
                View and manage your fuel map datasets, including processing status and metadata.
              </p>
            </div>

            <DatasetDashboard
              tenantId={tenantId}
              onDatasetSelect={handleDatasetSelect}
            />
          </div>
        )}

        {activeTab === 'coverage' && (
          <div className="space-y-8">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 mb-2">Coverage Visualization</h1>
              <p className="text-gray-600">
                Interactive map showing spatial coverage of your datasets with priority overlays.
              </p>
            </div>

            <CoverageMap tenantId={tenantId} height="500px" />

            {selectedDataset && (
              <div>
                <h2 className="text-xl font-semibold text-gray-900 mb-4">
                  Selected Dataset: {selectedDataset.name}
                </h2>
                <div className="fuel-card">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <span className="text-gray-600">Classification:</span>
                      <div className="font-medium">{selectedDataset.classification_system}</div>
                    </div>
                    <div>
                      <span className="text-gray-600">Resolution:</span>
                      <div className="font-medium">{selectedDataset.resolution_meters}m</div>
                    </div>
                    <div>
                      <span className="text-gray-600">Priority:</span>
                      <div className="font-medium">{selectedDataset.priority}</div>
                    </div>
                    <div>
                      <span className="text-gray-600">Status:</span>
                      <div className="font-medium">{selectedDataset.status}</div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'query' && (
          <div className="space-y-8">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 mb-2">Spatial Query Interface</h1>
              <p className="text-gray-600">
                Query fuel data at specific coordinates using the integrated Phase 1 + Phase 2 system.
              </p>
            </div>

            <FuelQueryInterface tenantId={tenantId} />
          </div>
        )}
      </div>
    </div>
  );
}

// Simple query interface component
function FuelQueryInterface({ tenantId }: { tenantId: string }) {
  const [lat, setLat] = useState('39.5');
  const [lon, setLon] = useState('-122.5');
  const [result, setResult] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleQuery = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`/api/fuel-query?lat=${lat}&lon=${lon}&tenant_id=${tenantId}`);
      const data = await response.json();
      setResult(data);
    } catch (error) {
      setResult({ success: false, error: 'Query failed' });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="fuel-card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Point Query</h3>

        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Latitude</label>
            <input
              type="number"
              value={lat}
              onChange={(e) => setLat(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              step="0.0001"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Longitude</label>
            <input
              type="number"
              value={lon}
              onChange={(e) => setLon(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              step="0.0001"
            />
          </div>
        </div>

        <button
          onClick={handleQuery}
          disabled={isLoading}
          className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Querying...' : 'Query Fuel Data'}
        </button>
      </div>

      {result && (
        <div className="fuel-card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Query Result</h3>

          {result.success ? (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="text-gray-600">Fuel Class:</span>
                  <div className="text-xl font-bold text-blue-600">{result.data.fuel_class}</div>
                </div>
                <div>
                  <span className="text-gray-600">Resolution:</span>
                  <div className="font-medium">{result.data.resolution_meters}m</div>
                </div>
                <div>
                  <span className="text-gray-600">Source Dataset:</span>
                  <div className="font-medium">{result.data.source_dataset}</div>
                </div>
                <div>
                  <span className="text-gray-600">Data Source:</span>
                  <div className="font-medium">{result.data.data_source}</div>
                </div>
              </div>

              <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                <div className="text-green-800 text-sm">
                  ✅ Successfully retrieved fuel data from {result.data.priority > 0 ? 'customer' : 'global'} dataset
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <div className="text-red-800 text-sm">
                ❌ {result.error || 'Query failed'}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}