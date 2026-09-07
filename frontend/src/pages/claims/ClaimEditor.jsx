import { useEffect, useMemo, useRef, useState } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useNavigate, useParams } from 'react-router-dom';

import ProcedureCodeInput from './ProcedureCodeInput';
import { claimSchema, createEmptyLine, defaultClaimValues } from './claimSchema';

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

function ClaimEditor() {
  const { claimId } = useParams();
  const navigate = useNavigate();

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
  const cellRefs = useRef({});

  const watchedLines = form.watch('lines') ?? defaultClaimValues.lines;
  const currentTotal = useMemo(() => getLineTotal(watchedLines), [watchedLines]);

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
        const response = await fetch(`/v1/claims/${claimId}`);

        if (!response.ok) {
          throw new Error('Unable to load the claim.');
        }

        const claim = await response.json();
        const normalized = {
          patient_id: claim.patient_id ?? '',
          provider_id: claim.provider_id ?? '',
          payer_id: claim.payer_id ?? '',
          service_date_from: claim.service_date_from ?? '',
          service_date_to: claim.service_date_to ?? '',
          total_amount: claim.total_amount ?? toMoney(getLineTotal(claim.lines ?? [])),
          lines: Array.isArray(claim.lines) && claim.lines.length > 0
            ? claim.lines.map((line) => ({
                procedure_code: line.procedure_code ?? '',
                tooth_number: line.tooth_number ?? '',
                surface: line.surface ?? '',
                charge_amount: line.charge_amount ?? '',
              }))
            : [createEmptyLine()],
        };

        if (isMounted) {
          form.reset(normalized);
          setLastSavedValues(cloneClaim(normalized));
          setStatusMessage('Claim loaded');
        }
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
  }, [claimId, form]);

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
      };

      let response;

      if (claimId) {
        response = await fetch(`/v1/claims/${claimId}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      } else {
        response = await fetch('/v1/claims', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      }

      if (!response.ok) {
        throw new Error('The claim could not be saved.');
      }

      const savedClaim = await response.json();
      const nextValues = {
        patient_id: savedClaim.patient_id ?? optimisticValues.patient_id,
        provider_id: savedClaim.provider_id ?? optimisticValues.provider_id,
        payer_id: savedClaim.payer_id ?? optimisticValues.payer_id ?? '',
        service_date_from: savedClaim.service_date_from ?? optimisticValues.service_date_from,
        service_date_to: savedClaim.service_date_to ?? optimisticValues.service_date_to,
        total_amount: savedClaim.total_amount ?? optimisticValues.total_amount,
        lines: values.lines.map((line) => ({
          procedure_code: line.procedure_code,
          tooth_number: line.tooth_number ?? '',
          surface: line.surface ?? '',
          charge_amount: line.charge_amount,
        })),
      };

      form.reset(nextValues);
      setLastSavedValues(cloneClaim(nextValues));
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
          <h1 className="mt-2 text-3xl font-bold text-slate-900">Draft claim</h1>
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
            onClick={onSubmit}
            disabled={isSaving || isLoading}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {isSaving ? 'Saving…' : 'Save changes'}
          </button>
        </div>
      </div>

      {saveError ? (
        <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {saveError}
        </div>
      ) : null}

      {statusMessage ? (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
          {statusMessage}
        </div>
      ) : null}

      {isLoading ? (
        <div className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-600 shadow-sm">
          Loading claim…
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
                  {...form.register('provider_id')}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                  placeholder="Provider ID"
                />
              </div>

              <div>
                <label htmlFor="payer_id" className="mb-1 block text-sm font-medium text-slate-700">Payer</label>
                <input
                  id="payer_id"
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
                  {...form.register('total_amount')}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                  placeholder="0.00"
                />
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

          <aside className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Validation</h2>

            <div className="mt-4 space-y-3">
              <div className="rounded-md bg-slate-100 p-3">
                <div className="text-xs uppercase tracking-wide text-slate-500">Readiness</div>
                <div className="mt-2 text-2xl font-semibold text-slate-900">{claimId ? '82%' : 'New'}</div>
              </div>

              <div className="rounded-md border border-slate-200 bg-white p-3">
                <ul className="space-y-2 text-sm text-slate-600">
                  <li>• Missing payer mapping</li>
                  <li>• Procedure code still needs review</li>
                  <li>• Totals align with line entries</li>
                </ul>
              </div>
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}

export default ClaimEditor;
