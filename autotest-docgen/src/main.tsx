import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'; // 👈 استيراد BrowserRouter
import './index.css'
import App from './App.tsx'
// 🚨 تأكدي من مسار الاستيراد الصحيح لـ AuthProvider
import { AuthProvider } from './context/AuthContext.tsx' 

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    {/* 🚨 الآن BrowserRouter هو الغلاف الخارجي */}
    <BrowserRouter> 
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
);