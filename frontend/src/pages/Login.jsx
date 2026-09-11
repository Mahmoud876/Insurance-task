import LoginButton from "@/components/auth/LoginButton";
import { ShieldCheck, Sparkles } from "lucide-react";

function Login() {
  return <main className="relative grid min-h-screen place-items-center overflow-hidden bg-slate-950 px-6 py-12"><div className="absolute -left-32 -top-32 h-96 w-96 rounded-full bg-indigo-600/30 blur-3xl" /><div className="absolute -bottom-40 -right-20 h-96 w-96 rounded-full bg-cyan-500/20 blur-3xl" /><section className="relative w-full max-w-md rounded-3xl border border-white/10 bg-white p-8 shadow-2xl shadow-black/30 sm:p-10"><div className="mb-8 flex items-center gap-2 text-sm font-bold text-slate-950"><span className="grid h-9 w-9 place-items-center rounded-xl bg-indigo-600 text-white">IC</span> InsureFlow</div><div className="mb-8"><div className="mb-5 inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700"><Sparkles size={13} /> Claims operations</div><h1 className="text-3xl font-bold tracking-tight text-slate-950">Welcome back</h1><p className="mt-2 text-sm leading-6 text-slate-500">Sign in to review claim readiness, resolve findings, and submit clean claims.</p></div><div className="rounded-2xl border border-slate-200 bg-slate-50 p-4"><div className="mb-4 flex items-center gap-2 text-sm font-semibold text-slate-800"><ShieldCheck size={17} className="text-emerald-600" /> Secure workspace</div><LoginButton /></div><p className="mt-6 text-center text-xs leading-5 text-slate-400">Access is managed by your organisation&apos;s identity provider.</p></section></main>;
}

export default Login;
