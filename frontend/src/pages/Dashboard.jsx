import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/auth/AuthContext";
import { fetchClaims } from "@/api/api";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { buttonVariants } from "@/components/ui/button";

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
        const response = await fetchClaims(accessToken, { limit: 5 });

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
  }, [initialized, authenticated, accessToken]);

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

        {isLoading && <div className="px-6 py-8 text-sm text-gray-500">Loading dashboard data…</div>}

        {!isLoading && loadError && (
          <div className="px-6 py-8 text-sm text-red-600">
            {loadError}
          </div>
        )}

        {!isLoading && !loadError && recentClaims.length === 0 && (
          <div className="px-6 py-8 text-sm text-gray-500">No claims found yet.</div>
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