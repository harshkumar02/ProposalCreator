'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import clsx from 'clsx';
import { api } from '@/lib/api';
import { Badge, Button, Card, Spinner } from '@/components/ui';
import { AlertTriangle, Check, ChevronDown, ChevronRight, ListChecks, Plus, ScanSearch, X } from 'lucide-react';

interface Clause {
  id: number;
  clause_code: string;
  category: string;
  criterion_type: string | null;
  requirement: string;
  source_text: string | null;
  mandatory: boolean | null;
  threshold_value: number | null;
  threshold_unit: string | null;
  operator: string | null;
  period: string | null;
  min_count: number | null;
  max_marks: number | null;
  scoring_rule: string | null;
  evidence_required: string[] | null;
  page_number: number | null;
  section_ref: string | null;
  amended_by: string | null;
  confidence: number | null;
  provider: string | null;
  review_status: 'PENDING' | 'VERIFIED' | 'REJECTED';
  reviewer_notes: string | null;
  edited: boolean;
}

interface Summary {
  total: number;
  by_category: Record<string, number>;
  by_review_status: Record<string, number>;
  mandatory_pq: number;
  tq_total_marks: number;
}

interface WorkflowRun {
  id: number;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  current_step: string | null;
  result: Record<string, any> | null;
  error: string | null;
}

const CATEGORIES: { key: string; label: string }[] = [
  { key: 'PQ', label: 'Pre-qualification' },
  { key: 'TQ', label: 'Technical evaluation' },
  { key: 'SCOPE', label: 'Scope of work' },
  { key: 'COMMERCIAL', label: 'Commercial' },
  { key: 'CONTRACTUAL', label: 'Contractual' },
  { key: 'DOCUMENT', label: 'Documents' },
  { key: 'TIMELINE', label: 'Timeline' },
  { key: 'ADMIN', label: 'Admin' },
];

const TENDER_LABELS: Record<string, string> = {
  tender_id: 'Tender no.',
  client_name: 'Client',
  project_name: 'Project',
  submission_deadline: 'Bid deadline',
  pre_bid_meeting: 'Pre-bid meeting',
  bid_validity: 'Bid validity',
  contract_duration: 'Contract period',
  estimated_value_inr: 'Estimated value',
  emd_amount_inr: 'EMD',
  emd_exemption: 'EMD exemption',
  evaluation_method: 'Evaluation',
  tq_cutoff_marks: 'TQ cut-off',
  consortium_allowed: 'Consortium',
  subcontracting_allowed: 'Subcontracting',
};

function formatINR(value: number): string {
  if (value >= 1e7) return `₹${+(value / 1e7).toFixed(2)} Cr`;
  if (value >= 1e5) return `₹${+(value / 1e5).toFixed(2)} lakh`;
  return `₹${value.toLocaleString('en-IN')}`;
}

function formatTenderValue(key: string, value: any): string {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'boolean') return value ? 'Allowed' : 'Not allowed';
  if (key.endsWith('_inr') && typeof value === 'number') return formatINR(value);
  return String(value);
}

function describeThreshold(c: Clause): string | null {
  const parts: string[] = [];
  if (c.min_count !== null) parts.push(`min ${c.min_count}`);
  if (c.threshold_value !== null) {
    const amount = c.threshold_unit === 'INR' ? formatINR(c.threshold_value) : `${c.threshold_value}${c.threshold_unit ? ` ${c.threshold_unit}` : ''}`;
    parts.push(`${c.operator ?? ''} ${amount}`.trim());
  }
  if (c.period) parts.push(c.period);
  return parts.length ? parts.join(' · ') : null;
}

function MandatoryBadge({ value }: { value: boolean | null }) {
  if (value === true) return <Badge variant="danger">Mandatory</Badge>;
  if (value === false) return <Badge variant="default">Desirable</Badge>;
  return <span className="text-xs text-gray-400">Not stated</span>;
}

const STATUS_STYLES: Record<Clause['review_status'], string> = {
  PENDING: 'bg-yellow-100 text-yellow-800',
  VERIFIED: 'bg-green-100 text-green-800',
  REJECTED: 'bg-gray-200 text-gray-500 line-through',
};

