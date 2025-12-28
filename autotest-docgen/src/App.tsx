// App.tsx
// 🚨 إزالة الاستيراد لـ BrowserRouter كـ Router
import { Routes, Route } from 'react-router-dom'; // 👈 ترك Routes و Route فقط

import Signup from './Signup';
import Dashboard from './Dashboard';
import UsersList from './compoents/ProjectCutomizationModal/UsersList';
// يجب عليك إنشاء وإضافة ملفات الـ contextes هنا إذا كنت تستخدم useAuth

function App() {
  return (
    // 🚨 إزالة الغلاف <Router> (أو <BrowserRouter>)
    <> 
      <Routes>
        {/* الواجهة الأولى: تسجيل الدخول (الصفحة الرئيسية) */}
        <Route path="/" element={<Signup />} />
        
        {/* الواجهة الثانية: لوحة التحكم وإدارة المشاريع */}
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/users" element={<UsersList users={[]} isLoading={false} error={null} />} />    
        {/* يمكن إضافة مسارات أخرى هنا */}
      </Routes>
    </>
  );
}

export default App;