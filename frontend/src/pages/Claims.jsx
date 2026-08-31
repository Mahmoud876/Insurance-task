import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { fetchClaims } from "../api/api";
import { StatusBadge } from "../components/shared/StatusBadge";
import { ScorePill } from "../components/shared/ScorePill";

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "DRAFT", label: "Draft" },
  { value: "SUBMITTED", label: "Submitted" },
  { value: "ACCEPTED", label: "Accepted" },
  { value: "REJECTED", label: "Rejected" },
  { value: "PAID", label: "Paid" },
];

function SkeletonRow() {
  return (
    <tr className="animate-pulse">
      {Array.from({ length: 8 }).map((_, index) => (
        <td key={index} className="px-4 py-4">
          <div className="h-4 rounded bg-gray-200" />
        </td>
      ))}
    </tr>
  );
}

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
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-bold">
          Claims
        </h1>

        <p className="mt-1 text-gray-500">
          Review claims, readiness, and validation findings.
        </p>
      </div>

      <form
        onSubmit={applyFilters}
        className="rounded-lg border bg-white p-4 shadow-sm"
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
              className="w-full rounded-md border px-3 py-2 text-sm"
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
              className="w-full rounded-md border px-3 py-2 text-sm"
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
              className="w-full rounded-md border px-3 py-2 text-sm"
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
              className="w-full rounded-md border px-3 py-2 text-sm"
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
              className="w-full rounded-md border px-3 py-2 text-sm"
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

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <div className="font-semibold text-red-800">
            Unable to load claims
          </div>

          <p className="mt-1 text-sm text-red-700">
            {error}
          </p>

          <button
            type="button"
            onClick={() => loadClaims()}
            className="mt-3 rounded-md border border-red-300 bg-white px-3 py-2 text-sm font-medium text-red-700"
          >
            Try again
          </button>
        </div>
      )}

      <div className="overflow-hidden rounded-lg border bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1100px] text-left text-sm">
            <thead className="border-b bg-gray-50">
              <tr>
                <th className="px-4 py-3 font-semibold">
                  Claim number
                </th>

                <th className="px-4 py-3 font-semibold">
                  Patient
                </th>

                <th className="px-4 py-3 font-semibold">
                  Payer
                </th>

                <th className="px-4 py-3 font-semibold">
                  Service date
                </th>

                <th className="px-4 py-3 font-semibold">
                  Total
                </th>

                <th className="px-4 py-3 font-semibold">
                  Status
                </th>

                <th className="px-4 py-3 font-semibold">
                  Readiness
                </th>

                <th className="px-4 py-3 font-semibold">
                  Findings summary
                </th>
              </tr>
            </thead>

            <tbody className="divide-y">
              {loading &&
                Array.from({ length: 6 }).map(
                  (_, index) => (
                    <SkeletonRow key={index} />
                  )
                )}

              {!loading &&
                claims.map((claim) => {
                  const serviceDateFromValue =
                    claim.serviceDateFrom ??
                    claim.service_date_from;

                  const serviceDateToValue =
                    claim.serviceDateTo ??
                    claim.service_date_to;

                  let serviceDateText =
                    formatDate(
                      serviceDateFromValue
                    );

                  if (serviceDateToValue) {
                    serviceDateText =
                      formatDate(
                        serviceDateFromValue
                      ) +
                      " - " +
                      formatDate(
                        serviceDateToValue
                      );
                  }

                  return (
                    <tr
                      key={claim.id}
                      className="hover:bg-gray-50"
                    >
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

              {!loading &&
                !error &&
                claims.length === 0 && (
                  <tr>
                    <td
                      colSpan={8}
                      className="px-6 py-16 text-center"
                    >
                      <div className="text-lg font-semibold">
                        No claims found
                      </div>

                      <p className="mt-1 text-sm text-gray-500">
                        Try changing your filters or search
                        criteria.
                      </p>
                    </td>
                  </tr>
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
