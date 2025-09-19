'use client';

import React, { useState, useRef, useCallback } from 'react';

interface FileUploadZoneProps {
  tenantId: string;
  onUploadSuccess: (result: any) => void;
  onUploadError: (error: string) => void;
}

export default function FileUploadZone({ tenantId, onUploadSuccess, onUploadError }: FileUploadZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [classificationSystem, setClassificationSystem] = useState('auto-detect');
  const [datasetType, setDatasetType] = useState<'regional' | 'global'>('regional');
  const [forceReprocess, setForceReprocess] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  }, []);

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const handleFileSelect = (file: File) => {
    // Validate file type
    if (!file.name.toLowerCase().endsWith('.tif') && !file.name.toLowerCase().endsWith('.tiff')) {
      onUploadError('Only GeoTIFF files (.tif, .tiff) are supported');
      return;
    }

    // Check file size (max 2GB)
    if (file.size > 2 * 1024 * 1024 * 1024) {
      onUploadError('File size must be less than 2GB');
      return;
    }

    setSelectedFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setUploadProgress(0);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('tenant_id', tenantId);
      formData.append('classification_system', classificationSystem);
      formData.append('dataset_type', datasetType);
      formData.append('force_reprocess', forceReprocess.toString());

      // Simulate progress (real progress would require chunked upload)
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + Math.random() * 10;
        });
      }, 500);

      const response = await fetch('/api/process-geospatial', {
        method: 'POST',
        body: formData,
      });

      clearInterval(progressInterval);
      setUploadProgress(100);

      const result = await response.json();

      if (result.success) {
        onUploadSuccess(result);
        setSelectedFile(null);
        setUploadProgress(0);
      } else {
        onUploadError(result.error || 'Upload failed');
      }
    } catch (error) {
      onUploadError(`Upload failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const clearFile = () => {
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="space-y-6">
      {/* File Upload Zone */}
      <div
        className={`fuel-upload-zone ${isDragOver ? 'dragover' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".tif,.tiff"
          onChange={handleFileInputChange}
          className="hidden"
        />

        <div className="space-y-4">
          <div className="w-12 h-12 mx-auto bg-gray-100 rounded-full flex items-center justify-center">
            <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>

          <div>
            <p className="text-lg font-medium text-gray-900">
              Drop your GeoTIFF file here
            </p>
            <p className="text-sm text-gray-500">
              or click to browse files
            </p>
          </div>

          <div className="text-xs text-gray-400">
            Supported: .tif, .tiff (max 2GB)
          </div>
        </div>
      </div>

      {/* Selected File */}
      {selectedFile && (
        <div className="fuel-card">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>

              <div>
                <p className="font-medium text-gray-900">{selectedFile.name}</p>
                <p className="text-sm text-gray-500">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            </div>

            <button
              onClick={clearFile}
              className="text-gray-400 hover:text-gray-600"
              disabled={isUploading}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Processing Options */}
          <div className="mt-4 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Dataset Type
              </label>
              <select
                value={datasetType}
                onChange={(e) => setDatasetType(e.target.value as 'regional' | 'global')}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={isUploading}
              >
                <option value="regional">Regional Dataset</option>
                <option value="global">Global Baseline Dataset</option>
              </select>
              <p className="mt-1 text-xs text-gray-500">
                {datasetType === 'regional'
                  ? 'Regional datasets provide high-resolution data for specific areas and take priority over global datasets.'
                  : 'Global datasets provide broad coverage as baseline fuel models with lower priority.'
                }
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Classification System
              </label>
              <select
                value={classificationSystem}
                onChange={(e) => setClassificationSystem(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={isUploading}
              >
                <option value="auto-detect">Auto-detect</option>
                <option value="FBFM40">FBFM40 (Anderson Fire Behavior)</option>
                <option value="SENTINEL_FUEL_2024">Sentinel Fuel 2024</option>
                <option value="LANDFIRE_US">LANDFIRE US</option>
                <option value="CANADIAN_FBP">Canadian FBP</option>
              </select>
            </div>

            <div className="flex items-center">
              <input
                id="force-reprocess"
                type="checkbox"
                checked={forceReprocess}
                onChange={(e) => setForceReprocess(e.target.checked)}
                className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
                disabled={isUploading}
              />
              <label htmlFor="force-reprocess" className="ml-2 text-sm text-gray-700">
                Force reprocessing (overwrite existing)
              </label>
            </div>
          </div>

          {/* Upload Progress */}
          {isUploading && (
            <div className="mt-4">
              <div className="flex justify-between text-sm text-gray-600 mb-2">
                <span>Processing...</span>
                <span>{Math.round(uploadProgress)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                ></div>
              </div>
            </div>
          )}

          {/* Upload Button */}
          <div className="mt-6">
            <button
              onClick={handleUpload}
              disabled={isUploading}
              className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {isUploading ? 'Processing...' : 'Process Fuel Map'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}