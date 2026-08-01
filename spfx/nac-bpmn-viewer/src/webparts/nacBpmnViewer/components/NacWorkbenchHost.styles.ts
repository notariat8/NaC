export const nacWorkbenchHostStyleSheet = `
.nacWorkbenchHost{color:#17202a;container-name:nac-workbench-host;container-type:inline-size;font-family:Segoe UI,Arial,sans-serif;letter-spacing:0;max-width:100%;min-width:0}
.nacWorkbenchHost__tabs{border-bottom:1px solid #c8ced5;display:flex;gap:4px;margin:0 0 12px;padding:0}
.nacWorkbenchHost__tabs button{background:transparent;border:0;border-bottom:3px solid transparent;color:#3e4852;cursor:pointer;font:600 14px Segoe UI,Arial,sans-serif;min-height:40px;padding:8px 12px}
.nacWorkbenchHost__tabs button[aria-selected=true]{border-bottom-color:#0b6a75;color:#07535c}
.nacWorkbenchHost__tabs button:focus-visible{outline:3px solid #f5c242;outline-offset:2px}
.nacWorkbenchHost__tabpanel{max-width:100%;min-width:0}
.nacWorkbenchHost__tabpanel[hidden]{display:none}
.nacWorkbenchHost__state{background:#fff;border:1px solid #c8ced5;border-radius:6px;color:#3e4852;padding:18px}
.nacWorkbenchHost__state[role=alert]{border-color:#a12a32;color:#7d1f26}
@container nac-workbench-host (max-width:820px){.nacWorkbenchHost__tabpanel .nacWorkbench{grid-template-columns:1fr}.nacWorkbenchHost__tabpanel .nacWorkbench nav{display:flex;gap:4px;overflow:auto;padding:10px}.nacWorkbenchHost__tabpanel .nacWorkbench nav strong{margin:8px 10px}.nacWorkbenchHost__tabpanel .nacWorkbench nav button{display:inline-block;min-width:max-content;width:auto}.nacWorkbenchHost__tabpanel .nacWorkbench aside{border-left:0;border-top:1px solid var(--line)}.nacWorkbenchHost__tabpanel .nacWorkbench__grid{grid-template-columns:1fr}}
@container nac-workbench-host (max-width:440px){.nacWorkbenchHost__tabs button{flex:1;min-width:0;padding-left:8px;padding-right:8px}.nacWorkbenchHost__tabpanel .nacWorkbench main{padding:16px}.nacWorkbenchHost__tabpanel .nacWorkbench header{display:block}.nacWorkbenchHost__tabpanel .nacWorkbench__badge{display:inline-block;margin-top:12px}}
@supports not (container-type:inline-size){
@media(max-width:820px){.nacWorkbenchHost__tabpanel .nacWorkbench{grid-template-columns:1fr}.nacWorkbenchHost__tabpanel .nacWorkbench nav{display:flex;gap:4px;overflow:auto;padding:10px}.nacWorkbenchHost__tabpanel .nacWorkbench nav strong{margin:8px 10px}.nacWorkbenchHost__tabpanel .nacWorkbench nav button{display:inline-block;min-width:max-content;width:auto}.nacWorkbenchHost__tabpanel .nacWorkbench aside{border-left:0;border-top:1px solid var(--line)}.nacWorkbenchHost__tabpanel .nacWorkbench__grid{grid-template-columns:1fr}}
@media(max-width:440px){.nacWorkbenchHost__tabs button{flex:1;min-width:0;padding-left:8px;padding-right:8px}.nacWorkbenchHost__tabpanel .nacWorkbench main{padding:16px}.nacWorkbenchHost__tabpanel .nacWorkbench header{display:block}.nacWorkbenchHost__tabpanel .nacWorkbench__badge{display:inline-block;margin-top:12px}}
}
`;
