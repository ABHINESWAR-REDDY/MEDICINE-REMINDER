import React from 'react';
import Header from './Header';
import Sidebar from './Sidebar';

export const Layout = ({ children }) => {
  return (
    <div className="min-h-screen bg-slate-950 flex flex-col text-slate-100 w-full">
      <Header />
      <div className="flex flex-1 w-full min-w-0">
        <Sidebar />
        <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto w-full min-w-0">
          {children}
        </main>
      </div>
    </div>
  );
};

export default Layout;
