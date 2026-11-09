'use client';

import React, { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { api } from '@/lib/api';
import { Button, Card, Badge, Spinner, Textarea } from '@/components/ui';
import ClauseAnalysis from '@/components/ClauseAnalysis';
import { ArrowLeft, FileText, Sparkles, CheckCircle, Clock, AlertCircle, Edit, Trash2 } from 'lucide-react';

interface ExtractionResult {
  id: number;
  rfp_id: number;
  engine: string;
  field_name: string;
  value: string | null;
  confidence: number;
  is_reviewed: boolean;
}

interface RFP {
  id: number;
  filename: string | null;
  file_type: string;
  uploaded_at: string;
}

export default function RFPPage() {
  const params = useParams();
  const router = useRouter();
  const rfpId = parseInt(params.id as string);

  const [rfp, setRfp] = useState<RFP | null>(null);
  const [content, setContent] = useState('');
  const [results, setResults] = useState<ExtractionResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [extracting, setExtracting] = useState(false);
  const [editingResult, setEditingResult] = useState<ExtractionResult | null>(null);

  useEffect(() => {
    loadRFP();
  }, [rfpId]);

  const loadRFP = async () => {
    setLoading(true);
    try {
      const rfpData = await api.getRFP(rfpId);
      setRfp(rfpData);

      const contentData = await api.getRFPContent(rfpId);
      setContent(contentData.content || '');

      const resultsData = await api.getExtractionResults(rfpId);
      setResults(resultsData.results || []);
    } catch (err) {
      console.error('Failed to load RFP:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleExtract = async () => {
    setExtracting(true);
    try {
      const data = await api.extractRFP(rfpId, ['claude', 'openai']);
      setResults(data.results || []);
    } catch (err) {
      console.error('Extraction failed:', err);
      alert('Extraction failed. Please check your API keys.');
    } finally {
      setExtracting(false);
    }
  };

  const handleUpdateResult = async (result: ExtractionResult) => {
    try {
      await api.updateExtractionResult(rfpId, result.id, {
        value: result.value,
        is_reviewed: result.is_reviewed
      });
      setEditingResult(null);
      loadRFP();
    } catch (err) {
      console.error('Failed to update result:', err);
    }
  };

  const handleDelete = async () => {
    if (confirm('Are you sure you want to delete this RFP?')) {
      try {
        await api.deleteRFP(rfpId);
        router.push('/dashboard');
      } catch (err) {
        console.error('Failed to delete RFP:', err);
      }
    }
  };

  const handleCreateProposal = async () => {
    try {
      const proposal = await api.createProposal({
        client_name: 'New Proposal',
        rfp_id: rfpId
      });
      router.push(`/proposals/${proposal.id}`);
    } catch (err) {
      console.error('Failed to create proposal:', err);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!rfp) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card>
          <h2 className="text-xl font-bold text-red-600">RFP not found</h2>
          <Link href="/dashboard">
            <Button className="mt-4">Back to Dashboard</Button>
          </Link>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <Link href="/dashboard" className="inline-flex items-center text-gray-600 hover:text-gray-900">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Dashboard
            </Link>
            <Button variant="danger" onClick={handleDelete}>
              <Trash2 className="w-4 h-4 mr-2" />
              Delete
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{rfp.filename || `RFP #${rfp.id}`}</h1>
            <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
              <Badge>{rfp.file_type.toUpperCase()}</Badge>
              <span>Uploaded {new Date(rfp.uploaded_at).toLocaleDateString()}</span>
              <span>{results.length} extraction results</span>
            </div>
          </div>

          <div className="flex gap-4">
            {results.length > 0 && (
              <Button variant="secondary" onClick={handleCreateProposal}>
                Create Proposal
              </Button>
            )}
            <Button
              onClick={handleExtract}
              loading={extracting}
              disabled={!content}
            >
              <Sparkles className="w-4 h-4 mr-2" />
              {results.length > 0 ? 'Re-extract' : 'Extract Data'}
            </Button>
          </div>
        </div>

        <ClauseAnalysis rfpId={rfpId} hasContent={!!content} />

        {/* RFP Content */}
        <Card className="mb-8">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <FileText className="w-5 h-5" />
            RFP Content
          </h2>
          <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
            <pre className="whitespace-pre-wrap text-sm text-gray-700 font-mono">
              {content || 'No content available'}
            </pre>
          </div>
        </Card>

        {/* Extraction Results */}
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-900">Extracted Data</h2>
          {results.length > 0 && (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <CheckCircle className="w-4 h-4 text-green-500" />
              {results.filter(r => r.is_reviewed).length} of {results.length} reviewed
            </div>
          )}
        </div>

        {results.length === 0 ? (
          <Card className="text-center py-12">
            <Sparkles className="w-12 h-12 mx-auto text-gray-400 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No extraction results yet</h3>
            <p className="text-gray-500 mb-4">Click "Extract Data" to analyze the RFP and extract key information.</p>
          </Card>
        ) : (
          <div className="space-y-4">
            {/* Group results by field_name */}
            {Object.entries(
              results.reduce((acc, result) => {
                const key = result.field_name;
                if (!acc[key]) acc[key] = [];
                acc[key].push(result);
                return acc;
              }, {} as Record<string, ExtractionResult[]>)
            ).map(([fieldName, fieldResults]) => (
              <Card key={fieldName}>
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="font-semibold text-gray-900 capitalize">
                      {fieldName.replace(/_/g, ' ')}
                    </h3>
                    <div className="flex items-center gap-2 mt-1">
                      {fieldResults.map((r, i) => (
                        <Badge key={i} variant="default">{r.engine}</Badge>
                      ))}
                      <span className="text-xs text-gray-400">
                        Avg confidence: {(fieldResults.reduce((a, b) => a + b.confidence, 0) / fieldResults.length * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  {fieldResults.every(r => r.is_reviewed) ? (
                    <CheckCircle className="w-5 h-5 text-green-500" />
                  ) : (
                    <button
                      onClick={() => {
                        fieldResults.forEach(r => {
                          if (!r.is_reviewed) {
                            api.updateExtractionResult(rfpId, r.id, { is_reviewed: true });
                          }
                        });
                        loadRFP();
                      }}
                      className="text-sm text-primary-600 hover:underline"
                    >
                      Mark all reviewed
                    </button>
                  )}
                </div>

                <div className="space-y-2">
                  {fieldResults.map((result) => (
                    <div key={result.id} className="flex items-center gap-2">
                      {editingResult?.id === result.id ? (
                        <div className="flex-1 flex gap-2">
                          <input
                            type="text"
                            value={editingResult.value || ''}
                            onChange={(e) => setEditingResult({ ...editingResult, value: e.target.value })}
                            className="flex-1 px-3 py-1 border rounded"
                          />
                          <Button size="sm" onClick={() => handleUpdateResult(editingResult)}>
                            Save
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => setEditingResult(null)}>
                            Cancel
                          </Button>
                        </div>
                      ) : (
                        <>
                          <span className="text-sm text-gray-600">{result.value || '(empty)'}</span>
                          <span className="text-xs text-gray-400">({result.engine})</span>
                          <button
                            onClick={() => setEditingResult(result)}
                            className="text-primary-600 hover:text-primary-700"
                          >
                            <Edit className="w-3 h-3" />
                          </button>
                        </>
                      )}
                    </div>
                  ))}
                </div>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}