'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/AuthContext';
import { api } from '@/lib/api';
import { Button, Card, Badge, Spinner } from '@/components/ui';
import { FileText, Upload, Plus, Clock, CheckCircle, FileOutput, Settings, LogOut } from 'lucide-react';

interface Proposal {
  id: number;
  client_name: string;
  title: string | null;
  status: string;
  version: number;
  created_at: string;
  updated_at: string;
}

interface RFP {
  id: number;
  filename: string | null;
  file_type: string;
  uploaded_at: string;
}

export default function DashboardPage() {
  const { user, loading: authLoading, logout } = useAuth();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<'proposals' | 'rfps' | 'templates'>('proposals');
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [rfps, setRfps] = useState<RFP[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
    }
  }, [user, authLoading, router]);

  useEffect(() => {
    if (user) {
      loadData();
    }
  }, [user, activeTab]);

  const loadData = async () => {
    setLoading(true);
    try {
      if (activeTab === 'proposals') {
        const data = await api.listProposals();
        setProposals(data);
      } else if (activeTab === 'rfps') {
        const data = await api.listRFPs();
        setRfps(data);
      }
    } catch (err) {
      console.error('Failed to load data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  if (authLoading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <h1 className="text-2xl font-bold text-primary-600">ProposalCreator</h1>
              <span className="text-sm text-gray-500">for Cybersecurity Consultants</span>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-600">{user.email}</span>
              <Button variant="ghost" onClick={handleLogout}>
                <LogOut className="w-4 h-4 mr-2" />
                Logout
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <Link href="/rfps/new">
            <Card className="hover:shadow-lg transition-shadow cursor-pointer">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-primary-100 rounded-lg">
                  <Upload className="w-6 h-6 text-primary-600" />
                </div>
                <div>
                  <h3 className="font-semibold">Upload RFP</h3>
                  <p className="text-sm text-gray-500">Upload a new RFP document</p>
                </div>
              </div>
            </Card>
          </Link>

          <Link href="/proposals/new">
            <Card className="hover:shadow-lg transition-shadow cursor-pointer">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-green-100 rounded-lg">
                  <Plus className="w-6 h-6 text-green-600" />
                </div>
                <div>
                  <h3 className="font-semibold">New Proposal</h3>
                  <p className="text-sm text-gray-500">Create a blank proposal</p>
                </div>
              </div>
            </Card>
          </Link>

          <Link href="/templates">
            <Card className="hover:shadow-lg transition-shadow cursor-pointer">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-purple-100 rounded-lg">
                  <Settings className="w-6 h-6 text-purple-600" />
                </div>
                <div>
                  <h3 className="font-semibold">Manage Templates</h3>
                  <p className="text-sm text-gray-500">Configure proposal templates</p>
                </div>
              </div>
            </Card>
          </Link>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('proposals')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'proposals'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <FileOutput className="w-4 h-4 inline mr-2" />
              Proposals ({proposals.length})
            </button>
            <button
              onClick={() => setActiveTab('rfps')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'rfps'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <FileText className="w-4 h-4 inline mr-2" />
              RFPs ({rfps.length})
            </button>
          </nav>
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex justify-center py-12">
            <Spinner />
          </div>
        ) : (
          <>
            {activeTab === 'proposals' && (
              <div className="space-y-4">
                {proposals.length === 0 ? (
                  <Card className="text-center py-12">
                    <FileOutput className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">No proposals yet</h3>
                    <p className="text-gray-500 mb-4">Create your first proposal or upload an RFP to get started.</p>
                    <Link href="/proposals/new">
                      <Button>Create Proposal</Button>
                    </Link>
                  </Card>
                ) : (
                  proposals.map((proposal) => (
                    <Link key={proposal.id} href={`/proposals/${proposal.id}`}>
                      <Card className="hover:shadow-lg transition-shadow cursor-pointer">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-4">
                            <div className="p-2 bg-primary-100 rounded-lg">
                              <FileOutput className="w-5 h-5 text-primary-600" />
                            </div>
                            <div>
                              <h3 className="font-semibold text-gray-900">{proposal.client_name}</h3>
                              {proposal.title && (
                                <p className="text-sm text-gray-500">{proposal.title}</p>
                              )}
                              <div className="flex items-center gap-2 mt-1 text-xs text-gray-400">
                                <Clock className="w-3 h-3" />
                                Updated {new Date(proposal.updated_at).toLocaleDateString()}
                                <span className="ml-2">v{proposal.version}</span>
                              </div>
                            </div>
                          </div>
                          <Badge variant={proposal.status === 'draft' ? 'warning' : 'success'}>
                            {proposal.status}
                          </Badge>
                        </div>
                      </Card>
                    </Link>
                  ))
                )}
              </div>
            )}

            {activeTab === 'rfps' && (
              <div className="space-y-4">
                {rfps.length === 0 ? (
                  <Card className="text-center py-12">
                    <FileText className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">No RFPs uploaded</h3>
                    <p className="text-gray-500 mb-4">Upload an RFP to start extracting data.</p>
                    <Link href="/rfps/new">
                      <Button>Upload RFP</Button>
                    </Link>
                  </Card>
                ) : (
                  rfps.map((rfp) => (
                    <Link key={rfp.id} href={`/rfps/${rfp.id}`}>
                      <Card className="hover:shadow-lg transition-shadow cursor-pointer">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-4">
                            <div className="p-2 bg-blue-100 rounded-lg">
                              <FileText className="w-5 h-5 text-blue-600" />
                            </div>
                            <div>
                              <h3 className="font-semibold text-gray-900">
                                {rfp.filename || `RFP #${rfp.id}`}
                              </h3>
                              <div className="flex items-center gap-2 mt-1 text-xs text-gray-400">
                                <span className="uppercase">{rfp.file_type}</span>
                                <span>Uploaded {new Date(rfp.uploaded_at).toLocaleDateString()}</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </Card>
                    </Link>
                  ))
                )}
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}