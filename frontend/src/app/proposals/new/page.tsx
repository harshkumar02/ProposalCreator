'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { api } from '@/lib/api';
import { Button, Card, Input } from '@/components/ui';
import { ArrowLeft, FileText } from 'lucide-react';

interface RFP {
  id: number;
  filename: string | null;
  file_type: string;
  uploaded_at: string;
}

export default function NewProposalPage() {
  const router = useRouter();
  const [clientName, setClientName] = useState('');
  const [title, setTitle] = useState('');
  const [selectedRfpId, setSelectedRfpId] = useState<number | null>(null);
  const [rfps, setRfps] = useState<RFP[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingRfps, setLoadingRfps] = useState(true);

  useEffect(() => {
    loadRFPs();
  }, []);

  const loadRFPs = async () => {
    setLoadingRfps(true);
    try {
      const data = await api.listRFPs();
      setRfps(data);
    } catch (err) {
      console.error('Failed to load RFPs:', err);
    } finally {
      setLoadingRfps(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const proposal = await api.createProposal({
        client_name: clientName,
        title: title || undefined,
        rfp_id: selectedRfpId || undefined
      });
      router.push(`/proposals/${proposal.id}`);
    } catch (err) {
      console.error('Failed to create proposal:', err);
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <Link href="/dashboard" className="inline-flex items-center text-gray-600 hover:text-gray-900">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Dashboard
          </Link>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Create New Proposal</h1>

        <Card>
          <form onSubmit={handleSubmit} className="space-y-6">
            <Input
              label="Client Name"
              value={clientName}
              onChange={(e) => setClientName(e.target.value)}
              placeholder="Enter client or company name"
              required
            />

            <Input
              label="Proposal Title (Optional)"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Enter a title for this proposal"
            />

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Link RFP (Optional)
              </label>
              {loadingRfps ? (
                <p className="text-gray-500">Loading RFPs...</p>
              ) : rfps.length === 0 ? (
                <div>
                  <p className="text-gray-500 mb-2">No RFPs available.</p>
                  <Link href="/rfps/new">
                    <Button variant="secondary" type="button">Upload an RFP first</Button>
                  </Link>
                </div>
              ) : (
                <div className="space-y-2">
                  <label className="flex items-center gap-2 p-3 border rounded-lg hover:bg-gray-50 cursor-pointer">
                    <input
                      type="radio"
                      name="rfp"
                      checked={selectedRfpId === null}
                      onChange={() => setSelectedRfpId(null)}
                      className="text-primary-600"
                    />
                    <span className="text-gray-700">No RFP (blank proposal)</span>
                  </label>
                  {rfps.map((rfp) => (
                    <label key={rfp.id} className="flex items-center gap-2 p-3 border rounded-lg hover:bg-gray-50 cursor-pointer">
                      <input
                        type="radio"
                        name="rfp"
                        checked={selectedRfpId === rfp.id}
                        onChange={() => setSelectedRfpId(rfp.id)}
                        className="text-primary-600"
                      />
                      <FileText className="w-4 h-4 text-gray-400" />
                      <span className="text-gray-700">
                        {rfp.filename || `RFP #${rfp.id}`}
                      </span>
                      <span className="text-xs text-gray-400">
                        {rfp.file_type.toUpperCase()} - {new Date(rfp.uploaded_at).toLocaleDateString()}
                      </span>
                    </label>
                  ))}
                </div>
              )}
            </div>

            <div className="flex justify-end gap-4 pt-4 border-t">
              <Link href="/dashboard">
                <Button variant="secondary" type="button">Cancel</Button>
              </Link>
              <Button type="submit" loading={loading} disabled={!clientName.trim()}>
                Create Proposal
              </Button>
            </div>
          </form>
        </Card>
      </main>
    </div>
  );
}