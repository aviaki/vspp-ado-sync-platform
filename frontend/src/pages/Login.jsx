import { useState } from "react"; import { useNavigate } from "react-router-dom"; import { useAuth } from "../context/AuthContext";
export default function Login(){ const [email,setEmail]=useState(""),[password,setPassword]=useState(""),[err,setErr]=useState("");
const nav=useNavigate(); const {login}=useAuth();
async function submit(e){ e.preventDefault(); try{await login(email,password); nav("/");}catch{setErr("Invalid credentials");}}
return (<div className="flex items-center justify-center h-screen bg-primary/10">
<form onSubmit={submit} className="bg-white p-8 rounded-xl shadow w-80 space-y-4"><h1 className="text-2xl font-bold text-primary text-center">Login</h1>
{err&&<p className="text-red-500 text-sm">{err}</p>}<input className="border w-full p-2 rounded" type="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="Email" required/>
<input className="border w-full p-2 rounded" type="password" value={password} onChange={e=>setPassword(e.target.value)} placeholder="Password" required/>
<button className="w-full bg-primary text-white py-2 rounded hover:bg-primary/90">Sign in</button></form></div>);}
