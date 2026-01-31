import React, { useState } from 'react';
import {
    MessageSquare,
    Terminal,
    Settings,
    Cpu,
    ChevronLeft,
    ChevronRight,
    Activity
} from 'lucide-react';
import { motion } from 'framer-motion';

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [sidebarOpen, setSidebarOpen] = useState(true);

    return (
        <div className="flex h-screen w-screen bg-background text-white overflow-hidden">
            {/* Side Navigation Bar */}
            <aside className="w-16 flex flex-col items-center py-6 glass-panel rounded-none border-y-0 border-l-0 z-20">
                <div className="mb-10 text-primary-light">
                    <Cpu size={32} className="animate-pulse" />
                </div>

                <nav className="flex flex-col gap-6 flex-1">
                    <NavItem icon={<MessageSquare size={24} />} active label="Chat" />
                    <NavItem icon={<Terminal size={24} />} label="Terminal" />
                    <NavItem icon={<Activity size={24} />} label="Metrics" />
                </nav>

                <div className="mt-auto">
                    <NavItem icon={<Settings size={24} />} label="Settings" />
                </div>
            </aside>

            {/* Main Content Area (Split View) */}
            <main className="flex-1 flex overflow-hidden relative">
                {/* Chat Section */}
                <motion.section
                    initial={false}
                    animate={{ width: sidebarOpen ? 420 : 0, opacity: sidebarOpen ? 1 : 0 }}
                    className="h-full border-r border-white/10 overflow-hidden flex flex-col bg-white/[0.02]"
                >
                    <div className="p-4 border-bottom border-white/10 flex justify-between items-center">
                        <h2 className="font-bold text-lg flex items-center gap-2">
                            <MessageSquare size={18} className="text-primary-light" />
                            Agent Chat
                        </h2>
                    </div>

                    <div className="flex-1 overflow-y-auto p-4 space-y-4">
                        {/* Chat messages will go here */}
                        <div className="p-4 glass-panel bg-white/5 border-primary-light/30">
                            <p className="text-sm opacity-80">Hello! I'm your AgentBus assistant. How can I help you today?</p>
                        </div>
                    </div>

                    <div className="p-4 border-t border-white/10">
                        <div className="relative">
                            <input
                                placeholder="Type a message or '!' for command..."
                                className="w-full glass-input p-3 pr-12 text-sm"
                            />
                            <button className="absolute right-2 top-1.5 p-1.5 bg-primary-light hover:bg-primary-dark rounded-md transition-colors text-white">
                                <ChevronRight size={18} />
                            </button>
                        </div>
                    </div>
                </motion.section>

                {/* Sidebar Toggle Button */}
                <button
                    onClick={() => setSidebarOpen(!sidebarOpen)}
                    className="absolute left-0 top-1/2 -translate-y-1/2 translate-x-[-50%] z-10 w-6 h-12 glass-panel flex items-center justify-center hover:bg-white/10 transition-colors"
                    style={{ left: sidebarOpen ? 420 : 0 }}
                >
                    {sidebarOpen ? <ChevronLeft size={14} /> : <ChevronRight size={14} />}
                </button>

                {/* Work Area / Workspace Section */}
                <section className="flex-1 h-full bg-[#0d0e14] relative overflow-hidden flex flex-col">
                    <header className="h-14 glass-panel rounded-none border-x-0 border-t-0 px-6 flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <span className="text-xs font-mono text-white/40 uppercase tracking-widest">Workspace</span>
                            <div className="h-4 w-px bg-white/10" />
                            <span className="text-xs text-primary-light font-medium bg-primary-light/10 px-2 py-0.5 rounded">Qwen-3-32B (Local)</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="flex items-center gap-1.5 px-3 py-1 bg-success/10 rounded-full">
                                <div className="w-1.5 h-1.5 bg-success rounded-full animate-pulse" />
                                <span className="text-[10px] text-success font-bold uppercase">Online</span>
                            </div>
                        </div>
                    </header>

                    <div className="flex-1 p-6 overflow-hidden">
                        {children}
                    </div>
                </section>
            </main>
        </div>
    );
};

const NavItem = ({ icon, active = false, label }: { icon: React.ReactNode, active?: boolean, label: string }) => (
    <div className={`relative group cursor-pointer p-2 rounded-xl transition-all ${active ? 'bg-primary-light text-white shadow-lg shadow-primary-light/20' : 'text-white/40 hover:text-white hover:bg-white/5'}`}>
        {icon}
        <div className="absolute left-16 scale-0 group-hover:scale-100 transition-transform origin-left bg-panel border border-white/10 px-2 py-1 rounded text-xs whitespace-nowrap z-50">
            {label}
        </div>
    </div>
);

export default Layout;
