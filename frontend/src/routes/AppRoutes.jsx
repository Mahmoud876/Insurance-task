import { Navigate, Routes, Route } from "react-router-dom";
import ProtectedRoute from "./ProtectedRoute";

import AppShell from "@/components/layout/AppShell";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import Claims from "@/pages/Claims";
import ClaimEditor from "@/pages/claims/ClaimEditor";
import Patients from "@/pages/Patients";

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/claims" replace />} />

      <Route path="/login" element={<Login />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/claims" element={<Claims />} />
          <Route path="/claims/new" element={<ClaimEditor />} />
          <Route path="/claims/:claimId" element={<ClaimEditor />} />
          <Route path="/patients" element={<Patients />} />
        </Route>
      </Route>
    </Routes>
  );
}

export default AppRoutes;

