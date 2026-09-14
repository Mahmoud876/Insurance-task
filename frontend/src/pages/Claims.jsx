import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { fetchClaims } from "../api/api";
import { StatusBadge } from "../components/shared/StatusBadge";
import { ScorePill } from "../components/shared/ScorePill";
import { EmptyState, LoadingState, ErrorState } from "../components/shared";

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "DRAFT", label: "Draft" },
  { value: "SUBMITTED", label: "Submitted" },
  { value: "ACCEPTED", label: "Accepted" },
  { value: "REJECTED", label: "Rejected" },
  { value: "PAID", label: "Paid" },
];


function formatDate(value) {
  if (!value) {
    return "—";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(date);
}

function formatMoney(value) {
  if (value === null || value === undefined) {
    return "—";
  }

  const number = Number(value);

  if (Number.isNaN(number)) {
    return "—";
  }

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(number);
}

function getFindingsSummary(findings) {
  if (!findings || findings.length === 0) {
    return "No findings";
  }

  return findings
    .map((finding) => {
      if (typeof finding === "string") {
        return finding;
      }

      if (finding.summary) {
        return finding.summary;
      }

      if (finding.message) {
        return finding.message;
      }

      if (finding.description) {
        return finding.description;
      }

      return JSON.stringify(finding);
    })
    .join("; ");
}

function Claims() {
  const {
    authenticated,
    initialized,
    accessToken,
    login,
  } = useAuth();

  const [claims, setClaims] = useState([]);
  const [nextCursor, setNextCursor] = useState(null);
  const [hasMore, setHasMore] = useState(false);

  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);

  const [patientSearch, setPatientSearch] = useState("");
  const [status, setStatus] = useState("");
  const [payerId, setPayerId] = useState("");
  const [serviceDateFrom, setServiceDateFrom] = useState("");
  const [serviceDateTo, setServiceDateTo] = useState("");
  const [selectedClaimIds, setSelectedClaimIds] = useState([]);
  const [isScrubbing, setIsScrubbing] = useState(false);

  async function bulkScrub() {
    if (!selectedClaimIds.length) return;
    setIsScrubbing(true);
    try {
      await Promise.all(selectedClaimIds.map((id) => fetch(`/v1/claims/${id}/scrub`, { method: "POST" })));
      setSelectedClaimIds([]);
      await loadClaims();
      // Add status message for aria-live
      setScrubStatus(`Successfully scrubbed ${selectedClaimIds.length} claims.`);
    } finally {
      setIsScrubbing(false);
    }
  }

  const [scrubStatus, setScrubStatus] = useState("");

  useEffect(() => {
    if (scrubStatus) {
      const timer = setTimeout(() => setScrubStatus(""), 5000);
      return () => clearTimeout(timer);
    }
  }, [scrubStatus]);

  const loadClaims = useCallback(
    async ({ cursor = null, append = false } = {}) => {
      if (!accessToken) {
        return;
      }

      if (append) {
        setLoadingMore(true);
      } else {
        setLoading(true);
        setError(null);
      }

      try {
        const result = await fetchClaims(accessToken, {
          cursor,
          limit: 25,
          patientSearch,
          status,
          payerId,
          serviceDateFrom,
          serviceDateTo,
        });

        const items = result?.items ?? [];

        if (append) {
          setClaims((previous) => [
            ...previous,
            ...items,
          ]);
        } else {
          setClaims(items);
        }

        setNextCursor(result?.nextCursor ?? null);
        setHasMore(Boolean(result?.hasMore));
      } catch (err) {
        console.error("Failed to load claims:", err);

        if (!append) {
          setClaims([]);
        }

        setError(
          err?.response?.body?.detail ||
            err?.message ||
            "Unable to load claims."
        );
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [
      accessToken,
      patientSearch,
      status,
      payerId,
      serviceDateFrom,
      serviceDateTo,
    ]
  );

  useEffect(() => {
    if (
      initialized &&
      authenticated &&
      accessToken
    ) {
      loadClaims();
    }
  }, [
    initialized,
    authenticated,
    accessToken,
    loadClaims,
  ]);

  function applyFilters(event) {
    event.preventDefault();

    loadClaims({
      cursor: null,
      append: false,
    });
  }

  function clearFilters() {
    setPatientSearch("");
    setStatus("");
    setPayerId("");
    setServiceDateFrom("");
    setServiceDateTo("");
  }

  if (!initialized) {
    return (
      <div className="p-6">
        <div className="h-8 w-48 animate-pulse rounded bg-gray-200" />
      </div>
    );
  }

  if (!authenticated) {
    return (
      <div className="flex min-h-[400px] flex-col items-center justify-center gap-4 p-6">
        <h1 className="text-2xl font-semibold">
          Claims
        </h1>

        <p className="text-gray-500">
          Please sign in to view claims.
        </p>

        <button
          type="button"
          onClick={login}
          className="rounded-md bg-black px-4 py-2 text-white hover:opacity-90"
        >
          Sign in
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-7">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">
            Claims
          </h1>

          <p className="mt-2 text-sm text-slate-500">
            Review claims, readiness, and validation findings.
          </p>
        </div>

        <Link
          to="/claims/new"
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
        >
          New claim
        </Link>
        <button type="button" disabled={!selectedClaimIds.length || isScrubbing} onClick={bulkScrub} title="Re-run validation on selected claims" className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium disabled:opacity-40">{isScrubbing ? "Scrubbing…" : `Bulk scrub${selectedClaimIds.length ? ` (${selectedClaimIds.length})` : ""}`}</button>
      </div>
      <div className="sr-only" aria-live="polite">{scrubStatus}</div>

      <form
        onSubmit={applyFilters}
        className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
      >
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
          <div>
            <label className="mb-1 block text-sm font-medium">
              Patient
            </label>

            <input
              value={patientSearch}
              onChange={(event) =>
                setPatientSearch(event.target.value)
              }
              placeholder="Search patient..."
            className="w-full rounded-lg border border-slate-200 bg-slate-50/50 px-3 py-2.5 text-sm outline-none focus:border-indigo-400 focus:bg-white focus:ring-4 focus:ring-indigo-50"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium">
              Status
            </label>

            <select
              value={status}
              onChange={(event) =>
                setStatus(event.target.value)
              }
            className="w-full rounded-lg border border-slate-200 bg-slate-50/50 px-3 py-2.5 text-sm outline-none focus:border-indigo-400 focus:bg-white focus:ring-4 focus:ring-indigo-50"
            >
              {STATUS_OPTIONS.map((option) => (
                <option
                  key={option.value}
                  value={option.value}
                >
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium">
              Payer ID
            </label>

            <input
              value={payerId}
              onChange={(event) =>
                setPayerId(event.target.value)
              }
              placeholder="Payer UUID..."
            className="w-full rounded-lg border border-slate-200 bg-slate-50/50 px-3 py-2.5 text-sm outline-none focus:border-indigo-400 focus:bg-white focus:ring-4 focus:ring-indigo-50"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium">
              Service date from
            </label>

            <input
              type="date"
              value={serviceDateFrom}
              onChange={(event) =>
                setServiceDateFrom(event.target.value)
              }
            className="w-full rounded-lg border border-slate-200 bg-slate-50/50 px-3 py-2.5 text-sm outline-none focus:border-indigo-400 focus:bg-white focus:ring-4 focus:ring-indigo-50"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium">
              Service date to
            </label>

            <input
              type="date"
              value={serviceDateTo}
              onChange={(event) =>
                setServiceDateTo(event.target.value)
              }
            className="w-full rounded-lg border border-slate-200 bg-slate-50/50 px-3 py-2.5 text-sm outline-none focus:border-indigo-400 focus:bg-white focus:ring-4 focus:ring-indigo-50"
            />
          </div>
        </div>

        <div className="mt-4 flex gap-2">
          <button
            type="submit"
            className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white"
          >
            Apply filters
          </button>

          <button
            type="button"
            onClick={clearFilters}
            className="rounded-md border px-4 py-2 text-sm font-medium"
          >
            Clear
          </button>
        </div>
      </form>

      {error && <ErrorState error={error} onRetry={() => loadClaims()} />}

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1100px] text-left text-sm">
            <thead className="border-b bg-gray-50">
              <tr>
                <th scope="col" className="px-4 py-3"><input aria-label="Select all claims" type="checkbox" checked={claims.length > 0 && selectedClaimIds.length === claims.length} onChange={(event) => setSelectedClaimIds(event.target.checked ? claims.map((claim) => claim.id) : [])} /></th>
                <th scope="col" className="px-4 py-3 font-semibold">
                  Claim number
                </th>

                <th scope="col" className="px-4 py-3 font-semibold">
                  Patient
                </th>

                <th scope="col" className="px-4 py-3 font-semibold">
                  Payer
                </th>

                <th scope="col" className="px-4 py-3 font-semibold">
                  Service date
                </th>

                <th scope="col" className="px-4 py-3 font-semibold">
                  Total
                </th>

                <th scope="col" className="px-4 py-3 font-semibold">
                  Status
                </th>

                <th scope="col" className="px-4 py-3 font-semibold">
                  Readiness
                </th>

                <th scope="col" className="px-4 py-3 font-semibold">
                  Findings summary
                </th>
              </tr>
            </thead>

            <tbody className="divide-y">
              {loading ? (
                <tr>
                  <td colSpan={9} className="p-8 text-center">
                    <LoadingState message="Loading claims..." />
                  </td>
                </tr>
              ) : (
                <>
                  {claims.map((claim) => {
                    const serviceDateText = claim.serviceDate ?? claim.service_date ?? "—";
                    return (
                      <tr key={claim.id}>
                        <td className="px-4 py-3">
                          <input
                            type="checkbox"
                            checked={selectedClaimIds.includes(claim.id)}
                            onChange={(event) =>
                              setSelectedClaimIds((previous) =>
                                event.target.checked
                                  ? [...previous, claim.id]
                                  : previous.filter((id) => id !== claim.id)
                              )
                            }
                          />
                        </td>
                        <td className="whitespace-nowrap px-4 py-4 font-medium">
                          {claim.claimNumber ??
                            claim.claim_number ??
                            "—"}
                        </td>
                        <td className="px-4 py-4">
                          {claim.patientId ??
                            claim.patient_id ??
                            "—"}
                        </td>
                        <td className="px-4 py-4">
                          {claim.payerId ??
                            claim.payer_id ??
                            "—"}
                        </td>
                        <td className="whitespace-nowrap px-4 py-4">
                          {serviceDateText}
                        </td>
                        <td className="whitespace-nowrap px-4 py-4">
                          {formatMoney(
                            claim.totalAmount ??
                              claim.total_amount
                          )}
                        </td>
                        <td className="px-4 py-4">
                          <StatusBadge
                            status={
                              claim.status?.value ??
                              claim.status
                            }
                          />
                        </td>
                        <td className="px-4 py-4">
                          <ScorePill
                            score={
                              claim.readinessScore ??
                              claim.readiness_score ??
                              0
                            }
                          />
                        </td>
                        <td className="max-w-[350px] px-4 py-4">
                          <div className="truncate">
                            {getFindingsSummary(
                              claim.findingsSummary ??
                                claim.findings_summary
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                  {!error && claims.length === 0 && <EmptyState title="No claims found" description="Try changing your filters or search criteria." />}
                </>
              )}
            </tbody>
          </table>
        </div>

        {!loading &&
          claims.length > 0 &&
          hasMore && (
            <div className="flex justify-center border-t p-4">
              <button
                type="button"
                disabled={loadingMore}
                onClick={() =>
                  loadClaims({
                    cursor: nextCursor,
                    append: true,
                  })
                }
                className="rounded-md border px-4 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loadingMore
                  ? "Loading..."
                  : "Load more"}
              </button>
            </div>
          )}
      </div>
    </div>
  );
}

export default Claims;
