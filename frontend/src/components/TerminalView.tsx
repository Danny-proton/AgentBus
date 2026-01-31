import React, { useState, useEffect, useRef } from 'react';
import { Terminal as TerminalIcon, Play, Square, Trash2 } from 'lucide-react';

interface LogLine {
    id: string;
    type: 'info' | 'error' | 'success' | 'command';
    content: string;
    timestamp: string;
}

const TerminalView: React.FC = () => {
    const [logs, setLogs] = useState<LogLine[]>([
        { id: '1', type: 'info', content: 'Initializing AgentBus Kernel...', timestamp: new Date().toLocaleTimeString() },
        { id: '2', type: 'success', content: 'Local Model connected: Qwen-3-32B', timestamp: new Date().toLocaleTimeString() },
        { id: '3', type: 'info', content: 'WebSocket gateway listening on port 18790', timestamp: new Date().toLocaleTimeString() },
    ]);

    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs]);

    const clearLogs = () => setLogs([]);

    return (
        <div className="h-full flex flex-col glass-panel overflow-hidden border-white/5 bg-black/40">
            <div className="flex items-center justify-between px-4 py-2 border-b border-white/5 bg-white/5">
                <div className="flex items-center gap-2 text-xs font-mono text-white/60">
                    <TerminalIcon size={14} />
                    <span>REALTIME_LOGS</span>
                </div>
                <div className="flex items-center gap-4">
                    <button onClick={clearLogs} className="text-white/40 hover:text-white transition-colors">
                        <Trash2 size={14} />
                    </button>
                    <div className="flex bg-black/40 rounded p-0.5 border border-white/5">
                        <button className="p-1 text-success hover:bg-success/10 rounded transition-colors">
                            <Play size={10} fill="currentColor" />
                        </button>
                        <button className="p-1 text-white/20 rounded">
                            <Square size={10} fill="currentColor" />
                        </button>
                    </div>
                </div>
            </div>

            <div
                ref={scrollRef}
                className="flex-1 p-4 font-mono text-[13px] overflow-y-auto space-y-1 selection:bg-primary-light/30"
            >
                {logs.map(log => (
                    <div key={log.id} className="flex gap-3 animate-in fade-in slide-in-from-left-2 duration-300">
                        <span className="text-white/20 flex-shrink-0">[{log.timestamp}]</span>
                        <span className={`
              ${log.type === 'error' ? 'text-error' : ''}
              ${log.type === 'success' ? 'text-success' : ''}
              ${log.type === 'info' ? 'text-primary-light' : ''}
              ${log.type === 'command' ? 'text-white font-bold' : 'text-white/80'}
            `}>
                            {log.type === 'command' && <span className="mr-2 text-warning">$</span>}
                            {log.content}
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default TerminalView;