export default function ClauseAnalysis({ rfpId, hasContent }: { rfpId: number; hasContent: boolean }) {
  const [clauses, setClauses] = useState<Clause[]>([]);
  const [tenderDetails, setTenderDetails] = useState<Record<string, any> | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const [run, setRun] = useState<WorkflowRun | null>(null);
  const [provider, setProvider] = useState('gemini');
  const [category, setCategory] = useState('PQ');
  const [expanded, setExpanded] = useState<number | null>(null);
  const [draft, setDraft] = useState<Partial<Clause>>({});
  const [newClause, setNewClause] = useState<{ requirement: string; mandatory: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadClauses = useCallback(async () => {
    try {
      const data = await api.getClauses(rfpId);
      setClauses(data.clauses);
      setTenderDetails(data.tender_details);
      setSummary(data.summary);
      if (data.summary.total && !data.summary.by_category.PQ) {
        const first = CATEGORIES.find((c) => data.summary.by_category[c.key]);
        if (first) setCategory(first.key);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [rfpId]);

  const stopPolling = () => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = null;
  };

  const pollRun = useCallback((runId: number) => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const latest: WorkflowRun = await api.getWorkflowRun(runId);
        setRun(latest);
        if (latest.status === 'COMPLETED' || latest.status === 'FAILED') {
          stopPolling();
          if (latest.status === 'COMPLETED') loadClauses();
        }
      } catch {
        // transient network error: keep polling
      }
    }, 2000);
  }, [loadClauses]);

  useEffect(() => {
    loadClauses();
    // Resume watching a run that was started before this page was opened.
    api.listWorkflowRuns({ rfp_id: rfpId }).then((runs: WorkflowRun[]) => {
      const active = runs.find((r) => r.status === 'PENDING' || r.status === 'RUNNING');
      if (active) {
        setRun(active);
        pollRun(active.id);
      }
    }).catch(() => {});
    return stopPolling;
  }, [rfpId, loadClauses, pollRun]);

  const running = run?.status === 'PENDING' || run?.status === 'RUNNING';

  const startAnalysis = async () => {
    const reviewed = summary ? summary.total - (summary.by_review_status.PENDING || 0) : 0;
    if (reviewed > 0 && !confirm(`Re-analysing replaces all clauses, including ${reviewed} you have reviewed. Continue?`)) return;
    setError(null);
    try {
      const started: WorkflowRun = await api.startWorkflow({ workflow: 'rfp-analysis', rfp_id: rfpId, params: { provider } });
      setRun(started);
      pollRun(started.id);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const saveClause = async (clause: Clause, changes: Partial<Clause>) => {
    setError(null);
    try {
      const updated: Clause = await api.updateClause(rfpId, clause.id, changes);
      setClauses((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
      setSummary((prev) => {
        if (!prev || changes.review_status === undefined || changes.review_status === clause.review_status) return prev;
        const counts = { ...prev.by_review_status };
        counts[clause.review_status] -= 1;
        counts[updated.review_status] = (counts[updated.review_status] || 0) + 1;
        return { ...prev, by_review_status: counts };
      });
      return true;
    } catch (err: any) {
      setError(err.message);
      return false;
    }
  };

  const addClause = async () => {
    if (!newClause?.requirement.trim()) return;
    try {
      await api.createClause(rfpId, {
        category,
        requirement: newClause.requirement,
        mandatory: newClause.mandatory === '' ? null : newClause.mandatory === 'true',
      });
      setNewClause(null);
      loadClauses();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const visible = clauses.filter((c) => c.category === category);
  const amendedFields: string[] = tenderDetails?._amended_fields || [];

  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <ListChecks className="w-5 h-5" />
            Tender Analysis
          </h2>
          {summary && summary.total > 0 && (
            <p className="text-sm text-gray-500 mt-1">
              {summary.total} requirements · {summary.mandatory_pq} mandatory PQ ·{' '}
              {summary.by_review_status.VERIFIED || 0} verified, {summary.by_review_status.REJECTED || 0} rejected,{' '}
              {summary.by_review_status.PENDING || 0} to review
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            disabled={running}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
            aria-label="AI provider"
          >
            <option value="gemini">Gemini</option>
            <option value="claude">Claude</option>
          </select>
          <Button onClick={startAnalysis} loading={running} disabled={!hasContent || running}>
            <ScanSearch className="w-4 h-4 mr-2" />
            {summary?.total ? 'Re-analyse Tender' : 'Analyse Tender'}
          </Button>
        </div>
      </div>

      {running && (
        <Card className="mb-4 flex items-center gap-3">
          <Spinner size="sm" />
          <span className="text-sm text-gray-700">{run?.current_step || 'Queued in n8n…'}</span>
        </Card>
      )}
      {run?.status === 'FAILED' && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800 flex gap-2">
          <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
          <span>Analysis failed: {run.error}</span>
        </div>
      )}
      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</div>
      )}
      {run?.status === 'COMPLETED' && (run.result?.warnings?.length ?? 0) > 0 && (
        <details className="mb-4 rounded-lg border border-yellow-200 bg-yellow-50 p-3 text-sm text-yellow-900">
          <summary className="cursor-pointer font-medium">{run.result?.warnings.length} extraction warning(s) to check</summary>
          <ul className="mt-2 list-disc pl-5 space-y-1">
            {run.result?.warnings.map((w: string, i: number) => <li key={i}>{w}</li>)}
          </ul>
        </details>
      )}

      {loading ? (
        <div className="py-8 flex justify-center"><Spinner /></div>
      ) : !summary?.total ? (
        !running && (
          <Card className="text-center py-10">
            <ScanSearch className="w-10 h-10 mx-auto text-gray-400 mb-3" />
            <h3 className="font-medium text-gray-900 mb-1">Not analysed yet</h3>
            <p className="text-sm text-gray-500">
              Extracts every PQ, TQ, scope, commercial and contractual requirement with page references,
              and applies corrigenda.
            </p>
          </Card>
        )
      ) : (
        <>
          {tenderDetails && (
            <Card className="mb-4">
              <dl className="grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-3 text-sm">
                {Object.entries(TENDER_LABELS).map(([key, label]) => (
                  <div key={key}>
                    <dt className="text-gray-500 flex items-center gap-1">
                      {label}
                      {amendedFields.includes(key) && <Badge variant="warning">Corrigendum</Badge>}
                    </dt>
                    <dd className="font-medium text-gray-900 break-words">{formatTenderValue(key, tenderDetails[key])}</dd>
                  </div>
                ))}
              </dl>
            </Card>
          )}

          <div className="flex flex-wrap gap-2 mb-3">
            {CATEGORIES.filter((c) => summary.by_category[c.key]).map((c) => (
              <button
                key={c.key}
                onClick={() => { setCategory(c.key); setExpanded(null); }}
                className={clsx(
                  'px-3 py-1.5 rounded-full text-sm font-medium transition-colors',
                  category === c.key ? 'bg-primary-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-200',
                )}
              >
                {c.label} <span className="opacity-75">{summary.by_category[c.key]}</span>
              </button>
            ))}
            {category === 'TQ' && (
              <span className="ml-auto self-center text-sm text-gray-500">Total marks: {summary.tq_total_marks}</span>
            )}
          </div>

          <Card className="p-0 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-left text-gray-500">
                <tr>
                  <th className="px-4 py-2 w-8" />
                  <th className="px-2 py-2 w-20">Code</th>
                  <th className="px-2 py-2">Requirement</th>
                  <th className="px-2 py-2 w-28">{category === 'TQ' ? 'Marks' : 'Type'}</th>
                  <th className="px-2 py-2 w-24">Source</th>
                  <th className="px-2 py-2 w-40">Review</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((c) => {
                  const open = expanded === c.id;
                  const threshold = describeThreshold(c);
                  return (
                    <React.Fragment key={c.id}>
                      <tr className={clsx('border-t border-gray-100 align-top', c.review_status === 'REJECTED' && 'opacity-60')}>
                        <td className="px-4 py-3">
                          <button
                            onClick={() => { setExpanded(open ? null : c.id); setDraft({}); }}
                            className="text-gray-400 hover:text-gray-700"
                            aria-label={open ? 'Collapse' : 'Expand'}
                          >
                            {open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                          </button>
                        </td>
                        <td className="px-2 py-3 font-mono text-xs text-gray-600">{c.clause_code}</td>
                        <td className="px-2 py-3">
                          <div className="text-gray-900">{c.requirement}</div>
                          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-gray-500">
                            {threshold && <span className="font-medium text-gray-700">{threshold}</span>}
                            {c.amended_by && <Badge variant="warning">Amended: {c.amended_by}</Badge>}
                            {c.edited && <Badge variant="default">Edited</Badge>}
                            {c.provider === 'manual' && <Badge variant="default">Added manually</Badge>}
                          </div>
                        </td>
                        <td className="px-2 py-3">
                          {category === 'TQ'
                            ? <span className="font-medium">{c.max_marks ?? '—'}</span>
                            : <MandatoryBadge value={c.mandatory} />}
                        </td>
                        <td className="px-2 py-3 text-xs text-gray-500">
                          {c.page_number ? `p. ${c.page_number}` : '—'}
                          {c.section_ref && <div>§ {c.section_ref}</div>}
                        </td>
                        <td className="px-2 py-3">
                          <div className="flex items-center gap-1">
                            <span className={clsx('px-2 py-0.5 rounded-full text-xs font-medium', STATUS_STYLES[c.review_status])}>
                              {c.review_status.toLowerCase()}
                            </span>
                            <button
                              onClick={() => saveClause(c, { review_status: c.review_status === 'VERIFIED' ? 'PENDING' : 'VERIFIED' })}
                              className={clsx('p-1 rounded hover:bg-green-50', c.review_status === 'VERIFIED' ? 'text-green-600' : 'text-gray-400')}
                              title="Verify"
                            >
                              <Check className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => saveClause(c, { review_status: c.review_status === 'REJECTED' ? 'PENDING' : 'REJECTED' })}
                              className={clsx('p-1 rounded hover:bg-red-50', c.review_status === 'REJECTED' ? 'text-red-600' : 'text-gray-400')}
                              title="Reject (not a real requirement)"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                      {open && (
                        <tr className="bg-gray-50 border-t border-gray-100">
                          <td />
                          <td colSpan={5} className="px-2 py-4">
                            <ClauseDetail
                              clause={c}
                              draft={draft}
                              setDraft={setDraft}
                              onSave={async () => {
                                if (await saveClause(c, draft)) setDraft({});
                              }}
                            />
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
            <div className="border-t border-gray-100 px-4 py-3">
              {newClause ? (
                <div className="flex flex-wrap gap-2 items-center">
                  <input
                    autoFocus
                    value={newClause.requirement}
                    onChange={(e) => setNewClause({ ...newClause, requirement: e.target.value })}
                    placeholder="Requirement the analysis missed"
                    className="flex-1 min-w-[240px] px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
                  />
                  <select
                    value={newClause.mandatory}
                    onChange={(e) => setNewClause({ ...newClause, mandatory: e.target.value })}
                    className="px-2 py-1.5 border border-gray-300 rounded-lg text-sm"
                  >
                    <option value="true">Mandatory</option>
                    <option value="false">Desirable</option>
                    <option value="">Not stated</option>
                  </select>
                  <Button size="sm" onClick={addClause}>Add</Button>
                  <Button size="sm" variant="ghost" onClick={() => setNewClause(null)}>Cancel</Button>
                </div>
              ) : (
                <button
                  onClick={() => setNewClause({ requirement: '', mandatory: 'true' })}
                  className="text-sm text-primary-600 hover:underline inline-flex items-center gap-1"
                >
                  <Plus className="w-4 h-4" /> Add a missed requirement
                </button>
              )}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}

function ClauseDetail({
  clause,
  draft,
  setDraft,
  onSave,
}: {
  clause: Clause;
  draft: Partial<Clause>;
  setDraft: (d: Partial<Clause>) => void;
  onSave: () => void;
}) {
  const value = <K extends keyof Clause>(key: K): Clause[K] => (key in draft ? (draft[key] as Clause[K]) : clause[key]);
  const numberField = (key: 'threshold_value' | 'min_count' | 'max_marks' | 'page_number', label: string) => (
    <label className="text-xs text-gray-500">
      {label}
      <input
        type="number"
        value={value(key) ?? ''}
        onChange={(e) => setDraft({ ...draft, [key]: e.target.value === '' ? null : Number(e.target.value) })}
        className="mt-1 block w-full px-2 py-1 border border-gray-300 rounded text-sm text-gray-900"
      />
    </label>
  );
  const dirty = Object.keys(draft).length > 0;

  return (
    <div className="space-y-4">
      {clause.source_text && (
        <blockquote className="border-l-4 border-primary-300 pl-3 text-sm italic text-gray-700">
          “{clause.source_text}”
          <span className="not-italic text-xs text-gray-400 ml-2">
            {clause.page_number ? `page ${clause.page_number}` : 'page unknown'}
            {clause.confidence !== null && ` · confidence ${Math.round(clause.confidence * 100)}%`}
          </span>
        </blockquote>
      )}
      {clause.scoring_rule && <p className="text-sm"><span className="text-gray-500">Scoring:</span> {clause.scoring_rule}</p>}
      {clause.evidence_required && clause.evidence_required.length > 0 && (
        <div className="text-sm">
          <span className="text-gray-500">Evidence to submit:</span>
          <ul className="list-disc pl-5">{clause.evidence_required.map((e, i) => <li key={i}>{e}</li>)}</ul>
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
        <label className="text-xs text-gray-500 col-span-2 md:col-span-6">
          Requirement
          <textarea
            value={value('requirement')}
            onChange={(e) => setDraft({ ...draft, requirement: e.target.value })}
            rows={2}
            className="mt-1 block w-full px-2 py-1 border border-gray-300 rounded text-sm text-gray-900"
          />
        </label>
        <label className="text-xs text-gray-500">
          Mandatory
          <select
            value={value('mandatory') === null ? '' : String(value('mandatory'))}
            onChange={(e) => setDraft({ ...draft, mandatory: e.target.value === '' ? null : e.target.value === 'true' })}
            className="mt-1 block w-full px-2 py-1 border border-gray-300 rounded text-sm text-gray-900"
          >
            <option value="true">Mandatory</option>
            <option value="false">Desirable</option>
            <option value="">Not stated</option>
          </select>
        </label>
        {numberField('threshold_value', `Threshold${clause.threshold_unit ? ` (${clause.threshold_unit})` : ''}`)}
        {numberField('min_count', 'Min count')}
        {numberField('max_marks', 'Max marks')}
        {numberField('page_number', 'Page')}
        <label className="text-xs text-gray-500">
          Section
          <input
            value={value('section_ref') ?? ''}
            onChange={(e) => setDraft({ ...draft, section_ref: e.target.value || null })}
            className="mt-1 block w-full px-2 py-1 border border-gray-300 rounded text-sm text-gray-900"
          />
        </label>
        <label className="text-xs text-gray-500 col-span-2 md:col-span-6">
          Reviewer notes
          <input
            value={value('reviewer_notes') ?? ''}
            onChange={(e) => setDraft({ ...draft, reviewer_notes: e.target.value || null })}
            className="mt-1 block w-full px-2 py-1 border border-gray-300 rounded text-sm text-gray-900"
          />
        </label>
      </div>
      <div className="flex gap-2">
        <Button size="sm" onClick={onSave} disabled={!dirty}>Save changes</Button>
        <Button size="sm" variant="ghost" onClick={() => setDraft({})} disabled={!dirty}>Discard</Button>
      </div>
    </div>
  );
}
