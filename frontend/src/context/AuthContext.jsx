import { createContext, useContext, useState } from "react";
import api from "../services/api";
const Ctx = createContext();
export function AuthProvider({children}){ const [token,setToken]=useState(localStorage.getItem("token")||"");
async function login(email,password){ const {data}=await api.post("/auth/login",{email,password}); localStorage.setItem("token",data.access_token); setToken(data.access_token);}
function logout(){ localStorage.removeItem("token"); setToken("");}
return <Ctx.Provider value={{token,login,logout}}>{children}</Ctx.Provider>}
export function useAuth(){ return useContext(Ctx);}
