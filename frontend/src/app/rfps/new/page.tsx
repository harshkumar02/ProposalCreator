'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { Button, Card, Input, Textarea } from '@/components/ui';
import { ArrowLeft, Upload, FileText, AlertCircle } from 'lucide-react';
import Link from 'next/link';

export default function NewRFPPage() {
  const router = useRouter();
  const [mode, setMode] = useState<'upload' | 'paste'>('upload');
  const [file, setFile] = useState<File | null>(null);
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError('');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (mode === 'upload' && !file) {
        setError('Please select a file to upload');
        setLoading(false);
        return;
      }

      if (mode === 'paste' && !content.trim()) {
        setError('Please paste some content');
        setLoading(false);
        return;
      }

      const result = await api.uploadRFP(file || undefined, mode === 'paste' ? content : undefined);
      router.push(`/rfps/${result.id}`);
    } catch (err: any) {
      setError(err.message || 'Failed to upload RFP');
    } finally {
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
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Upload RFP</h1>

        {/* Mode Toggle */}
        <div className="flex gap-4 mb-6">
          <button
            onClick={() => setMode('upload')}
            className={`flex-1 py-4 px-6 rounded-lg border-2 transition-colors ${
              mode === 'upload'
                ? 'border-primary-500 bg-primary-50 text-primary-700'
                : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'
            }`}
          >
            <Upload className="w-6 h-6 mx-auto mb-2" />
            <span className="font-medium">Upload File</span>
          </button>
          <button
            onClick={() => setMode('paste')}
            className={`flex-1 py-4 px-6 rounded-lg border-2 transition-colors ${
              mode === 'paste'
                ? 'border-primary-500 bg-primary-50 text-primary-700'
                : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'
            }`}
          >
            <FileText className="w-6 h-6 mx-auto mb-2" />
            <span className="font-medium">Paste Text</span>
          </button>
        </div>

        <Card>
          {error && (
            <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-4 flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            {mode === 'upload' ? (
              <div className="space-y-4">
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-primary-400 transition-colors">
                  <input
                    type="file"
                    id="file-upload"
                    className="hidden"
                    onChange={handleFileChange}
                    accept=".pdf,.doc,.docx,.txt"
                  />
                  <label htmlFor="file-upload" className="cursor-pointer">
                    <Upload className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                    {file ? (
                      <div>
                        <p className="text-lg font-medium text-gray-900">{file.name}</p>
                        <p className="text-sm text-gray-500">{(file.size / 1024).toFixed(1)} KB</p>
                        <p className="text-sm text-primary-600 mt-2">Click to change file</p>
                      </div>
                    ) : (
                      <div>
                        <p className="text-lg font-medium text-gray-900">Click to upload RFP</p>
                        <p className="text-sm text-gray-500 mt-1">PDF, Word, or Text files</p>
                      </div>
                    )}
                  </label>
                </div>
              </div>
            ) : (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Paste RFP Content
                </label>
                <textarea
                  className="w-full h-64 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none"
                  placeholder="Paste the RFP content here..."
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                />
              </div>
            )}

            <div className="mt-6 flex justify-end gap-4">
              <Link href="/dashboard">
                <Button variant="secondary" type="button">Cancel</Button>
              </Link>
              <Button type="submit" loading={loading}>
                Upload RFP
              </Button>
            </div>
          </form>
        </Card>
      </main>
    </div>
  );
}