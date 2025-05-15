import { Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login"; import Dashboard from "./pages/Dashboard";
import { AuthProvider, useAuth } from "./context/AuthContext";
function Protected({ children }){ const { token } = useAuth(); return token?children:<Navigate to="/login" replace/>;}
export default function App(){ return (<AuthProvider><Routes><Route path="/login" element={<Login/>}/><Route path="/" element={<Protected><Dashboard/></Protected>}/></Routes></AuthProvider>); }
