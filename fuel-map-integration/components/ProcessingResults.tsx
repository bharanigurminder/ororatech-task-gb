'use client';

import React from 'react';

interface ProcessingResultsProps {
  result: any;
  onClose: () => void;
}

export default function ProcessingResults({ result, onClose }: ProcessingResultsProps) {
  if (!result) return null;

  const { dataset_id, validation, classification, processing, paths } = result;

  const getClassificationBadge = (system: string) => {
    const badges = {
      'FBFM40': 'fuel-badge-grass',
      'SENTINEL_FUEL_2024': 'fuel-badge-shrub',
      'LANDFIRE_US': 'fuel-badge-timber',
      'CANADIAN_FBP': 'fuel-badge-urban',
    };
    return badges[system as keyof typeof badges] || 'fuel-badge-urban';
  };

  const getStatusIcon = (success: boolean) => {
    if (success) {
      return (
        <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
          <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
      );
    } else {
      return (
        <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
          <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
      );
    }
  };

  return (
    <div className="fuel-card">
      <div className="flex items-start justify-between mb-6">
        <div className="flex items-center space-x-3">
          {getStatusIcon(result.success)}
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              {result.success ? 'Processing Complete' : 'Processing Failed'}
            </h3>
            <p className="text-sm text-gray-500">Dataset: {dataset_id}</p>
          </div>
        </div>

        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {result.success ? (
        <div className="space-y-6">
          {/* Validation Results */}
          {validation && (
            <div>
              <h4 className="font-medium text-gray-900 mb-3">File Validation</h4>
              <div className="bg-gray-50 rounded-lg p-4 space-y-2">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">Format:</span>
                    <span className="ml-2 font-medium">{validation.format}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Dimensions:</span>
                    <span className="ml-2 font-medium">{validation.width} × {validation.height}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Resolution:</span>
                    <span className="ml-2 font-medium">{validation.resolution?.toFixed(1)}m</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Pixel Count:</span>
                    <span className="ml-2 font-medium">{validation.pixel_count?.toLocaleString()}</span>
                  </div>
                </div>

                {validation.detected_classes && validation.detected_classes.length > 0 && (
                  <div className="mt-3">
                    <span className="text-gray-600 text-sm">Detected Classes:</span>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {validation.detected_classes.slice(0, 10).map((cls: number) => (
                        <span
                          key={cls}
                          className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800"
                        >
                          {cls}
                        </span>
                      ))}
                      {validation.detected_classes.length > 10 && (
                        <span className="text-xs text-gray-500">
                          +{validation.detected_classes.length - 10} more
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {validation.warnings && validation.warnings.length > 0 && (
                  <div className="mt-3">
                    <div className="text-xs text-amber-600">
                      <strong>Warnings:</strong>
                      <ul className="mt-1 list-disc list-inside space-y-1">
                        {validation.warnings.map((warning: string, idx: number) => (
                          <li key={idx}>{warning}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Classification Results */}
          {classification && (
            <div>
              <h4 className="font-medium text-gray-900 mb-3">Classification Analysis</h4>
              <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Detected System:</span>
                  <span className={`fuel-badge ${getClassificationBadge(classification.detected_system)}`}>
                    {classification.detected_system}
                  </span>
                </div>

                {classification.mapping && (
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-gray-600">Auto-mapped:</span>
                      <span className="ml-2 font-medium">{classification.mapping.auto_mapped_count || 0}</span>
                    </div>
                    <div>
                      <span className="text-gray-600">Manual review:</span>
                      <span className="ml-2 font-medium">{classification.mapping.manual_review_count || 0}</span>
                    </div>
                    <div className="col-span-2">
                      <span className="text-gray-600">Auto-mappable:</span>
                      <span className={`ml-2 font-medium ${classification.mapping.auto_mappable ? 'text-green-600' : 'text-amber-600'}`}>
                        {classification.mapping.auto_mappable ? 'Yes' : 'No'}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Processing Results */}
          {processing && (
            <div>
              <h4 className="font-medium text-gray-900 mb-3">COG Processing</h4>
              <div className="bg-gray-50 rounded-lg p-4 space-y-2">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">Status:</span>
                    <span className={`ml-2 font-medium ${processing.success ? 'text-green-600' : 'text-red-600'}`}>
                      {processing.success ? 'Success' : 'Failed'}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600">Processing Time:</span>
                    <span className="ml-2 font-medium">{processing.processing_time_seconds}s</span>
                  </div>
                  {processing.original_size_mb && (
                    <>
                      <div>
                        <span className="text-gray-600">Original Size:</span>
                        <span className="ml-2 font-medium">{processing.original_size_mb} MB</span>
                      </div>
                      <div>
                        <span className="text-gray-600">COG Size:</span>
                        <span className="ml-2 font-medium">{processing.cog_size_mb} MB</span>
                      </div>
                    </>
                  )}
                  {processing.compression_ratio && (
                    <div className="col-span-2">
                      <span className="text-gray-600">Compression:</span>
                      <span className="ml-2 font-medium text-green-600">{processing.compression_ratio}% smaller</span>
                    </div>
                  )}
                </div>

                {processing.cog_validation && (
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <div className="text-xs text-gray-600">
                      <strong>COG Validation:</strong>
                      <ul className="mt-1 space-y-1">
                        <li className="flex justify-between">
                          <span>Valid COG:</span>
                          <span className={processing.cog_validation.is_valid_cog ? 'text-green-600' : 'text-red-600'}>
                            {processing.cog_validation.is_valid_cog ? 'Yes' : 'No'}
                          </span>
                        </li>
                        <li className="flex justify-between">
                          <span>Tiled:</span>
                          <span className={processing.cog_validation.is_tiled ? 'text-green-600' : 'text-red-600'}>
                            {processing.cog_validation.is_tiled ? 'Yes' : 'No'}
                          </span>
                        </li>
                        <li className="flex justify-between">
                          <span>Overviews:</span>
                          <span>{processing.cog_validation.overview_count || 0}</span>
                        </li>
                      </ul>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* File Paths */}
          {paths && (
            <div>
              <h4 className="font-medium text-gray-900 mb-3">Generated Files</h4>
              <div className="bg-gray-50 rounded-lg p-4 space-y-2 text-sm">
                <div>
                  <span className="text-gray-600">Original:</span>
                  <code className="ml-2 text-xs bg-white px-2 py-1 rounded">{paths.original}</code>
                </div>
                <div>
                  <span className="text-gray-600">COG:</span>
                  <code className="ml-2 text-xs bg-white px-2 py-1 rounded">{paths.cog}</code>
                </div>
              </div>
            </div>
          )}

          {/* Summary */}
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="flex items-center">
              <svg className="w-5 h-5 text-green-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span className="text-green-800 font-medium">
                Dataset successfully processed and added to your collection
              </span>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-start">
              <svg className="w-5 h-5 text-red-600 mr-2 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <h4 className="text-red-800 font-medium mb-1">Processing Error</h4>
                <p className="text-red-700 text-sm">{result.error}</p>
              </div>
            </div>
          </div>

          {result.details && (
            <div className="text-sm text-gray-600">
              <strong>Details:</strong> {result.details}
            </div>
          )}
        </div>
      )}
    </div>
  );
}