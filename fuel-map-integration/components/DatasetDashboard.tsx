'use client';

import React, { useEffect, useState } from 'react';

interface Dataset {
  id: string;
  name: string;
  type: string;
  classification_system: string;
  resolution_meters: number;
  status: string;
  priority: number;
  pixel_count: number;
  created_at: string;
  processing?: {
    validation_status: string;
    cog_created: boolean;
    size_reduction: string;
    processing_time_seconds: number;
  };
}

interface TenantStats {
  total_datasets: number;
  private_datasets: number;
  total_storage_mb: number;
  total_pixels: number;
  coverage_area_km2: number;
  last_upload: string | null;
}

interface DatasetDashboardProps {
  tenantId: string;
  onDatasetSelect?: (dataset: Dataset) => void;
}

export default function DatasetDashboard({ tenantId, onDatasetSelect }: DatasetDashboardProps) {
  const [datasets, setDatasets] = useState<{ owned: Dataset[]; shared: Dataset[]; global: Dataset[] } | null>(null);
  const [stats, setStats] = useState<TenantStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'owned' | 'global'>('owned');
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  useEffect(() => {
    loadData();
  }, [tenantId]);

  const getStatusBadge = (status: string) => {
    const badges = {
      processed: 'bg-green-100 text-green-800',
      processing: 'bg-yellow-100 text-yellow-800',
      active: 'bg-blue-100 text-blue-800',
      failed: 'bg-red-100 text-red-800',
    };
    return badges[status as keyof typeof badges] || 'bg-gray-100 text-gray-800';
  };

  const getTypeBadge = (type: string) => {
    const badges = {
      customer_private: 'bg-purple-100 text-purple-800',
      global_baseline: 'bg-blue-100 text-blue-800',
    };
    return badges[type as keyof typeof badges] || 'bg-gray-100 text-gray-800';
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const handleDeleteAllDatasets = async () => {
    if (!tenantId) return;

    try {
      setIsDeleting(true);

      const response = await fetch(`/api/datasets/delete-all?tenant_id=${tenantId}`, {
        method: 'DELETE',
      });

      const result = await response.json();

      if (response.ok && result.success) {
        // Refresh data after successful deletion
        await loadData();
        setShowDeleteConfirm(false);
      } else {
        throw new Error(result.error || 'Failed to delete datasets');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete datasets');
    } finally {
      setIsDeleting(false);
    }
  };

  const loadData = async () => {
    try {
      setIsLoading(true);

      // Load datasets and stats in parallel
      const [datasetsResponse, statsResponse] = await Promise.all([
        fetch(`/api/datasets?tenant_id=${tenantId}`),
        fetch(`/api/tenants/${tenantId}/stats`)
      ]);

      if (datasetsResponse.ok) {
        const datasetsData = await datasetsResponse.json();
        setDatasets(datasetsData.datasets);
      } else {
        throw new Error('Failed to load datasets');
      }

      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        setStats(statsData.statistics);
      } else {
        throw new Error('Failed to load tenant statistics');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="grid grid-cols-4 gap-4 mb-6">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-20 bg-gray-200 rounded"></div>
            ))}
          </div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <div className="flex items-center">
          <svg className="w-5 h-5 text-red-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-red-800 font-medium">Error loading dashboard: {error}</span>
        </div>
      </div>
    );
  }

  const currentDatasets = datasets?.[activeTab] || [];

  return (
    <div className="space-y-6">
      {/* Tenant Statistics */}
      {stats && (
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Tenant Overview</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="fuel-card">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{stats.total_datasets}</div>
                <div className="text-sm text-gray-600">Total Datasets</div>
              </div>
            </div>
            <div className="fuel-card">
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">{stats.private_datasets}</div>
                <div className="text-sm text-gray-600">Private Datasets</div>
              </div>
            </div>
            <div className="fuel-card">
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{stats.total_storage_mb.toFixed(1)}</div>
                <div className="text-sm text-gray-600">Storage (MB)</div>
              </div>
            </div>
            <div className="fuel-card">
              <div className="text-center">
                <div className="text-2xl font-bold text-orange-600">{(stats.coverage_area_km2 / 1000).toFixed(1)}K</div>
                <div className="text-sm text-gray-600">Coverage (km²)</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Dataset Tabs */}
      <div>
        <div className="border-b border-gray-200">
          <div className="flex justify-between items-center">
            <nav className="-mb-px flex space-x-8">
              {['owned', 'global'].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab as any)}
                  className={`py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === tab
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  {tab === 'owned' ? 'Owned/Regional' : 'Global'} Datasets
                  {datasets && (
                    <span className="ml-2 bg-gray-100 text-gray-900 py-0.5 px-2 rounded-full text-xs">
                      {datasets[tab as keyof typeof datasets].length}
                    </span>
                  )}
                </button>
              ))}
            </nav>

            {/* Delete All Datasets Button */}
            {datasets && (datasets.owned.length > 0 || datasets.global.length > 0) && (
              <button
                onClick={() => setShowDeleteConfirm(true)}
                disabled={isDeleting}
                className="inline-flex items-center px-3 py-2 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isDeleting ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-red-600 mr-2"></div>
                    Deleting...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                    Delete All Datasets
                  </>
                )}
              </button>
            )}
          </div>
        </div>

        {/* Dataset List */}
        <div className="mt-6">
          {currentDatasets.length === 0 ? (
            <div className="text-center py-12 bg-gray-50 rounded-lg">
              <svg className="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2M4 13h2m13-8l-4 4m0 0l-4-4m4 4V3" />
              </svg>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                No {activeTab === 'owned' ? 'owned/regional' : 'global'} datasets
              </h3>
              <p className="text-gray-500">
                {activeTab === 'owned'
                  ? 'Upload your first regional fuel map dataset to get started'
                  : 'No global baseline datasets available'}
              </p>
            </div>
          ) : (
            <div className="grid gap-4">
              {currentDatasets.map((dataset) => (
                <div
                  key={dataset.id}
                  className="fuel-card cursor-pointer hover:shadow-lg transition-shadow"
                  onClick={() => onDatasetSelect?.(dataset)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        <h3 className="font-medium text-gray-900">{dataset.name}</h3>
                        <span className={`fuel-badge ${getTypeBadge(dataset.type)}`}>
                          {dataset.type.replace('_', ' ')}
                        </span>
                        <span className={`fuel-badge ${getStatusBadge(dataset.status)}`}>
                          {dataset.status}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-600 mb-3">
                        <div>
                          <span className="font-medium">Classification:</span>
                          <div>{dataset.classification_system}</div>
                        </div>
                        <div>
                          <span className="font-medium">Resolution:</span>
                          <div>{dataset.resolution_meters}m</div>
                        </div>
                        <div>
                          <span className="font-medium">Priority:</span>
                          <div>{dataset.priority}</div>
                        </div>
                        <div>
                          <span className="font-medium">Pixels:</span>
                          <div>{dataset.pixel_count.toLocaleString()}</div>
                        </div>
                      </div>

                      {dataset.processing && (
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-600 mb-3">
                          <div>
                            <span className="font-medium">Validation:</span>
                            <div className={dataset.processing.validation_status.includes('warning') ? 'text-amber-600' : 'text-green-600'}>
                              {dataset.processing.validation_status.replace('_', ' ')}
                            </div>
                          </div>
                          <div>
                            <span className="font-medium">COG:</span>
                            <div className={dataset.processing.cog_created ? 'text-green-600' : 'text-red-600'}>
                              {dataset.processing.cog_created ? 'Created' : 'Failed'}
                            </div>
                          </div>
                          <div>
                            <span className="font-medium">Compression:</span>
                            <div>{dataset.processing.size_reduction}</div>
                          </div>
                          <div>
                            <span className="font-medium">Process Time:</span>
                            <div>{dataset.processing.processing_time_seconds}s</div>
                          </div>
                        </div>
                      )}

                      <div className="text-xs text-gray-500">
                        Created: {formatDate(dataset.created_at)}
                      </div>
                    </div>

                    <div className="ml-4">
                      <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3 text-center">
              <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100">
                <svg className="h-6 w-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-gray-900 mt-4">Delete All Datasets</h3>
              <div className="mt-2 px-7 py-3">
                <p className="text-sm text-gray-500">
                  Are you sure you want to delete all datasets? This action cannot be undone and will permanently remove all uploaded files and their processing results.
                </p>
                <div className="mt-4 text-xs text-gray-400">
                  Total datasets to be deleted: {datasets ? datasets.owned.length + datasets.shared.length + datasets.global.length : 0}
                </div>
              </div>
              <div className="items-center px-4 py-3">
                <div className="flex space-x-3">
                  <button
                    onClick={() => setShowDeleteConfirm(false)}
                    disabled={isDeleting}
                    className="px-4 py-2 bg-gray-500 text-white text-base font-medium rounded-md w-full shadow-sm hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-300 disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleDeleteAllDatasets}
                    disabled={isDeleting}
                    className="px-4 py-2 bg-red-600 text-white text-base font-medium rounded-md w-full shadow-sm hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-300 disabled:opacity-50"
                  >
                    {isDeleting ? 'Deleting...' : 'Delete All'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}