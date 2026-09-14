import { useEffect, useMemo, useState, useCallback } from "react";
import { useAuth } from "@/auth/AuthContext";
import { fetchClaims } from "@/api/api";
import { EmptyState, LoadingState, ErrorState, SkeletonRow } from "@/components/shared";

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
  const number = Number(value);
  if (Number.isNaN(number)) {
    return "$0.00";
  }

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(number);
}

function normalizeClaim(claim) {
  return {
    id: claim.id,
    patientId: claim.patientId || claim.patient_id || "Unknown",
    serviceDateFrom: claim.serviceDateFrom || claim.service_date_from || null,
    totalAmount: Number(claim.totalAmount || claim.total_amount || 0),
    status: claim.status || "DRAFT",
  };
}

function toPatientRows(claims) {
  const groups = new Map();

  for (const rawClaim of claims) {
    const claim = normalizeClaim(rawClaim);
    const existing = groups.get(claim.patientId);

    if (!existing) {
      groups.set(claim.patientId, {
        patientId: claim.patientId,
        claimCount: 1,
        totalBilled: claim.totalAmount,
        openClaims: claim.status === "DRAFT" || claim.status === "SUBMITTED" ? 1 : 0,
        lastServiceDate: claim.serviceDateFrom,
      });
      continue;
    }

    existing.claimCount += 1;
    existing.totalBilled += claim.totalAmount;
    if (claim.status === "DRAFT" || claim.status === "SUBMITTED") {
      existing.openClaims += 1;
    }

    if (
      claim.serviceDateFrom &&
      (!existing.lastServiceDate ||
        new Date(claim.serviceDateFrom).getTime() >
          new Date(existing.lastServiceDate).getTime())
    ) {
      existing.lastServiceDate = claim.serviceDateFrom;
    }
  }

  return Array.from(groups.values()).sort((a, b) => b.claimCount - a.claimCount);
}

function Patients() {
  const { authenticated, initialized, accessToken, login } = useAuth();
  const [claims, setClaims] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState("");

  const loadClaims = useCallback(async () => {
    if (!initialized || !authenticated || !accessToken) {
      return;
    }

    setIsLoading(true);
    setLoadError("");

    try {
      const response = await fetchClaims(accessToken, { limit: 100 });
      setClaims(response?.items ?? []);
    } catch (error) {
      setClaims([]);
      setLoadError(
        error?.response?.body?.detail ||
          error?.message ||
          "Unable to load patients data."
      );
    } finally {
      setIsLoading(false);
    }
  }, [initialized, authenticated, accessToken]);

  useEffect(() => {
    loadClaims();
  }, [loadClaims]);

  const patientRows = useMemo(() => toPatientRows(claims), [claims]);

  const filteredRows = useMemo(() => {
    if (!searchQuery.trim()) {
      return patientRows;
    }

    const query = searchQuery.trim().toLowerCase();
    return patientRows.filter((row) => row.patientId.toLowerCase().includes(query));
  }, [patientRows, searchQuery]);

  const totalOpenClaims = useMemo(
    () => patientRows.reduce((sum, row) => sum + row.openClaims, 0),
    [patientRows]
  );

  const totalBilled = useMemo(
    () => patientRows.reduce((sum, row) => sum + row.totalBilled, 0),
    [patientRows]
  );

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
        <h1 className="text-2xl font-semibold">Patients</h1>
        <p className="text-gray-500">Please sign in to view patients.</p>
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
          <h1 className="text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">Patients</h1>
          <p className="mt-2 text-sm text-slate-500">
            Patient overview based on recent claim activity.
          </p>
        </div>
      </div>

      <section className="grid gap-4 md:grid-cols-3">
        <article className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-sm text-gray-500">Patients in view</p>
          <p className="mt-2 text-2xl font-semibold text-gray-900">{filteredRows.length}</p>
        </article>
        <article className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-sm text-gray-500">Open claims</p>
          <p className="mt-2 text-2xl font-semibold text-gray-900">{totalOpenClaims}</p>
        </article>
        <article className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-sm text-gray-500">Total billed</p>
          <p className="mt-2 text-2xl font-semibold text-gray-900">{formatMoney(totalBilled)}</p>
        </article>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <label className="mb-2 block text-sm font-medium">Search patient ID</label>
        <input
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.target.value)}
          placeholder="Type patient ID..."
          className="w-full rounded-lg border border-slate-200 bg-slate-50/50 px-3 py-2.5 text-sm outline-none focus:border-indigo-400 focus:bg-white focus:ring-4 focus:ring-indigo-50"
        />
      </section>

      {loadError && <ErrorState error={loadError} onRetry={loadClaims} />}

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] text-left text-sm">
            <thead className="border-b bg-gray-50">
              <tr>
                <th className="px-4 py-3 font-semibold">Patient ID</th>
                <th className="px-4 py-3 font-semibold">Claims</th>
                <th className="px-4 py-3 font-semibold">Open claims</th>
                <th className="px-4 py-3 font-semibold">Last service date</th>
                <th className="px-4 py-3 font-semibold">Total billed</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {isLoading ? (
                <>
                  <SkeletonRow />
                  <SkeletonRow />
                  <SkeletonRow />
                  <SkeletonRow />
                  <SkeletonRow />
                </>
              ) : filteredRows.length === 0 ? (
                <tr className="bg-white">
                  <td colSpan={5} className="p-12">
                    <EmptyState
                      title="No patients found"
                      description="Try a different search query or check your data."
                    />
                  </td>
                </tr>
              ) : (
                filteredRows.map((row) => (
                  <tr key={row.patientId} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">{row.patientId}</td>
                    <td className="px-4 py-3 text-gray-700">{row.claimCount}</td>
                    <td className="px-4 py-3 text-gray-700">{row.openClaims}</td>
                    <td className="px-4 py-3 text-gray-700">{formatDate(row.lastServiceDate)}</td>
                    <td className="px-4 py-3 text-gray-700">{formatMoney(row.totalBilled)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

export default Patients;
