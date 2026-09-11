import { useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { BarChart3, ClipboardList, FileCog, LayoutDashboard, Menu, Users, X } from "lucide-react";
import { useAuth } from "@/auth/AuthContext";
import { Button } from "@/components/ui/button";

const navItems = [["/dashboard", "Dashboard", LayoutDashboard], ["/claims", "Claims", ClipboardList], ["/patients", "Patients", Users], ["/rules", "Rules", FileCog]];
const navLinkClasses = ({ isActive }) => `group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${isActive ? "bg-indigo-50 text-indigo-700" : "text-slate-600 hover:bg-slate-50 hover:text-slate-950"}`;

function AppShell() {
  const { authenticated, initialized, login, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  return <div className="min-h-screen bg-slate-50/80">
    <aside className={`fixed inset-y-0 left-0 z-40 w-64 border-r border-slate-200 bg-white px-4 py-5 shadow-sm transition-transform lg:translate-x-0 ${mobileOpen ? "translate-x-0" : "-translate-x-full"}`}><div className="flex items-center justify-between px-2"><Link to="/dashboard" onClick={() => setMobileOpen(false)} className="flex items-center gap-2.5 text-base font-bold tracking-tight text-slate-950"><span className="grid h-8 w-8 place-items-center rounded-lg bg-indigo-600 text-sm text-white shadow-sm">IC</span> InsureFlow</Link><button type="button" onClick={() => setMobileOpen(false)} className="rounded-md p-1 text-slate-400 hover:bg-slate-100 lg:hidden"><X size={18} /></button></div><p className="mb-3 mt-10 px-3 text-[10px] font-bold uppercase tracking-[0.2em] text-slate-400">Workspace</p><nav className="space-y-1">{navItems.map(([to, label, Icon]) => <NavLink key={to} to={to} onClick={() => setMobileOpen(false)} className={navLinkClasses}><Icon size={17} strokeWidth={1.8} /><span>{label}</span></NavLink>)}</nav><div className="absolute bottom-5 left-4 right-4 rounded-xl bg-slate-50 p-3"><div className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-emerald-500" /><span className="text-xs font-medium text-slate-700">Operations online</span></div><p className="mt-1 text-[11px] text-slate-500">Claims workspace</p></div></aside>
    {mobileOpen && <button type="button" aria-label="Close navigation" onClick={() => setMobileOpen(false)} className="fixed inset-0 z-30 bg-slate-950/20 lg:hidden" />}
    <div className="lg:pl-64"><header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/85 backdrop-blur-xl"><div className="mx-auto flex h-16 max-w-[1500px] items-center justify-between px-4 sm:px-6 lg:px-8"><div className="flex items-center gap-3"><button type="button" onClick={() => setMobileOpen(true)} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 lg:hidden"><Menu size={20} /></button><div className="hidden items-center gap-2 text-sm text-slate-500 sm:flex"><BarChart3 size={16} /> Operations center</div></div><div className="flex items-center gap-3">{!initialized && <span className="text-sm text-slate-500">Checking auth...</span>}{initialized && !authenticated && <Button type="button" size="sm" onClick={login}>Login</Button>}{initialized && authenticated && <Button type="button" variant="outline" size="sm" onClick={logout}>Logout</Button>}</div></div></header><main className="mx-auto min-h-[calc(100vh-4rem)] max-w-[1500px] px-4 py-6 sm:px-6 sm:py-8 lg:px-8"><Outlet /></main></div>
  </div>;
}
export default AppShell;
