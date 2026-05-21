'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { Button, Card, Badge, Spinner, Input, Textarea } from '@/components/ui';
import { ArrowLeft, Plus, Trash2, Edit, Check, FileText, Upload } from 'lucide-react';

interface Template {
  id: number;
  name: string;
  is_default: boolean;
  created_at: string;
}

interface TemplateDetail {
  id: number;
  name: string;
  content: string | null;
  is_default: boolean;
  created_at: string;
}

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [newTemplate, setNewTemplate] = useState({ name: '', content: '', is_default: false });
  const [editTemplate, setEditTemplate] = useState<TemplateDetail | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    setLoading(true);
    try {
      const data = await api.listTemplates();
      setTemplates(data);
    } catch (err) {
      console.error('Failed to load templates:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!newTemplate.name.trim()) return;
    setSaving(true);
    try {
      await api.createTemplate({
        name: newTemplate.name,
        content: newTemplate.content || undefined,
        is_default: newTemplate.is_default
      });
      setNewTemplate({ name: '', content: '', is_default: false });
      setShowCreateForm(false);
      loadTemplates();
    } catch (err) {
      console.error('Failed to create template:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      await api.createTemplate({ name: file.name.replace(/\.[^/.]+$/, '') }, file);
      loadTemplates();
    } catch (err) {
      console.error('Failed to upload template:', err);
    }
  };

  const handleEdit = async (id: number) => {
    try {
      const template = await api.getTemplate(id);
      setEditTemplate(template);
    } catch (err) {
      console.error('Failed to load template:', err);
    }
  };

  const handleSaveEdit = async () => {
    if (!editTemplate) return;
    setSaving(true);
    try {
      await api.updateTemplate(editTemplate.id, {
        name: editTemplate.name,
        content: editTemplate.content,
        is_default: editTemplate.is_default
      });
      setEditTemplate(null);
      loadTemplates();
    } catch (err) {
      console.error('Failed to save template:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this template?')) return;
    try {
      await api.deleteTemplate(id);
      loadTemplates();
    } catch (err) {
      console.error('Failed to delete template:', err);
    }
  };

  const handleSetDefault = async (id: number) => {
    try {
      await api.updateTemplate(id, { is_default: true });
      loadTemplates();
    } catch (err) {
      console.error('Failed to set default:', err);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <Link href="/dashboard" className="inline-flex items-center text-gray-600 hover:text-gray-900">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Dashboard
          </Link>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Proposal Templates</h1>
          <div className="flex gap-4">
            <label className="cursor-pointer inline-flex items-center justify-center font-medium rounded-lg transition-colors bg-gray-200 text-gray-800 px-4 py-2 hover:bg-gray-300">
              <input type="file" className="hidden" accept=".docx,.doc,.txt" onChange={handleFileUpload} />
              <Upload className="w-4 h-4 mr-2" />
              Upload Template
            </label>
            <Button onClick={() => setShowCreateForm(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Create Template
            </Button>
          </div>
        </div>

        {/* Create Form */}
        {showCreateForm && (
          <Card className="mb-8">
            <h2 className="text-xl font-semibold mb-4">Create New Template</h2>
            <div className="space-y-4">
              <Input
                label="Template Name"
                value={newTemplate.name}
                onChange={(e) => setNewTemplate({ ...newTemplate, name: e.target.value })}
                placeholder="e.g., Standard Cybersecurity Proposal"
              />
              <Textarea
                label="Template Content (with {{placeholders}})"
                value={newTemplate.content}
                onChange={(e) => setNewTemplate({ ...newTemplate, content: e.target.value })}
                placeholder="Enter template content. Use {{field_name}} for placeholders like {{client_name}}, {{scope_of_work}}, etc."
                rows={12}
              />
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={newTemplate.is_default}
                  onChange={(e) => setNewTemplate({ ...newTemplate, is_default: e.target.checked })}
                  className="rounded text-primary-600"
                />
                <span className="text-sm text-gray-700">Set as default template</span>
              </label>
              <div className="flex justify-end gap-4 pt-4 border-t">
                <Button variant="secondary" onClick={() => setShowCreateForm(false)}>Cancel</Button>
                <Button onClick={handleCreate} loading={saving} disabled={!newTemplate.name.trim()}>
                  Create Template
                </Button>
              </div>
            </div>
          </Card>
        )}

        {/* Edit Form */}
        {editTemplate && (
          <Card className="mb-8">
            <h2 className="text-xl font-semibold mb-4">Edit Template: {editTemplate.name}</h2>
            <div className="space-y-4">
              <Input
                label="Template Name"
                value={editTemplate.name}
                onChange={(e) => setEditTemplate({ ...editTemplate, name: e.target.value })}
              />
              <Textarea
                label="Template Content"
                value={editTemplate.content || ''}
                onChange={(e) => setEditTemplate({ ...editTemplate, content: e.target.value })}
                rows={12}
              />
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={editTemplate.is_default}
                  onChange={(e) => setEditTemplate({ ...editTemplate, is_default: e.target.checked })}
                  className="rounded text-primary-600"
                />
                <span className="text-sm text-gray-700">Set as default template</span>
              </label>
              <div className="flex justify-end gap-4 pt-4 border-t">
                <Button variant="secondary" onClick={() => setEditTemplate(null)}>Cancel</Button>
                <Button onClick={handleSaveEdit} loading={saving}>Save Changes</Button>
              </div>
            </div>
          </Card>
        )}

        {/* Template List */}
        {templates.length === 0 ? (
          <Card className="text-center py-12">
            <FileText className="w-12 h-12 mx-auto text-gray-400 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No templates yet</h3>
            <p className="text-gray-500 mb-4">Create your first proposal template to get started.</p>
            <Button onClick={() => setShowCreateForm(true)}>Create Template</Button>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {templates.map((template) => (
              <Card key={template.id}>
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-purple-100 rounded-lg">
                      <FileText className="w-5 h-5 text-purple-600" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900">{template.name}</h3>
                      <div className="flex items-center gap-2 mt-1">
                        {template.is_default && (
                          <Badge variant="success">Default</Badge>
                        )}
                        <span className="text-xs text-gray-400">
                          Created {new Date(template.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex gap-2 pt-4 border-t">
                  <Button variant="ghost" size="sm" onClick={() => handleEdit(template.id)}>
                    <Edit className="w-4 h-4" />
                  </Button>
                  {!template.is_default && (
                    <Button variant="ghost" size="sm" onClick={() => handleSetDefault(template.id)}>
                      Set Default
                    </Button>
                  )}
                  <Button variant="danger" size="sm" onClick={() => handleDelete(template.id)}>
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* Placeholder Guide */}
        <Card className="mt-8">
          <h3 className="font-semibold text-gray-900 mb-4">Available Placeholders</h3>
          <p className="text-sm text-gray-600 mb-4">
            Use these placeholders in your templates. They will be replaced with the corresponding extracted data.
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            {[
              'client_name', 'project_title', 'scope_of_work', 'requirements',
              'compliance_requirements', 'security_requirements', 'pricing_information',
              'contact_information', 'deliverables', 'qualifications',
              'timeline', 'terms_and_conditions'
            ].map((placeholder) => (
              <div key={placeholder} className="bg-gray-50 px-3 py-2 rounded font-mono text-xs">
                {`{{${placeholder}}}`}
              </div>
            ))}
          </div>
        </Card>
      </main>
    </div>
  );
}