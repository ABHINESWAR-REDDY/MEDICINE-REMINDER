import React from 'react';
import Header from './Header';
import Sidebar from './Sidebar';
import AIAssistantWidget from '../ai/AIAssistantWidget';

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
      {/* Global Multi-Source Verified AI Healthcare Assistant */}
      <AIAssistantWidget />
    </div>
  );
};

export default Layout;
