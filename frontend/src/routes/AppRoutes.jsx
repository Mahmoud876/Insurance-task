import { Routes, Route } from "react-router-dom";
import Dashboard from "@/pages/Dashboard";
import Claims from "@/pages/Claims";
import Patients from "@/pages/Patients";

function AppRoutes() {
  return (
    <Routes>
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/claims" element={<Claims />} />
      <Route path="/patients" element={<Patients />} />
    </Routes>
  );
}

export default AppRoutes;