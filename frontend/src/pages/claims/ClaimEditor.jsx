import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useNavigate, useParams } from 'react-router-dom';

import ProcedureCodeInput from './ProcedureCodeInput';
import { claimSchema, createEmptyLine, defaultClaimValues } from './claimSchema';
import FindingsWorkbench, { makeFindings } from './FindingsWorkbench';
import { useAuth } from '../../auth/AuthContext';
import { API_BASE_URL } from '../../api/api';
import { ErrorState } from '../../components/shared/ErrorState';
import { LoadingState } from '../../components/shared/LoadingState';

const gridColumns = [
  { key: 'procedure_code', label: 'Procedure', className: 'min-w-[180px]' },
  { key: 'tooth_number', label: 'Tooth', className: 'min-w-[110px]' },
  { key: 'surface', label: 'Surface', className: 'min-w-[110px]' },
  { key: 'charge_amount', label: 'Charge', className: 'min-w-[140px]' },
];

function cloneClaim(value) {
  return JSON.parse(JSON.stringify(value ?? defaultClaimValues));
}

function toMoney(value) {
  const number = Number.parseFloat(String(value ?? '').replace(/[^0-9.-]/g, ''));

  if (!Number.isFinite(number)) {
    return '0.00';
  }

  return Number(number).toFixed(2);
}

function getLineTotal(lines = []) {
  return lines.reduce((sum, line) => {
    const value = Number.parseFloat(String(line?.charge_amount ?? '').replace(/[^0-9.-]/g, ''));

    if (!Number.isFinite(value)) {
      return sum;
    }

    return sum + value;
  }, 0);
}

function parseErrorMessage(error) {
  if (error?.message) {
    return error.message;
  }

  if (error?.body?.detail) {
    return error.body.detail;
  }

  return 'Unable to save the claim right now.';
}

function normalizeServerClaim(claim) {
  return {
    patient_id: claim.patient_id ?? '',
    provider_id: claim.provider_id ?? '',
    payer_id: claim.payer_id ?? '',
    service_date_from: claim.service_date_from ?? '',
    service_date_to: claim.service_date_to ?? '',
    total_amount: claim.total_amount ?? '',
    is_secondary_claim: claim.is_secondary_claim ?? false,
    narrative: '',
    authorization_number: '',
    attachments: [],
  };
}

function normalizeServerLines(lines) {
  if (!Array.isArray(lines) || lines.length === 0) {
    return [createEmptyLine()];
  }

  return lines.map((line) => ({
    procedure_code: line.procedure_code ?? '',
    tooth_number: line.tooth_number ?? '',
    surface: line.surface ?? '',
    charge_amount: line.charge_amount ?? '',
  }));
}

