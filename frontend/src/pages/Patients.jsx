import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/auth/AuthContext";
import { fetchClaims } from "@/api/api";

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

  useEffect(() => {
    if (!initialized || !authenticated || !accessToken) {
      return;
    }

    let isMounted = true;

    async function loadClaims() {
      setIsLoading(true);
      setLoadError("");

      try {
        const response = await fetchClaims(accessToken, { limit: 200 });
        if (isMounted) {
          setClaims(response?.items ?? []);
        }
      } catch (error) {
        if (isMounted) {
          setClaims([]);
          setLoadError(
            error?.response?.body?.detail ||
              error?.message ||
              "Unable to load patients data."
          );
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadClaims();

    return () => {
      isMounted = false;
    };
  }, [initialized, authenticated, accessToken]);

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
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold">Patients</h1>
          <p className="mt-1 text-gray-500">
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

      <section className="rounded-lg border bg-white p-4 shadow-sm">
        <label className="mb-2 block text-sm font-medium">Search patient ID</label>
        <input
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.target.value)}
          placeholder="Type patient ID..."
          className="w-full rounded-md border px-3 py-2 text-sm"
        />
      </section>

      {loadError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <div className="font-semibold text-red-800">Unable to load patients</div>
          <p className="mt-1 text-sm text-red-700">{loadError}</p>
        </div>
      )}

      <section className="overflow-hidden rounded-lg border bg-white shadow-sm">
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
            <tbody>
              {isLoading && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                    Loading patients...
                  </td>
                </tr>
              )}

              {!isLoading && filteredRows.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                    No patients found.
                  </td>
                </tr>
              )}

              {!isLoading &&
                filteredRows.map((row) => (
                  <tr key={row.patientId} className="border-b last:border-b-0 hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">{row.patientId}</td>
                    <td className="px-4 py-3 text-gray-700">{row.claimCount}</td>
                    <td className="px-4 py-3 text-gray-700">{row.openClaims}</td>
                    <td className="px-4 py-3 text-gray-700">{formatDate(row.lastServiceDate)}</td>
                    <td className="px-4 py-3 text-gray-700">{formatMoney(row.totalBilled)}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

export default Patients;

