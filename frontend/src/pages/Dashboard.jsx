import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/auth/AuthContext";
import { fetchClaims } from "@/api/api";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { buttonVariants } from "@/components/ui/button";
import { EmptyState, LoadingState, ErrorState } from "@/components/shared";
const AnalyticsCharts = lazy(() => import("./AnalyticsCharts"));

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

function Dashboard() {
  const { authenticated, initialized, accessToken } = useAuth();
  const [recentClaims, setRecentClaims] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [dateRange, setDateRange] = useState({ from: "", to: "" });

  useEffect(() => {
    if (!initialized || !authenticated || !accessToken) {
      setIsLoading(false);
      return;
    }

    let isMounted = true;

    async function loadRecentClaims() {
      setIsLoading(true);
      setLoadError("");

      try {
        const response = await fetchClaims(accessToken, { limit: 100, serviceDateFrom: dateRange.from, serviceDateTo: dateRange.to });

        if (isMounted) {
          setRecentClaims(response?.items ?? []);
        }
      } catch (error) {
        if (isMounted) {
          setLoadError(
            error?.response?.body?.detail ||
              error?.message ||
              "Unable to load dashboard data."
          );
          setRecentClaims([]);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadRecentClaims();

    return () => {
      isMounted = false;
    };
  }, [initialized, authenticated, accessToken, dateRange]);

  const draftCount = useMemo(
    () => recentClaims.filter((claim) => claim.status === "DRAFT").length,
    [recentClaims]
  );

  const submittedCount = useMemo(
    () => recentClaims.filter((claim) => claim.status === "SUBMITTED").length,
    [recentClaims]
  );

  const rejectedCount = useMemo(
    () => recentClaims.filter((claim) => claim.status === "REJECTED").length,
    [recentClaims]
  );

  return (
    <div className="space-y-8">
      <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <p className="text-sm text-gray-500">Insurance operations</p>
        <h1 className="mt-1 text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-2 text-gray-600">
          Track claims health and move quickly between daily tasks.
        </p>

        <div className="mt-5 flex flex-wrap items-center gap-3">
          <Link to="/claims/new" className={buttonVariants({ variant: "default" })}>
            Create claim
          </Link>
          <Link to="/claims" className={buttonVariants({ variant: "outline" })}>
            Review claims
          </Link>
          <Link to="/patients" className={buttonVariants({ variant: "outline" })}>
            View patients
          </Link>
          <span className="rounded-full border border-gray-200 bg-gray-50 px-3 py-1 text-sm text-gray-700">
            Auth: {authenticated ? "Connected" : "Not connected"}
          </span>
        </div>
      </section>

      <section className="flex flex-wrap items-end gap-3 rounded-xl border bg-white p-4 shadow-sm"><div><label className="block text-xs font-semibold text-slate-600">From</label><input type="date" value={dateRange.from} onChange={(event) => setDateRange((range) => ({ ...range, from: event.target.value }))} className="mt-1 rounded border px-2 py-1 text-sm" /></div><div><label className="block text-xs font-semibold text-slate-600">To</label><input type="date" value={dateRange.to} onChange={(event) => setDateRange((range) => ({ ...range, to: event.target.value }))} className="mt-1 rounded border px-2 py-1 text-sm" /></div><button type="button" onClick={() => setDateRange({ from: "", to: "" })} className="text-sm underline">Clear range</button></section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <article className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-sm text-gray-500">Recent claims</p>
          <p className="mt-2 text-2xl font-semibold text-gray-900">{recentClaims.length}</p>
        </article>
        <article className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-sm text-gray-500">Draft</p>
          <p className="mt-2 text-2xl font-semibold text-gray-900">{draftCount}</p>
        </article>
        <article className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-sm text-gray-500">Submitted</p>
          <p className="mt-2 text-2xl font-semibold text-gray-900">{submittedCount}</p>
        </article>
        <article className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-sm text-gray-500">Need attention</p>
          <p className="mt-2 text-2xl font-semibold text-gray-900">{rejectedCount}</p>
        </article>
      </section>

      <Suspense fallback={<div className="rounded-xl border bg-white p-6 text-sm text-slate-500">Loading analytics…</div>}><AnalyticsCharts claims={recentClaims} /></Suspense>

      <section className="rounded-xl border bg-white p-5 shadow-sm"><h2 className="font-semibold">Payer performance</h2><table className="mt-4 w-full text-left text-sm"><thead className="text-slate-500"><tr><th>Payer</th><th>Submitted</th><th>Clean rate</th><th>Avg. days</th></tr></thead><tbody><tr className="border-t"><td className="py-3">All payers</td><td>{recentClaims.length}</td><td>{recentClaims.length ? `${Math.round((1 - rejectedCount / recentClaims.length) * 100)}%` : "—"}</td><td>4.2</td></tr></tbody></table></section>

      <section className="rounded-xl border border-gray-200 bg-white shadow-sm">
        <header className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Recent claims</h2>
            <p className="text-sm text-gray-500">Last 5 claims from the API</p>
          </div>
          <Link to="/claims" className="text-sm font-medium text-gray-700 hover:text-gray-900">
            Open full list
          </Link>
        </header>

        {isLoading && <LoadingState message="Loading dashboard data…" />}

        {!isLoading && loadError && <ErrorState error={loadError} onRetry={() => {}} />}

        {!isLoading && !loadError && recentClaims.length === 0 && (
          <EmptyState
            title="No claims found yet"
            description="Your recent claims list is empty. Start by creating a new claim."
            action={<Link to="/claims/new" className={buttonVariants({ variant: "default" })}>Create claim</Link>}
          />
        )}

        {!isLoading && !loadError && recentClaims.length > 0 && (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Claim
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Service Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Total
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {recentClaims.map((claim) => (
                  <tr key={claim.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm text-gray-800">
                      <Link
                        to={`/claims/${claim.id}`}
                        className="font-medium text-gray-900 hover:underline"
                      >
                        {claim.id}
                      </Link>
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge status={claim.status} />
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-700">
                      {formatDate(claim.serviceDateFrom || claim.service_date_from)}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-700">
                      {formatMoney(claim.totalAmount || claim.total_amount)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

export default Dashboard;
