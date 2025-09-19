'use client';

import React, { useState, useEffect } from 'react';

interface ClassMappingProps {
  mappingData: any;
  onMappingUpdate?: (updatedMapping: any) => void;
  readonly?: boolean;
}

interface FuelClass {
  id: number;
  name: string;
  group: string;
  description?: string;
}

export default function ClassMappingReview({ mappingData, onMappingUpdate, readonly = false }: ClassMappingProps) {
  const [mapping, setMapping] = useState(mappingData || {});
  const [fbfm40Classes, setFbfm40Classes] = useState<FuelClass[]>([]);
  const [editingClass, setEditingClass] = useState<number | null>(null);

  useEffect(() => {
    // Load FBFM40 reference classes
    const loadFbfm40Classes = async () => {
      try {
        const response = await fetch('/api/detect-classification');
        const data = await response.json();

        if (data.success && data.systems?.FBFM40) {
          // Convert to array format for easier use
          const classes = [
            { id: 1, name: 'Short Grass (1 ft)', group: 'grass' },
            { id: 2, name: 'Timber (Grass and Understory)', group: 'grass' },
            { id: 3, name: 'Tall Grass (2.5 ft)', group: 'grass' },
            { id: 4, name: 'Chaparral (6 ft)', group: 'chaparral' },
            { id: 5, name: 'Brush (2 ft)', group: 'shrub' },
            { id: 6, name: 'Dormant Brush, Hardwood Slash', group: 'shrub' },
            { id: 7, name: 'Southern Rough', group: 'shrub' },
            { id: 8, name: 'Closed Timber Litter', group: 'timber' },
            { id: 9, name: 'Hardwood Litter', group: 'timber' },
            { id: 10, name: 'Timber (Litter and Understory)', group: 'timber' },
            { id: 11, name: 'Light Logging Slash', group: 'slash' },
            { id: 12, name: 'Medium Logging Slash', group: 'slash' },
            { id: 13, name: 'Heavy Logging Slash', group: 'slash' },
            { id: 14, name: 'Low Load, Dry Climate Shrub', group: 'shrub' },
            { id: 15, name: 'High Load, Dry Climate Shrub', group: 'shrub' },
            { id: 91, name: 'Urban or Developed', group: 'non-burnable' },
            { id: 92, name: 'Snow or Ice', group: 'non-burnable' },
            { id: 93, name: 'Agriculture', group: 'non-burnable' },
            { id: 98, name: 'Water', group: 'non-burnable' },
            { id: 99, name: 'Barren or Sparsely Vegetated', group: 'non-burnable' }
          ];
          setFbfm40Classes(classes);
        }
      } catch (error) {
        console.error('Failed to load FBFM40 classes:', error);
      }
    };

    loadFbfm40Classes();
  }, []);

  const getGroupColor = (group: string) => {
    const colors = {
      grass: 'bg-green-100 text-green-800',
      shrub: 'bg-orange-100 text-orange-800',
      timber: 'bg-emerald-100 text-emerald-800',
      chaparral: 'bg-yellow-100 text-yellow-800',
      slash: 'bg-red-100 text-red-800',
      'non-burnable': 'bg-gray-100 text-gray-800',
    };
    return colors[group as keyof typeof colors] || 'bg-gray-100 text-gray-800';
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return 'text-green-600';
    if (confidence >= 0.8) return 'text-yellow-600';
    return 'text-red-600';
  };

  const updateMapping = (sourceClass: number, targetClass: number) => {
    if (readonly) return;

    const updatedMapping = {
      ...mapping,
      mappings: {
        ...mapping.mappings,
        [sourceClass]: targetClass
      }
    };

    // Remove from unmapped if it was there
    if (mapping.unmapped_classes?.includes(sourceClass)) {
      updatedMapping.unmapped_classes = mapping.unmapped_classes.filter(
        (cls: number) => cls !== sourceClass
      );
      updatedMapping.manual_review_count = (updatedMapping.manual_review_count || 0) - 1;
      updatedMapping.auto_mapped_count = (updatedMapping.auto_mapped_count || 0) + 1;
    }

    setMapping(updatedMapping);
    onMappingUpdate?.(updatedMapping);
    setEditingClass(null);
  };

  const removeMapping = (sourceClass: number) => {
    if (readonly) return;

    const updatedMapping = { ...mapping };
    delete updatedMapping.mappings[sourceClass];

    // Add to unmapped
    if (!updatedMapping.unmapped_classes?.includes(sourceClass)) {
      updatedMapping.unmapped_classes = [...(updatedMapping.unmapped_classes || []), sourceClass];
      updatedMapping.manual_review_count = (updatedMapping.manual_review_count || 0) + 1;
      updatedMapping.auto_mapped_count = Math.max((updatedMapping.auto_mapped_count || 0) - 1, 0);
    }

    setMapping(updatedMapping);
    onMappingUpdate?.(updatedMapping);
    setEditingClass(null);
  };

  if (!mapping || (!mapping.mappings && !mapping.unmapped_classes)) {
    return (
      <div className="fuel-card">
        <div className="text-center py-8">
          <svg className="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <p className="text-gray-500">No class mapping data available</p>
        </div>
      </div>
    );
  }

  const mappedClasses = Object.entries(mapping.mappings || {});
  const unmappedClasses = mapping.unmapped_classes || [];

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="fuel-card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Class Mapping Summary</h3>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
          <div className="text-center">
            <div className="text-xl font-bold text-blue-600">{mappedClasses.length}</div>
            <div className="text-sm text-gray-600">Mapped Classes</div>
          </div>
          <div className="text-center">
            <div className="text-xl font-bold text-orange-600">{unmappedClasses.length}</div>
            <div className="text-sm text-gray-600">Need Review</div>
          </div>
          <div className="text-center">
            <div className="text-xl font-bold text-green-600">
              {mapping.auto_mapped_count || 0}
            </div>
            <div className="text-sm text-gray-600">Auto-mapped</div>
          </div>
          <div className="text-center">
            <div className={`text-xl font-bold ${mapping.auto_mappable ? 'text-green-600' : 'text-red-600'}`}>
              {mapping.auto_mappable ? 'Yes' : 'No'}
            </div>
            <div className="text-sm text-gray-600">Auto-mappable</div>
          </div>
        </div>

        <div className="flex items-center space-x-4 text-sm">
          <div className="flex items-center space-x-2">
            <span className="font-medium">Source:</span>
            <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
              {mapping.source_system}
            </span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="font-medium">Target:</span>
            <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs">
              {mapping.target_system || 'FBFM40'}
            </span>
          </div>
        </div>
      </div>

      {/* Mapped Classes */}
      {mappedClasses.length > 0 && (
        <div className="fuel-card">
          <h4 className="font-medium text-gray-900 mb-4">Mapped Classes</h4>

          <div className="space-y-3">
            {mappedClasses.map(([sourceClass, targetClass]) => {
              const source = parseInt(sourceClass);
              const target = parseInt(targetClass as string);
              const confidence = mapping.confidence_scores?.[source] || 1.0;
              const targetClassInfo = fbfm40Classes.find(c => c.id === target);

              return (
                <div key={sourceClass} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center space-x-4">
                    <div className="text-center">
                      <div className="text-lg font-semibold text-gray-900">{source}</div>
                      <div className="text-xs text-gray-500">Source</div>
                    </div>

                    <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                    </svg>

                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="text-lg font-semibold text-gray-900">{target}</span>
                        {targetClassInfo && (
                          <span className={`fuel-badge ${getGroupColor(targetClassInfo.group)}`}>
                            {targetClassInfo.group}
                          </span>
                        )}
                      </div>
                      {targetClassInfo && (
                        <div className="text-sm text-gray-600">{targetClassInfo.name}</div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    <div className="text-right">
                      <div className={`text-sm font-medium ${getConfidenceColor(confidence)}`}>
                        {(confidence * 100).toFixed(0)}%
                      </div>
                      <div className="text-xs text-gray-500">confidence</div>
                    </div>

                    {!readonly && (
                      <button
                        onClick={() => setEditingClass(source)}
                        className="p-1 text-gray-400 hover:text-gray-600"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Unmapped Classes */}
      {unmappedClasses.length > 0 && (
        <div className="fuel-card">
          <h4 className="font-medium text-gray-900 mb-4">Classes Requiring Manual Review</h4>

          <div className="space-y-3">
            {unmappedClasses.map((sourceClass: number) => (
              <div key={sourceClass} className="flex items-center justify-between p-3 bg-amber-50 border border-amber-200 rounded-lg">
                <div className="flex items-center space-x-4">
                  <div className="text-center">
                    <div className="text-lg font-semibold text-gray-900">{sourceClass}</div>
                    <div className="text-xs text-gray-500">Unmapped</div>
                  </div>

                  <div className="text-sm text-amber-700">
                    No automatic mapping available - manual review required
                  </div>
                </div>

                {!readonly && (
                  <button
                    onClick={() => setEditingClass(sourceClass)}
                    className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                  >
                    Map Class
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editingClass !== null && !readonly && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full m-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Map Source Class {editingClass}
            </h3>

            <div className="space-y-3 max-h-64 overflow-y-auto">
              {fbfm40Classes.map((fuelClass) => (
                <button
                  key={fuelClass.id}
                  onClick={() => updateMapping(editingClass, fuelClass.id)}
                  className="w-full text-left p-3 rounded-lg border hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium text-gray-900">{fuelClass.id}</div>
                      <div className="text-sm text-gray-600">{fuelClass.name}</div>
                    </div>
                    <span className={`fuel-badge ${getGroupColor(fuelClass.group)}`}>
                      {fuelClass.group}
                    </span>
                  </div>
                </button>
              ))}
            </div>

            <div className="mt-6 flex space-x-3">
              <button
                onClick={() => setEditingClass(null)}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
              {mapping.mappings?.[editingClass] && (
                <button
                  onClick={() => removeMapping(editingClass)}
                  className="flex-1 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
                >
                  Remove Mapping
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}