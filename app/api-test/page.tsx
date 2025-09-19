'use client';
import { useEffect, useState } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE!;

type Signal = { symbol:string; decision:string; ts:string; close:number; rationale?:string };

export default function ApiTestPage(){
  const [signals, setSignals] = useState<Signal[]>([]);
  const [err, setErr] = useState<string>('');

  useEffect(()=>{
    fetch(`${API_BASE}/api/stockpilot/signals`)
      .then(r=>r.json())
      .then(setSignals)
      .catch(e=>setErr(String(e)));
  },[]);

  return (
    <main style={{padding:24}}>
      <h1>API Test</h1>
      <p>API_BASE: {API_BASE}</p>
      {err && <pre style={{color:'salmon'}}>{err}</pre>}
      <pre>{JSON.stringify(signals.slice(0,3), null, 2)}</pre>
    </main>
  );
}