function ClaimEditor() {
  const { claimId } = useParams();
  const navigate = useNavigate();
  const { accessToken } = useAuth();

  const form = useForm({
    resolver: zodResolver(claimSchema),
    defaultValues: cloneClaim(defaultClaimValues),
    mode: 'onChange',
  });

  const { append, fields, remove } = useFieldArray({
    control: form.control,
    name: 'lines',
  });

  const [isLoading, setIsLoading] = useState(Boolean(claimId));
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState('');
  const [statusMessage, setStatusMessage] = useState('');
  const [lastSavedValues, setLastSavedValues] = useState(() => cloneClaim(defaultClaimValues));
  const [dispositions, setDispositions] = useState({});
  const [showSubmitConfirm, setShowSubmitConfirm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [attachments, setAttachments] = useState([]);
  const [selectedDocType, setSelectedDocType] = useState('attachment');
  const [selectedFile, setSelectedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isScrubbing, setIsScrubbing] = useState(false);
  const [scrubResult, setScrubResult] = useState(null);
  const [claimMeta, setClaimMeta] = useState(null);
  const cellRefs = useRef({});

  const watchedLines = form.watch('lines') ?? defaultClaimValues.lines;
  const watchedValues = form.watch();
  const currentTotal = useMemo(() => getLineTotal(watchedLines), [watchedLines]);
  const blockingFindings = makeFindings(watchedValues).filter((finding) => finding.severity === 'ERROR' && !dispositions[finding.code]).length;

  function authenticatedFetchRef(path, options = {}) {
    const headers = new Headers(options.headers || {});
    if (accessToken) {
      headers.set('Authorization', `Bearer ${accessToken}`);
    }
    if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }
    return fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  }

  const authenticatedFetch = useCallback(authenticatedFetchRef, [accessToken]);

  useEffect(() => {
    const nextTotal = toMoney(currentTotal);
    const currentValue = form.getValues('total_amount');

    if (currentValue !== nextTotal) {
      form.setValue('total_amount', nextTotal, {
        shouldDirty: true,
        shouldTouch: true,
      });
    }
  }, [currentTotal, form]);

  useEffect(() => {
    if (!claimId) {
      const initial = cloneClaim(defaultClaimValues);
      form.reset(initial);
      setLastSavedValues(initial);
      setIsLoading(false);
      return;
    }

    let isMounted = true;

    async function loadClaim() {
      setIsLoading(true);
      setSaveError('');

      try {
        const [claimResponse, linesResponse, attachmentsResponse] = await Promise.all([
          authenticatedFetch(`/api/v1/claims/${claimId}`),
          authenticatedFetch(`/api/v1/claims/${claimId}/lines`),
          authenticatedFetch(`/api/v1/claims/${claimId}/attachments`),
        ]);

        if (!claimResponse.ok || !linesResponse.ok || !attachmentsResponse.ok) {
          throw new Error('Unable to load the claim.');
        }

        const claim = await claimResponse.json();
        const lines = await linesResponse.json();
        const serverAttachments = await attachmentsResponse.json();

        if (!isMounted) {
          return;
        }

        const normalized = {
          ...normalizeServerClaim(claim),
          attachments: serverAttachments.map((attachment) => ({
            name: attachment.file_type,
            type: attachment.file_type,
            size: 0,
          })),
          lines: normalizeServerLines(lines),
        };

        form.reset(normalized);
        setLastSavedValues(cloneClaim(normalized));
        setAttachments(serverAttachments);
        setClaimMeta({
          id: claim.id,
          claim_number: claim.claim_number,
          status: claim.status,
          readiness_score: claim.readiness_score,
          etag: claimResponse.headers.get('etag'),
        });
        setScrubResult(claim.findings_summary ?? []);
        setStatusMessage('Claim loaded');
      } catch (error) {
        if (isMounted) {
          setSaveError(parseErrorMessage(error));
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadClaim();

    return () => {
      isMounted = false;
    };
  }, [claimId, form, accessToken, authenticatedFetch]);

  function focusCell(rowIndex, columnIndex) {
    const key = `${rowIndex}-${columnIndex}`;
    const field = cellRefs.current[key];

    if (field) {
      field.focus();
      field.select?.();
    }
  }

  function moveFocus(event, rowIndex, columnKey) {
    const columnIndex = gridColumns.findIndex((column) => column.key === columnKey);
    const lastColumnIndex = gridColumns.length - 1;

    if (event.key === 'ArrowRight' || (event.key === 'Tab' && !event.shiftKey)) {
      event.preventDefault();
      const nextColumnIndex = columnIndex >= lastColumnIndex ? 0 : columnIndex + 1;
      const nextRowIndex = columnIndex >= lastColumnIndex ? rowIndex + 1 : rowIndex;
      focusCell(nextRowIndex, nextColumnIndex);
      return;
    }

    if (event.key === 'ArrowLeft' || (event.key === 'Tab' && event.shiftKey)) {
      event.preventDefault();
      const nextColumnIndex = columnIndex <= 0 ? lastColumnIndex : columnIndex - 1;
      const nextRowIndex = columnIndex <= 0 ? Math.max(0, rowIndex - 1) : rowIndex;
      focusCell(nextRowIndex, nextColumnIndex);
      return;
    }

    if (event.key === 'ArrowDown' || event.key === 'Enter') {
      event.preventDefault();
      const nextRowIndex = rowIndex + 1;
      focusCell(nextRowIndex, columnIndex);
      return;
    }

    if (event.key === 'ArrowUp') {
      event.preventDefault();
      focusCell(Math.max(0, rowIndex - 1), columnIndex);
    }
  }

  async function handleSave(values) {
    const previousValues = cloneClaim(lastSavedValues);
    const optimisticValues = {
      ...values,
      total_amount: toMoney(getLineTotal(values.lines)),
    };

    form.reset(optimisticValues);
    setLastSavedValues(cloneClaim(optimisticValues));
    setStatusMessage('Saving changes…');
    setSaveError('');
    setIsSaving(true);

    try {
      const payload = {
        patient_id: optimisticValues.patient_id,
        provider_id: optimisticValues.provider_id,
        payer_id: optimisticValues.payer_id || null,
        service_date_from: optimisticValues.service_date_from,
        service_date_to: optimisticValues.service_date_to,
        total_amount: optimisticValues.total_amount,
        is_secondary_claim: optimisticValues.is_secondary_claim,
      };

      let response;

      if (claimId) {
        const headers = { 'Content-Type': 'application/json' };
        if (claimMeta?.etag) {
          headers['If-Match'] = claimMeta.etag;
        }
        response = await authenticatedFetch(`/api/v1/claims/${claimId}`, {
          method: 'PUT',
          headers,
          body: JSON.stringify(payload),
        });
      } else {
        response = await authenticatedFetch('/api/v1/claims', {
          method: 'POST',
          body: JSON.stringify(payload),
        });
      }

      if (!response.ok) {
        throw new Error('The claim could not be saved.');
      }

      const savedClaim = await response.json();

      if (claimId) {
        const linesPayload = values.lines.map((line) => ({
          procedure_code: line.procedure_code,
          tooth_number: line.tooth_number || null,
          surface: line.surface || null,
          charge_amount: toMoney(line.charge_amount),
        }));
        const linesResponse = await authenticatedFetch(`/api/v1/claims/${claimId}/lines`, {
          method: 'PUT',
          body: JSON.stringify(linesPayload),
        });

        if (!linesResponse.ok) {
          throw new Error('Claim saved, but line items could not be saved.');
        }
      }

      const nextValues = {
        ...normalizeServerClaim(savedClaim),
        lines: values.lines.map((line) => ({
          procedure_code: line.procedure_code,
          tooth_number: line.tooth_number ?? '',
          surface: line.surface ?? '',
          charge_amount: line.charge_amount,
        })),
      };

      form.reset(nextValues);
      setLastSavedValues(cloneClaim(nextValues));
      setClaimMeta({
        id: savedClaim.id,
        claim_number: savedClaim.claim_number,
        status: savedClaim.status,
        readiness_score: savedClaim.readiness_score,
        etag: response.headers.get('etag'),
      });
      setScrubResult(savedClaim.findings_summary ?? []);
      setStatusMessage(claimId ? 'Claim updated' : 'Claim created');

      if (!claimId && savedClaim.id) {
        navigate(`/claims/${savedClaim.id}`, { replace: true });
      }
    } catch (error) {
      form.reset(previousValues);
      setSaveError(parseErrorMessage(error));
      setStatusMessage('Changes rolled back');
    } finally {
      setIsSaving(false);
    }
  }

  async function uploadAttachment() {
    if (!selectedFile || !claimId) {
      return;
    }
    setIsUploading(true);
    setSaveError('');
    try {
      const body = new FormData();
      body.append('file', selectedFile);
      body.append('doc_type', selectedDocType);

      const response = await authenticatedFetch(`/api/v1/claims/${claimId}/attachments`, {
        method: 'POST',
        body,
      });

      if (!response.ok) {
        throw new Error('The attachment could not be uploaded.');
      }

      const attachment = await response.json();
      setAttachments((previous) => [attachment, ...previous]);
      form.setValue(
        'attachments',
        [...(form.getValues('attachments') ?? []), { name: selectedFile.name, type: selectedFile.type, size: selectedFile.size }],
        { shouldDirty: true, shouldTouch: true },
      );
      setSelectedFile(null);
      setStatusMessage('Attachment uploaded');
    } catch (error) {
      setSaveError(parseErrorMessage(error));
    } finally {
      setIsUploading(false);
    }
  }

  async function runScrub() {
    if (!claimId) {
      return;
    }
    setIsScrubbing(true);
    setSaveError('');
    try {
      const response = await authenticatedFetch(`/api/v1/claims/${claimId}/scrub`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error('Unable to scrub the claim.');
      }

      const scrubbed = await response.json();
      setScrubResult(scrubbed.findings_summary ?? []);
      setClaimMeta((meta) => ({
        ...meta,
        status: scrubbed.status,
        readiness_score: scrubbed.readiness_score,
        etag: response.headers.get('etag') ?? meta?.etag,
      }));
      setStatusMessage('Claim scrubbed — findings updated');
    } catch (error) {
      setSaveError(parseErrorMessage(error));
    } finally {
      setIsScrubbing(false);
    }
  }

  function goToField(path) {
    const target = document.querySelector(`[data-path="${path}"]`);
    target?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    target?.focus?.();
    target?.classList.add('ring-2', 'ring-amber-400');
    window.setTimeout(() => target?.classList.remove('ring-2', 'ring-amber-400'), 1800);
  }

  function applyFix(fix) {
    Object.entries(fix).forEach(([path, value]) => form.setValue(path, value, { shouldDirty: true, shouldTouch: true, shouldValidate: true }));
  }

  function recordDisposition(finding, disposition, reason) {
    const entry = { disposition, reason, actor: 'current-user', at: new Date().toISOString() };
    setDispositions((previous) => ({ ...previous, [finding.code]: entry }));
  }

  async function submitClaim() {
    setIsSubmitting(true);
    try {
      const response = await authenticatedFetch(`/api/v1/claims/${claimId}/submit`, {
        method: 'POST',
        body: JSON.stringify({ dispositions }),
      });
      if (!response.ok) throw new Error('Unable to submit claim.');
      setStatusMessage('Claim submitted and moved to Submitted.');
      setShowSubmitConfirm(false);
      navigate('/claims');
    } catch (error) {
      setSaveError(parseErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleGridAddRow() {
    append(createEmptyLine());
    requestAnimationFrame(() => {
      const nextIndex = fields.length;
      focusCell(nextIndex, 0);
    });
  }

  const onSubmit = form.handleSubmit(handleSave);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.2em] text-slate-500">
            Claim editor
          </p>
          <h1 className="mt-2 text-3xl font-bold text-slate-900">
            {claimMeta?.claim_number ? `Claim ${claimMeta.claim_number}` : 'Draft claim'}
          </h1>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to="/claims"
            className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Back to claims
          </Link>
          <button
            type="button"
            onClick={runScrub}
            disabled={!claimId || isScrubbing || isSaving || isLoading}
            className="rounded-md bg-indigo-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-600 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {isScrubbing ? 'Scrubbing…' : 'Run scrub'}
          </button>
          <button
            type="button"
            onClick={onSubmit}
            disabled={isSaving || isLoading}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {isSaving ? 'Saving…' : 'Save changes'}
          </button>
          <button type="button" title={blockingFindings ? 'Resolve or override all ERROR findings before submitting.' : 'Submit this clean claim.'} onClick={() => setShowSubmitConfirm(true)} disabled={!claimId || isSaving || isLoading || blockingFindings > 0} className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-300">Submit</button>
        </div>
      </div>

      {saveError ? (
        <ErrorState error={saveError} onRetry={() => {}} />
      ) : null}

      {statusMessage ? (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700 animate-in fade-in duration-300">
          {statusMessage}
        </div>
      ) : null}

      {isLoading ? (
        <div className="rounded-xl border border-slate-200 bg-white p-12 text-center shadow-sm">
          <LoadingState message="Loading claim details..." />
        </div>
      ) : (
        <div className="grid gap-6 xl:grid-cols-[280px_minmax(0,1fr)_300px]">
          <aside className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Header</h2>
            </div>

            <div className="space-y-4">
              <div>
                <label htmlFor="patient_id" className="mb-1 block text-sm font-medium text-slate-700">Patient</label>
                <input
                  id="patient_id"
                  data-path="patient_id"
                  {...form.register('patient_id')}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                  placeholder="Patient ID"
                />
                {form.formState.errors.patient_id ? (
                  <p className="mt-1 text-xs text-red-600">{form.formState.errors.patient_id.message}</p>
                ) : null}
              </div>

              <div>
                <label htmlFor="provider_id" className="mb-1 block text-sm font-medium text-slate-700">Provider</label>
                <input
                  id="provider_id"
                  data-path="provider_id"
                  {...form.register('provider_id')}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                  placeholder="Provider ID"
                />
              </div>

              <div>
                <label htmlFor="payer_id" className="mb-1 block text-sm font-medium text-slate-700">Payer</label>
                <input
                  id="payer_id"
                  data-path="payer_id"
                  {...form.register('payer_id')}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                  placeholder="Optional payer"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="service_date_from" className="mb-1 block text-sm font-medium text-slate-700">From</label>
                  <input
                    id="service_date_from"
                    type="date"
                    {...form.register('service_date_from')}
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                  />
                </div>

                <div>
                  <label htmlFor="service_date_to" className="mb-1 block text-sm font-medium text-slate-700">To</label>
                  <input
                    id="service_date_to"
                    type="date"
                    {...form.register('service_date_to')}
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="total_amount" className="mb-1 block text-sm font-medium text-slate-700">Total amount</label>
                <input
                  id="total_amount"
                  data-path="total_amount"
                  {...form.register('total_amount')}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                  placeholder="0.00"
                />
              </div>

              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
                  <input
                    id="is_secondary_claim"
                    data-path="is_secondary_claim"
                    type="checkbox"
                    {...form.register('is_secondary_claim')}
                    className="h-4 w-4 rounded border-slate-300 text-slate-900 focus:ring-slate-500"
                  />
                  Secondary claim (COB)
                </label>
                <p className="mt-1 pl-6 text-xs text-slate-500">
                  Mark if this claim is being submitted to a second payer.
                </p>
              </div>

              <div>
                <label htmlFor="authorization_number" className="mb-1 block text-sm font-medium text-slate-700">Authorisation number</label>
                <input id="authorization_number" data-path="authorization_number" {...form.register('authorization_number')} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Required for some procedures" />
              </div>
              <div>
                <label htmlFor="narrative" className="mb-1 block text-sm font-medium text-slate-700">Clinical narrative</label>
                <textarea id="narrative" data-path="narrative" {...form.register('narrative')} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" rows="3" placeholder="Clinical necessity" />
              </div>
            </div>

            <div className="mt-4 border-t border-slate-200 pt-4">
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Attachments</h2>

              <div className="space-y-3">
                <div>
                  <label htmlFor="doc_type_select" className="mb-1 block text-sm font-medium text-slate-700">Document type</label>
                  <select
                    id="doc_type_select"
                    value={selectedDocType}
                    onChange={(event) => setSelectedDocType(event.target.value)}
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                  >
                    <option value="attachment">General attachment</option>
                    <option value="x-ray">X-ray</option>
                    <option value="primary_eob">EOB (primary payer)</option>
                    <option value="secondary_eob">EOB (secondary payer)</option>
                    <option value="narrative">Narrative</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="attachment_file" className="mb-1 block text-sm font-medium text-slate-700">File</label>
                  <input
                    id="attachment_file"
                    type="file"
                    accept="application/pdf,image/jpeg,image/png"
                    onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                    className="w-full text-xs"
                  />
                </div>

                <button
                  type="button"
                  onClick={uploadAttachment}
                  disabled={!selectedFile || !claimId || isUploading}
                  className="w-full rounded-md bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-600 disabled:cursor-not-allowed disabled:bg-slate-300"
                >
                  {isUploading ? 'Uploading…' : 'Upload attachment'}
                </button>

                <ul className="space-y-2">
                  {attachments.map((attachment) => (
                    <li key={attachment.id} className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
                      <div className="flex items-center justify-between gap-2">
                        <span className="rounded bg-slate-200 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-700">
                          {attachment.doc_type}
                        </span>
                        <span className="text-[10px] text-slate-400">
                          {new Date(attachment.created_at).toLocaleString()}
                        </span>
                      </div>
                      <p className="mt-1 text-[11px] text-slate-600">{attachment.file_type}</p>
                      <p className="mt-1 line-clamp-3 text-[11px] text-slate-500">
                        {attachment.ocr_text ? `OCR: ${attachment.ocr_text}` : 'No OCR text'}
                      </p>
                    </li>
                  ))}
                  {attachments.length === 0 ? (
                    <li className="text-xs text-slate-400">No attachments uploaded yet.</li>
                  ) : null}
                </ul>
              </div>
            </div>
          </aside>

          <main className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Line items</h2>
              </div>

              <button
                type="button"
                onClick={handleGridAddRow}
                className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
              >
                Add line
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-full border-separate border-spacing-0 text-left">
                <thead>
                  <tr>
                    {gridColumns.map((column) => (
                      <th
                        key={column.key}
                        className="border-b border-slate-200 bg-slate-50 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-600"
                      >
                        {column.label}
                      </th>
                    ))}
                    <th className="w-10 border-b border-slate-200 bg-slate-50 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-600">
                      Action
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {fields.map((field, rowIndex) => (
                    <tr key={field.id} className="align-top">
                      {gridColumns.map((column) => {
                        const columnIndex = gridColumns.findIndex((item) => item.key === column.key);

                        if (column.key === 'procedure_code') {
                          return (
                            <td key={`${field.id}-${column.key}`} className="border-b border-slate-200 px-2 py-2">
                              <ProcedureCodeInput
                                value={form.watch(`lines.${rowIndex}.${column.key}`) ?? ''}
                                onChange={(nextValue) => {
                                  form.setValue(`lines.${rowIndex}.${column.key}`, nextValue, {
                                    shouldDirty: true,
                                    shouldTouch: true,
                                  });
                                }}
                                onKeyDown={(event) => moveFocus(event, rowIndex, column.key)}
                                inputRef={(node) => {
                                  if (node) {
                                    cellRefs.current[`${rowIndex}-${columnIndex}`] = node;
                                  }
                                }}
                              />
                            </td>
                          );
                        }

                        return (
                          <td key={`${field.id}-${column.key}`} className="border-b border-slate-200 px-2 py-2">
                            <input
                              data-path={`lines.${rowIndex}.${column.key}`}
                              ref={(node) => {
                                if (node) {
                                  cellRefs.current[`${rowIndex}-${columnIndex}`] = node;
                                }
                              }}
                              {...form.register(`lines.${rowIndex}.${column.key}`)}
                              onKeyDown={(event) => moveFocus(event, rowIndex, column.key)}
                              className="w-full rounded-md border border-slate-300 px-2 py-2 text-sm outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                              placeholder={column.label}
                            />
                          </td>
                        );
                      })}

                      <td className="border-b border-slate-200 px-2 py-2">
                        <button
                          type="button"
                          onClick={() => remove(rowIndex)}
                          disabled={fields.length <= 1}
                          className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </main>

          <div className="space-y-6">
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Backend scrub</h2>
              </div>

              <div className="space-y-2 text-xs text-slate-600">
                <p>
                  Status: <span className="font-medium text-slate-800">{claimMeta?.status ?? '—'}</span>
                </p>
                <p>
                  Readiness score: <span className="font-medium text-slate-800">{claimMeta?.readiness_score ?? '—'}</span>
                </p>
                <p>
                  Claim number: <span className="font-medium text-slate-800">{claimMeta?.claim_number ?? '—'}</span>
                </p>
              </div>

              {Array.isArray(scrubResult) && scrubResult.length > 0 ? (
                <ul className="mt-4 space-y-2">
                  {scrubResult.map((finding, index) => (
                    <li key={`${finding.rule_id ?? finding.code ?? 'finding'}-${index}`} className="rounded-md border border-slate-200 px-3 py-2 text-xs">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-semibold text-slate-800">{finding.rule_id ?? finding.code ?? 'Finding'}</span>
                        <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${finding.severity === 'ERROR' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>
                          {finding.severity}
                        </span>
                      </div>
                      <p className="mt-1 text-slate-600">{finding.summary ?? finding.message ?? ''}</p>
                    </li>
                  ))}
                </ul>
              ) : Array.isArray(scrubResult) ? (
                <p className="mt-4 text-xs text-emerald-700">No findings after the last scrub.</p>
              ) : null}
            </div>

            <FindingsWorkbench values={watchedValues} onGoTo={goToField} onFix={applyFix} dispositions={dispositions} onDisposition={recordDisposition} />
          </div>
        </div>
      )}
      {showSubmitConfirm ? <div role="dialog" aria-label="Submit claim confirmation" className="fixed inset-0 z-50 grid place-items-center bg-slate-900/40 p-4"><div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl"><h2 className="text-lg font-bold">Submit this claim?</h2><p className="mt-2 text-sm text-slate-600">This will transition the claim from Draft to Submitted.</p><div className="mt-5 flex justify-end gap-3"><button type="button" onClick={() => setShowSubmitConfirm(false)} className="text-sm underline">Cancel</button><button type="button" onClick={submitClaim} disabled={isSubmitting} className="rounded bg-emerald-700 px-4 py-2 text-sm font-semibold text-white">{isSubmitting ? 'Submitting…' : 'Confirm submit'}</button></div></div></div> : null}
    </div>
  );
}

export default ClaimEditor;