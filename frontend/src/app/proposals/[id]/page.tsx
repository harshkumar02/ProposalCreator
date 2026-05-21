'use client';

import React, { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { api } from '@/lib/api';
import { Button, Card, Badge, Spinner, Input, Textarea } from '@/components/ui';
import { ArrowLeft, Save, Download, Sparkles, Copy, Trash2, Eye, ChevronDown, ChevronRight, Info } from 'lucide-react';

interface ExtractionResult {
  id: number;
  field_name: string;
  value: string | null;
  confidence: number;
  is_reviewed: boolean;
}

interface Proposal {
  id: number;
  client_name: string;
  title: string | null;
  status: string;
  version: number;
  rfp_id: number | null;
  created_at: string;
  updated_at: string;
}

// Editable sections for 63SATS proposal (fixed content auto-filled)
const EDITABLE_SECTIONS = {
  '1. Proposal Overview': {
    '1.1 Overview': ['proposal_overview'],
  },
  '2. Current Challenges': {
    '2.1 Client Challenges': ['current_challenges', 'challenges'],
  },
  '3. Objectives': {
    '3.1 Project Objectives': ['objectives'],
  },
  '4. Scope of Work': {
    '4.1 Assets in Scope': ['assets'],
    '4.2 Key Services': ['key_services'],
  },
  '5. Solution Proposed': {
    '5.1 Our Solution': ['solution_proposed'],
  },
  '6. Implementation Plan': {
    '6.1 Implementation Approach': ['implementation_approach'],
    '6.2 Methodology': ['implementation_methodology'],
  },
  '8. Assumptions': {
    '8.1 Terms & Assumptions': ['assumptions'],
  },
  '9. Implementation Timeline': {
    '9.1 Project Timeline': ['timeline', 'implementation_timeline'],
  },
  '10. Expected Outcomes & ROI': {
    '10.1 Outcomes': ['expected_outcomes', 'roi'],
  },
  '12. Conclusion': {
    '12.1 Closing Statement': ['conclusion'],
  },
};

export default function ProposalPage() {
  const params = useParams();
  const router = useRouter();
  const proposalId = parseInt(params.id as string);

  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [extractionResults, setExtractionResults] = useState<ExtractionResult[]>([]);
  const [editedData, setEditedData] = useState<Record<string, string>>({});
  const [clientName, setClientName] = useState('');
  const [title, setTitle] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [preview, setPreview] = useState('');
  const [showPreview, setShowPreview] = useState(false);
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    '1. Proposal Overview': true,
    '2. Current Challenges': true,
    '3. Objectives': true,
    '4. Scope of Work': true,
    '5. Solution Proposed': true,
    '6. Implementation Plan': true,
    '8. Assumptions': true,
    '9. Implementation Timeline': true,
    '10. Expected Outcomes & ROI': true,
    '12. Conclusion': true,
  });

  useEffect(() => {
    loadProposal();
  }, [proposalId]);

  const loadProposal = async () => {
    setLoading(true);
    try {
      const data = await api.getProposal(proposalId);
      setProposal(data);
      setClientName(data.client_name);
      setTitle(data.title || '');

      if (data.extraction_results) {
        setExtractionResults(data.extraction_results);

        const initialData: Record<string, string> = {};
        data.extraction_results.forEach((r: ExtractionResult) => {
          initialData[r.field_name] = r.value || '';
        });
        setEditedData(initialData);
      }
    } catch (err) {
      console.error('Failed to load proposal:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.updateProposal(proposalId, {
        client_name: clientName,
        title: title || undefined,
        extracted_data: JSON.stringify(editedData)
      });

      for (const result of extractionResults) {
        await api.updateExtractionResult(proposal!.rfp_id!, result.id, {
          value: editedData[result.field_name] || result.value,
          is_reviewed: true
        });
      }

      alert('Proposal saved successfully!');
    } catch (err) {
      console.error('Failed to save proposal:', err);
      alert('Failed to save proposal');
    } finally {
      setSaving(false);
    }
  };

  const handleDuplicate = async () => {
    try {
      const newProposal = await api.duplicateProposal(proposalId);
      router.push(`/proposals/${newProposal.id}`);
    } catch (err) {
      console.error('Failed to duplicate proposal:', err);
    }
  };

  const handleDelete = async () => {
    if (confirm('Are you sure you want to delete this proposal?')) {
      try {
        await api.deleteProposal(proposalId);
        router.push('/dashboard');
      } catch (err) {
        console.error('Failed to delete proposal:', err);
      }
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await api.updateProposal(proposalId, {
        client_name: clientName,
        title: title || undefined,
        extracted_data: JSON.stringify(editedData)
      });

      const blob = await api.generateProposal(proposalId, selectedTemplateId || undefined);

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `63SATS_Proposal_${clientName.replace(/\s+/g, '_')}.docx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Failed to generate proposal:', err);
      alert('Failed to generate proposal.');
    } finally {
      setGenerating(false);
    }
  };

  const handlePreview = async () => {
    try {
      await api.updateProposal(proposalId, {
        client_name: clientName,
        title: title || undefined,
        extracted_data: JSON.stringify(editedData)
      });

      const data = await api.generateProposalText(proposalId, selectedTemplateId || undefined);
      setPreview(data.text);
      setShowPreview(true);
    } catch (err) {
      console.error('Failed to preview:', err);
    }
  };

  const handleFieldChange = (fieldName: string, value: string) => {
    setEditedData((prev) => ({ ...prev, [fieldName]: value }));
  };

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const getFieldValues = (fieldNames: string[]): Record<string, string> => {
    const values: Record<string, string> = {};
    fieldNames.forEach(name => {
      values[name] = editedData[name] || '';
    });
    return values;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!proposal) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card>
          <h2 className="text-xl font-bold text-red-600">Proposal not found</h2>
          <Link href="/dashboard">
            <Button className="mt-4">Back to Dashboard</Button>
          </Link>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-slate-900 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/dashboard" className="flex items-center text-gray-300 hover:text-white">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Dashboard
              </Link>
              <span className="text-gray-500">|</span>
              <h1 className="text-xl font-bold">63SATS Proposal Editor</h1>
            </div>
            <div className="flex items-center gap-4">
              <Button variant="ghost" onClick={handleDuplicate} className="text-white hover:bg-slate-800">
                <Copy className="w-4 h-4 mr-2" />
                Duplicate
              </Button>
              <Button variant="danger" onClick={handleDelete}>
                <Trash2 className="w-4 h-4 mr-2" />
                Delete
              </Button>
              <Button onClick={handleSave} loading={saving}>
                <Save className="w-4 h-4 mr-2" />
                Save
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Fixed Content Info Banner */}
        <Card className="mb-8 bg-blue-50 border-blue-200">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-blue-600 mt-0.5" />
            <div>
              <h3 className="font-semibold text-blue-900">Pre-filled Content</h3>
              <p className="text-sm text-blue-700">
                Sections 1.1 (About 63SATS), 7 (RACI Matrix), and 11 (Why 63SATS) contain fixed content that appears automatically in all proposals. Edit the sections below to customize your proposal.
              </p>
            </div>
          </div>
        </Card>

        {/* Proposal Header */}
        <Card className="mb-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="md:col-span-2">
              <Input
                label="Client Name"
                value={clientName}
                onChange={(e) => setClientName(e.target.value)}
                placeholder="Enter client or company name"
              />
              <Input
                label="Proposal Title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="mt-4"
                placeholder="e.g., Managed Security Services Proposal"
              />
            </div>
            <div className="text-center p-6 bg-slate-50 rounded-lg">
              <p className="text-sm text-gray-500">Status</p>
              <Badge variant={proposal.status === 'draft' ? 'warning' : 'success'} className="text-lg px-4 py-1">
                {proposal.status}
              </Badge>
              <p className="text-sm text-gray-500 mt-2">Version {proposal.version}</p>
            </div>
          </div>
        </Card>

        {/* Action Buttons */}
        <Card className="mb-8">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-4">
              <Button onClick={handlePreview} variant="secondary">
                <Eye className="w-4 h-4 mr-2" />
                Preview Proposal
              </Button>
              <Button onClick={handleGenerate} loading={generating}>
                <Download className="w-4 h-4 mr-2" />
                Generate 63SATS Proposal (.docx)
              </Button>
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Sparkles className="w-4 h-4 text-primary-500" />
              {extractionResults.filter(r => r.is_reviewed).length} of {extractionResults.length} fields reviewed
            </div>
          </div>
        </Card>

        {/* Preview Modal */}
        {showPreview && (
          <div className="fixed inset-0 z-50 bg-black bg-opacity-50 flex items-center justify-center p-4">
            <Card className="w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
              <div className="flex items-center justify-between mb-4 pb-4 border-b">
                <h2 className="text-xl font-bold">63SATS Proposal Preview</h2>
                <Button variant="ghost" onClick={() => setShowPreview(false)}>Close</Button>
              </div>
              <pre className="whitespace-pre-wrap text-sm font-mono bg-gray-50 p-4 rounded-lg overflow-auto flex-1">
                {preview}
              </pre>
            </Card>
          </div>
        )}

        {/* Proposal Sections */}
        <div className="space-y-4">
          {Object.entries(EDITABLE_SECTIONS).map(([sectionTitle, subsections]) => (
            <div key={sectionTitle} className="border rounded-lg overflow-hidden bg-white">
              <button
                onClick={() => toggleSection(sectionTitle)}
                className="w-full px-6 py-4 bg-slate-100 hover:bg-slate-200 flex items-center justify-between text-left transition-colors"
              >
                <h2 className="text-lg font-bold text-slate-900">{sectionTitle}</h2>
                {expandedSections[sectionTitle] ? (
                  <ChevronDown className="w-5 h-5 text-slate-500" />
                ) : (
                  <ChevronRight className="w-5 h-5 text-slate-500" />
                )}
              </button>

              {expandedSections[sectionTitle] && (
                <div className="p-6 space-y-6">
                  {Object.entries(subsections).map(([subsectionTitle, fieldNames]) => (
                    <div key={subsectionTitle} className="border-b pb-6 last:border-b-0 last:pb-0">
                      <h3 className="text-md font-semibold text-slate-700 mb-4">{subsectionTitle}</h3>
                      <div className="space-y-4">
                        {fieldNames.map((fieldName) => (
                          <div key={fieldName}>
                            <label className="block text-sm font-medium text-gray-700 mb-2 capitalize">
                              {fieldName.replace(/_/g, ' ')}
                            </label>
                            <textarea
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none resize-none"
                              rows={fieldName === 'solution_proposed' || fieldName === 'implementation_approach' ? 6 : 4}
                              value={editedData[fieldName] || ''}
                              onChange={(e) => handleFieldChange(fieldName, e.target.value)}
                              placeholder={`Enter ${fieldName.replace(/_/g, ' ')}...`}
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Additional Custom Fields */}
        <Card className="mt-8">
          <h3 className="font-semibold text-gray-900 mb-4">Additional Notes</h3>
          <Textarea
            label="Custom Notes (Optional)"
            value={editedData.custom_notes || ''}
            onChange={(e) => handleFieldChange('custom_notes', e.target.value)}
            placeholder="Add any additional notes or information for this proposal..."
            rows={6}
          />
        </Card>
      </main>
    </div>
  );
}