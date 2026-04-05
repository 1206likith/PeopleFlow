import re
import os

filepath = 'src/features/operations/OperationsPage.tsx'
with open(filepath, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. State 'tab' -> 'expandedTab'
text = text.replace('const [tab, setTab] = useState<OpsTab>("System");', 'const [expandedTab, setExpandedTab] = useState<OpsTab | null>("System");')

# 2. panelOutput terminal styling
panel_output_old = """  const panelOutput = (key: string) => (
    <pre className="mt-3 max-h-[240px] overflow-auto code-panel">{String(prettyResults[key] ?? "No output yet")}</pre>
  );"""

panel_output_new = """  const panelOutput = (key: string) => {
    const isBusy = busyKey === key;
    const output = prettyResults[key];
    
    if (isBusy) {
      return (
        <div className="mt-4 rounded-xl bg-[#0a0a0d] border border-white/10 p-4 shadow-inner overflow-hidden relative min-h-[100px]">
          <div className="absolute inset-0 w-[200%] animate-[spin_4s_linear_infinite] opacity-20" style={{ background: 'linear-gradient(90deg, transparent, rgba(168,85,247,0.4), transparent)' }} />
          <div className="absolute inset-0 bg-[#0a0a0d]/80 backdrop-blur-sm" />
          <div className="relative z-10 flex items-center gap-3 font-mono text-xs text-violet-400">
             <span className="animate-pulse">▶</span>
             <span className="animate-pulse">Awaiting uplink sequence...</span>
          </div>
        </div>
      );
    }
    
    if (!output) return null;
    
    return (
      <div className="mt-4 rounded-xl bg-[#0a0a0d] border border-white/10 p-4 font-mono text-[11px] text-emerald-400 shadow-inner overflow-auto max-h-[400px]">
        <div className="flex items-center gap-2 mb-3 pb-3 border-b border-white/5 opacity-70">
           <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
           <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
           <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
           <span className="ml-2 text-[10px] text-fog font-sans tracking-wider">TERMINAL ~ {key}</span>
        </div>
        <pre className="whitespace-pre-wrap break-all">{String(output)}</pre>
      </div>
    );
  };"""
# ensure it's replaced
text = text.replace(panel_output_old, panel_output_new)

# 3. Remove horizontal pill bar
pill_regex = r'<div className="flex gap-1 flex-wrap rounded-2xl p-1 w-fit"[^>]*>.*?</div>'
text = re.sub(pill_regex, '<div className="space-y-4">', text, flags=re.DOTALL)

# 4. Turn tabs into accordions
accordion_pattern = r'\{tab === "(.*?)" && \(\s*<div className="surface-grid">(.*?)</div>\s*\)\}'

def replacer(match):
    category = match.group(1)
    content = match.group(2)
    return f"""      {{/* {category} Accordion */}}
      <div className="glass-card overflow-hidden transition-all duration-300 shadow-lg" style={{{{ border: "1px solid rgba(255,255,255,0.05)" }}}}>
         <button 
           type="button"
           className="w-full flex items-center justify-between p-5 text-left transition-colors"
           style={{{{ background: expandedTab === "{category}" ? "rgba(255,255,255,0.03)" : "transparent" }}}}
           onClick={{() => setExpandedTab(expandedTab === "{category}" ? null : "{category}")}}
         >
            <h2 className="text-lg font-bold text-snow flex items-center gap-4" style={{{{ fontFamily: "var(--font-heading)" }}}}>
               <span className="text-violet-400 text-sm font-mono tracking-widest">OPS</span>
               {category}
            </h2>
            <svg className={{`w-5 h-5 text-fog transition-transform duration-300 ${{expandedTab === "{category}" ? "rotate-180" : ""}}`}} fill="none" viewBox="0 0 24 24" stroke="currentColor">
               <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={{2}} d="M19 9l-7 7-7-7" />
            </svg>
         </button>
         
         <div className={{`transition-all duration-500 overflow-hidden ${{expandedTab === "{category}" ? "opacity-100" : "max-h-0 opacity-0"}}`}}>
            <div className="p-5 border-t border-white/5 space-y-6">
               <div className="surface-grid">
                  {content}
               </div>
            </div>
         </div>
      </div>"""

text = re.sub(accordion_pattern, replacer, text, flags=re.DOTALL)

# close the space-y-4 div that replaced the pill bar
text = text.replace('<AdminKeyDialog open={adminDialogOpen} onClose={() => setAdminDialogOpen(false)} />', '</div>\n\n      <AdminKeyDialog open={adminDialogOpen} onClose={() => setAdminDialogOpen(false)} />')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(text)

print("Rewrite successful")
