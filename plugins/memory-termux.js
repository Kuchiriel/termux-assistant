// memory-termux.js — plugin de memoria/estado para o OpenCode 2.2.5 no Termux.
//
// PORTE do memory.js do host Linux (nixos-ai) para a API V2 (Effect/Promise hooks).
// O loader do 2.2.5 exige `export default` com `id` + `setup(ctx)` (o named export
// do Linux — `export const X = async () => ({...})` — e V1 e nao carrega aqui).
//
// REGRAS DE OURO (aprendidas no incidente de 07/11/2026):
//   - O hook "context" NUNCA pode fazer chamada de rede/spawn para descobrir o
//     modelo. O evento JA traz `event.model` e `event.sessionID`. Chamar a CLI
//     opencode aqui a cada mensagem derrubava o servidor (timeouts / ECONNRESET /
//     409 no MCP jarvis porque uma segunda conexao abrira o socket SSE).
//   - TA_STATE (execFileSync) roda no maximo 1x a cada CACHE_TTL_MS por processo,
//     mesmo que o hook rode dezenas de vezes.
//   - Qualquer erro no plugin NAO pode derrubar a sessao: tudo em try/catch.
//
// O QUE ELE FAZ
//   1. ctx.session.hook("context")  -> injeta no system prompt:
//        IDENTIDADE (model/provider/variante/session/host — o modelo nao se introspecta),
//        SESSION STATE (licoes da frota, pendencias, handoff, roster, malha) [1x/sessao],
//        REGRAS FIXAS (pinned — a compactacao destroi o que nao for pinned).
//   2. ctx.session.hook("compaction") -> garante que a compactacao SEMPRE produza
//        resumo: tenta resumir com um modelo; se falhar, devolve um resumo
//        deterministico do transcript (fallback). Isso mata o erro
//        "Compaction produced no summary".
//   3. ctx.tool.hook("execute.before") -> bloqueia delete recursivo SEM caminho
//        ancorado (`rm -rf /`, `rm -fr ~`, `rm -Rf /*`).
//
// A/B sem rebuild:
//   OPENCODE_NO_IDENTITY_INJECT=1 · OPENCODE_NO_STATE_INJECT=1 · OPENCODE_NO_REHYDRATE_INJECT=1
//   MEMORY_TERMUX_NO_COMPACTION_HOOK=1 (desliga o hook de compaction)
//   MEMORY_TERMUX_DEBUG=1 (escreve dump em ~/.local/state/memory-termux-debug.json)

import { execFileSync } from "node:child_process";
import { writeFileSync, mkdirSync, readFileSync, appendFileSync } from "node:fs";

const HOME = process.env.HOME || "${HOME}";
const STATE_CMD = process.env.TA_STATE_CMD || `${HOME}/bin/ta-state`;
const DEBUG = process.env.MEMORY_TERMUX_DEBUG === "1";
const DEBUG_FILE = `${HOME}/.local/state/memory-termux-debug.json`;
const STATE_MAX_CHARS = 4200;
const CACHE_TTL_MS = 10 * 60 * 1000;

// ---------- caches ----------
let stateCache = { at: 0, text: "" };      // cache global do processo
const debugSeen = new Set();
const sessionState = new Map();             // sessionID -> { at, len }
let identityCache = { at: 0, text: "" };    // fallback se o evento nao trouxer model

// (20/11) rastro do idle: distingue "hook nao disparou" de "fila vazia" e
// "budade bloqueado". Nao e segredo: so eventos, tarefa curta e decisao.
function traceIdle(data) {
  try {
    appendFileSync(`${HOME}/.local/state/auto-wake-idle.jsonl`,
      JSON.stringify({ ts: new Date().toISOString(), ...data }) + "\n");
  } catch {}
}

function debug(label, data) {
  if (!DEBUG) return;
  try {
    mkdirSync(`${HOME}/.local/state`, { recursive: true });
    let prev = [];
    try { prev = JSON.parse(readFileSync(DEBUG_FILE, "utf8")); } catch {}
    if (!Array.isArray(prev)) prev = [];
    prev.push({ ts: new Date().toISOString(), label, data });
    writeFileSync(DEBUG_FILE, JSON.stringify(prev.slice(-40), null, 1));
  } catch {}
}

// ta-state custa ~0.05s com cache interno, mas mesmo assim so roda 1x a cada 10 min.
function fetchState(force = false) {
  if (process.env.OPENCODE_NO_STATE_INJECT === "1") return "";
  const now = Date.now();
  if (!force && stateCache.text && now - stateCache.at < CACHE_TTL_MS) return stateCache.text;
  let out = "";
  try {
    out = execFileSync("bash", [STATE_CMD], {
      encoding: "utf8",
      timeout: 8000,
      maxBuffer: 1024 * 1024,
      env: { ...process.env },
    });
  } catch {}
  stateCache = { at: now, text: String(out || "").trim().slice(0, STATE_MAX_CHARS) };
  return stateCache.text;
}

// Fallback so quando o evento nao trouxer model (nunca deve acontecer no 2.2.5).
function readModelState() {
  const now = Date.now();
  if (identityCache.text && now - identityCache.at < 60000) return identityCache.text;
  try {
    const raw = JSON.parse(readFileSync(`${HOME}/.local/state/opencode/model.json`, "utf8"));
    const recent = (raw && raw.recent && raw.recent[0]) || {};
    if (recent.modelID) {
      const variant = (raw.variant && raw.variant[`${recent.providerID}/${recent.modelID}`]) || "";
      identityCache = { at: now, text: `${recent.providerID || "?"}/${recent.modelID}${variant ? ` (${variant})` : ""}` };
      return identityCache.text;
    }
  } catch {}
  return "unknown";
}

function buildIdentity(event, sessionID) {
  if (process.env.OPENCODE_NO_IDENTITY_INJECT === "1") return "";
  const m = (event && event.model) || {};
  const provider = m.providerID || "unknown";
  const id = m.id || m.modelID || readModelState();
  const variant = m.variant && m.variant !== "default" ? ` (${m.variant})` : "";
  const sid = event?.sessionID || sessionID || "unknown";
  return [
    "## IDENTITY (harness-provided — this is you)",
    `- model: ${provider}/${id}${variant}`,
    `- session: ${sid}`,
    "- host: termux (Motorola Edge, Termux, Android 11, tailnet ${TA_PHONE_IP:-100.104.175.123})",
    "You cannot introspect your own weights: this block is your identity.",
    "Never guess it and never claim to be a local or an API model without it.",
  ].join("\n");
}

const PINNED_GUARDS = `## Hard rules (pinned — never summarize, never rewrite)
- NEVER expose the owner's public IP: any test that needs anonymity goes through \`~/bin/egress-guard\`.
  Every credential test goes through \`~/bin/egress-guard\` (egress guard).
- NEVER delete user data without quarantine + manifest: \`Databases/\`, DCIM, Documents,
  Pictures, Music, Movies and WhatsApp backups are off limits. Use \`~/bin/phone-clean\`.
- Secrets never go to the bus, the repo, or the clipboard. Public keys only.
- \`pkill -f\` matches the shell's own command line: use PID or \`pgrep -f "padr[ao]"\`.
- Termux has no \`/tmp\` (use \`$PREFIX/tmp/opencode\`) and no \`df -Pm\` (use \`df -k\`).
- Before upgrading a package: stop the service, upgrade, restart, re-validate.
- Validate the PORT, not just the PID (an orphaned sshd has a dead socket after Tailscale
  recreates the interface — that is how a 29 GB log happened).
- The model identity is dynamic: ask \`~/bin/oc-identidade\`, never assume.`;

const REHYDRATE_RULE = `## Rehydration (first tool of a session)
Read the injected SESSION STATE first; it already carries the fleet's lessons, the pending
items, the handoff, the roster and the mesh status. When the state looks stale or a problem
looks like a repeat, run \`~/bin/ta-state\` (cached, ~0.05 s) and \`~/bin/mesh-repo pull\`.
Do not re-derive what the state already says: the fleet's failures are already paid for.
## Which tool (pick ONE)
- new session / after compaction / "already solved" -> \`~/bin/ta-state\`
- "what did we decide before" -> \`grep -rh '"kind":"decision"' ~/ai-mesh/memory/episodic/*.jsonl | jq -r .text\`
- a command FAILED and you are about to retry -> \`~/bin/ta-state\` (lessons)
- what another host has/needs -> \`~/bin/mesh-repo pull\` then read \`~/ai-mesh/manifests/*.json\`
- talk to another agent -> \`~/bin/coord-cli msg <codinome> "..."\` (delivers + wakes)
${PINNED_GUARDS}`;

const STATE_HEADER = "## SESSION STATE (auto-injected — ground truth; read the paths instead of re-deriving)\n";

// rm recursivo+forca apontando para /, ~ ou /* — flags em qualquer ordem, maiusculas.
const ROOT_DELETE =
  /(^|[;&|\s])rm\s+[^;&|]*-[a-zA-Z]*(?:[rR][a-zA-Z]*[fF]|[fF][a-zA-Z]*[rR])[^;&|]*\s+(\/(\s|$|;|\*)|\~(\s|$|;))/;

function appendSystem(event, block) {
  if (!block) return;
  try {
    const sys = event.system;
    if (Array.isArray(sys) && sys.length > 0 && typeof sys[0]?.text === "string") {
      sys[0].text = `${sys[0].text}\n\n${block}`;
      return;
    }
    if (Array.isArray(sys) && sys.length > 0) {
      sys[sys.length - 1] = {
        ...sys[sys.length - 1],
        text: `${sys[sys.length - 1]?.text ?? ""}\n\n${block}`,
      };
      return;
    }
    if (sys && typeof sys.text === "string") {
      sys.text = `${sys.text}\n\n${block}`;
    }
  } catch {}
}

// (15/11) FORMATO REAL das mensagens no evento de compactacao (medido):
//   user      -> { role:"user", content:"..." }  ou { text:"..." }
//   assistant -> { role:"assistant", content:[{type:"text",text:"..."}, {type:"tool-call",...}] }
//   tool      -> { role:"tool", content:[{type:"tool-result",...}] }
// O codigo antigo so olhava m.text / m.content STRING / m.parts — entao o
// assistant (content ARRAY) virava "" e o transcript chegava ao modelo como
// uma lista de marcadores vazios ("[user] [assistant] [tool]"). O modelo
// respondia "nao registrado" e a compactacao jogava o contexto fora.
function extractText(m) {
  const flat = (parts) => {
    if (!Array.isArray(parts)) return "";
    return parts
      .map((p) => {
        if (!p) return "";
        if (typeof p === "string") return p;
        if (typeof p.text === "string" && p.text.trim()) return p.text;
        const t = String(p.type || "");
        if (t === "tool-call" || t === "tool_call") {
          let a = "";
          try { a = JSON.stringify(p.input ?? p.args ?? p.arguments ?? {}); } catch {}
          return `[tool ${p.toolName || p.name || "?"}] ${a.slice(0, 400)}`;
        }
        if (t === "tool-result" || t === "tool_result") {
          let r = "";
          try { r = JSON.stringify(p.output ?? p.result ?? p.content ?? ""); } catch {}
          return `[tool-result] ${r.slice(0, 600)}`;
        }
        if (typeof p.content === "string") return p.content;
        if (Array.isArray(p.content)) return flat(p.content);
        return "";
      })
      .filter(Boolean)
      .join(" ");
  };
  let out = "";
  if (typeof m?.text === "string") out = m.text;
  else if (typeof m?.content === "string") out = m.content;
  else if (Array.isArray(m?.content)) out = flat(m.content);
  else if (Array.isArray(m?.parts)) out = flat(m.parts);
  if (!out && m?.data && typeof m.data === "object") out = extractText(m.data);
  return String(out || "").replace(/\s+/g, " ").trim();
}

// Rastro sempre-ligado (arquivo local, sem rede/spawn): prova qual transcript
// e qual modelo produziram cada resumo. Mantem as 6 ultimas entradas.
const COMPACTION_TRACE = `${HOME}/.local/state/memory-termux-compaction.json`;
function compactionTrace(entry) {
  try {
    mkdirSync(`${HOME}/.local/state`, { recursive: true });
    let prev = [];
    try { prev = JSON.parse(readFileSync(COMPACTION_TRACE, "utf8")); } catch {}
    if (!Array.isArray(prev)) prev = [];
    prev.push(entry);
    writeFileSync(COMPACTION_TRACE, JSON.stringify(prev.slice(-6), null, 1));
  } catch {}
}

// Resumo deterministico (fallback): nao depende de modelo nenhum.
function fallbackSummary(messages) {
  const lines = [];
  try {
    for (const m of messages || []) {
      const role = m?.role || m?.type || m?.info?.role || "msg";
      const text = extractText(m);
      if (!text) continue;
      lines.push(`- [${role}] ${text.slice(0, 300)}`);
    }
  } catch {}
  const head = lines.slice(-40).join("\n");
  return [
    "## Objective",
    "Continuar o trabalho da frota (TAB / Termux). O resumo abaixo e automatico",
    "e preserva o essencial do transcript; a memoria da frota esta em ~/ai-mesh/memory/episodic.",
    "",
    "## Transcript (tail)",
    head || "- (sem texto extraivel do transcript)",
    "",
    "## Next Move",
    "- Ler SESSION STATE (injetado) antes de agir.",
    "- Consultar ~/ai-mesh/memory/episodic/*.jsonl e o bus antes de rediagnosticar.",
  ].join("\n");
}

// (15/11) Um resumo e DEGENERADO quando tem so o esqueleto do template
// (os 8 cabecalhos, secoes vazias): foi assim que a compactacao jogou o
// contexto fora 5x (98-114 chars). Regra medida: confere o CONTEUDO, nao
// o status nem o tamanho bruto.
function summaryIsDegenerate(text) {
  const s = String(text || "").trim();
  if (s.length < 600) return true;
  // (15/11) resumo "bem formado" que confessa nao ter lido nada tambem e
  // degenerado: foi o que aconteceu as 14:46 (992 chars de "Nao registrado"
  // porque o transcript chegou vazio ao modelo).
  if (/n[ãa]o registrado|transcript (cont[eé]m|est[aá])? ?vazi|sem conte[úu]do de mensagens/i.test(s.slice(0, 600))) return true;
  const secoes = [
    "Objective", "Requirements", "Decisions", "Completed",
    "Active", "Blockers", "Next Move", "Files",
  ];
  // quantas secoes tem corpo de verdade (>= 15 chars ate o proximo "## ")
  let vazias = 0;
  for (const h of secoes) {
    const i = s.indexOf("## " + h);
    if (i < 0) { vazias += 1; continue; }
    const resto = s.slice(i + h.length + 3);
    const next = resto.search(/\n## /);
    const bloco = (next >= 0 ? resto.slice(0, next) : resto).trim();
    if (bloco.length < 15) vazias += 1;
  }
  if (vazias >= 5) return true;
  // e o texto fora dos cabecalhos precisa ter substancia
  let corpo = s;
  for (const h of secoes) corpo = corpo.split("## " + h).join("");
  corpo = corpo.replace(/[#\s*\-]/g, "");
  return corpo.length < 400;
}

function messageCount(event) {
  return Array.isArray(event?.messages) ? event.messages.length : 0;
}

// Injeta SESSION STATE no maximo 1x por sessao (ou quando a compactacao encolhe o transcript).
function shouldRehydrate(sessionID, event) {
  const len = messageCount(event);
  const prev = sessionState.get(sessionID);
  if (!prev) return true;
  // compactacao: o transcript encolheu => re-injeta
  if (len > 0 && prev.len > 0 && len < prev.len) return true;
  if (Date.now() - prev.at > CACHE_TTL_MS) return true;
  return false;
}

// Marcadores: provam em que nivel o plugin roda (modulo > setup > hook).
function mark(nivel, extra) {
  try {
    mkdirSync(`${HOME}/.local/state`, { recursive: true });
    writeFileSync(
      `${HOME}/.local/state/memory-termux-${nivel}.txt`,
      `${new Date().toISOString()} ${JSON.stringify(extra || {})}\n`,
    );
  } catch {}
}

mark("module", { file: "memory-termux.js" });

export default {
  id: "memory-termux",

  async setup(ctx) {
    mark("setup", { app: ctx?.app?.version });
    // ---------- 1. contexto do modelo: identidade + estado + regras ----------
    try {
      await ctx.session.hook("context", (event) => {
        try {
          const sessionID = event?.sessionID || "unknown";
          mark("hook-context", { sessionID });
          if (!debugSeen.has("cat:" + sessionID)) {
            debugSeen.add("cat:" + sessionID);
            const tnames = event?.tools instanceof Map
              ? [...event.tools.keys()]
              : Object.keys(event?.tools || {});
            mark("catalog", {
              n: tnames.length,
              github: tnames.filter((t) => t.startsWith("github_")).length,
              jarvis: tnames.filter((t) => t.startsWith("jarvis_")).length,
              contexto: tnames.filter((t) => t.startsWith("context7_")).length,
              sample: tnames.slice(0, 14),
            });
          }
          if (DEBUG && !debugSeen.has(sessionID)) {
            debugSeen.add(sessionID);
            debug("context", {
              keys: Object.keys(event || {}),
              model: event?.model,
              sessionID: event?.sessionID,
              agent: event?.agent,
            });
          }

          const blocks = [];
          const identity = buildIdentity(event, sessionID);
          if (identity) blocks.push(identity);

          if (shouldRehydrate(sessionID, event)) {
            const state = fetchState();
            if (state) {
              blocks.push(STATE_HEADER + state);
              if (process.env.OPENCODE_NO_REHYDRATE_INJECT !== "1") blocks.push(REHYDRATE_RULE);
              sessionState.set(sessionID, { at: Date.now(), len: messageCount(event) });
            }
          }
          appendSystem(event, blocks.join("\n\n"));
        } catch {}
      });
    } catch (e) {
      debug("context-hook-fail", { err: String(e) });
    }

    // ---------- 2. compactacao: sempre produzir resumo ----------
    if (process.env.MEMORY_TERMUX_NO_COMPACTION_HOOK !== "1") {
      try {
        await ctx.session.hook("compaction", async (event) => {
          try {
            if (DEBUG) {
              debug("compaction", {
                keys: Object.keys(event || {}),
                messages: messageCount(event),
                sessionID: event?.sessionID,
              });
            }
            // (15/11) so aceita o resumo PRONTO se ele NAO for degenerado:
            // o esqueleto do template (secoes vazias) conta como FALHA.
            const pronto = event?.result?.summary;
            if (typeof pronto === "string" && !summaryIsDegenerate(pronto)) return;
            const msgs = Array.isArray(event?.messages) ? event.messages : [];
            if (!msgs.length) return;

            // deterministico primeiro: nunca mais "Compaction produced no summary"
            const fallback = fallbackSummary(msgs);
            let summary = "";
            try {
              const transcript = msgs
                .map((m) => {
                  const t = extractText(m);
                  if (!t) return "";
                  const role = m?.role || m?.type || m?.info?.role || "msg";
                  return `[${role}] ${t.slice(0, 1200)}`;
                })
                .filter(Boolean)
                .join("\n")
                .slice(-60000);
              // (15/11) transcript vazio/irrelevante = resumo inutil. Nao
              // chama modelo (ele inventa "nao registrado" e isso passava
              // pelo filtro): cai direto no deterministico.
              if (transcript.length < 200) {
                compactionTrace({
                  at: new Date().toISOString(),
                  sessionID: event?.sessionID,
                  via: "fallback-transcript-curto",
                  msgs: msgs.length,
                  transcriptChars: transcript.length,
                  fallbackChars: fallback.length,
                });
                event.result = { summary: fallback };
                return;
              }
              const state = fetchState(true);
              const prompt = [
                "Resuma esta conversa de forma ESTRUTURADA e curta (em portugues do Brasil).",
                "Use exatamente estas secoes:",
                "## Objective / ## Requirements / ## Decisions / ## Completed / ## Active / ## Blockers / ## Next Move / ## Files",
                "Cite caminhos e comandos exatos. Nao invente. Se algo nao existir, omita.",
                "",
                "ESTADO DA FROTA (para nao perder o que ja foi pago):",
                state || "(sem estado)",
                "",
                "TRANSCRIPT:",
                transcript,
              ].join("\n");
              // (15/11) MEDIDO: o nemotron devolvia SO O ESQUELETO (98-114
              // chars, secoes vazias) e o filtro antigo (">40 chars")
              // aceitava — era a compactacao degenerada que jogava o
              // contexto fora. Agora:
              //   1. o candidato PRINCIPAL e o minimax (o mesmo que gravou
              //      7-11k chars com conteudo real na casa);
              //   2. TODA saida passa por summaryIsDegenerate();
              //   3. se todos falharem, cai no fallback DETERMINISTICO, que
              //      traz o tail do transcript — nunca fica vazio.
              const candidatos = [
                { providerID: "opencode", id: "minimax-m3.1-flash-free" },
                { providerID: "nvidia", id: "minimaxai/minimax-m3.1-flash" },
                { providerID: "opencode", id: "deepseek-v4.1-flash-free" },
              ];
              for (const cand of candidatos) {
                try {
                  const gen = await ctx.experimental.generate.text({ model: cand, prompt });
                  const text = typeof gen === "string" ? gen : gen?.text || gen?.content || "";
                  const limpo = String(text || "").trim();
                  if (!summaryIsDegenerate(limpo)) { summary = limpo; break; }
                  debug("compaction-degenerada", { modelo: cand.id, chars: limpo.length });
                } catch (e) {
                  debug("compaction-gen-fail", { modelo: cand.id, err: String(e) });
                }
              }
            } catch (e) {
              debug("compaction-gen-fail", { err: String(e) });
            }
            compactionTrace({
              at: new Date().toISOString(),
              sessionID: event?.sessionID,
              eventKeys: Object.keys(event || {}),
              msgs: msgs.length,
              amostra: msgs.slice(0, 4).map((m) => ({
                role: m?.role || m?.type || "?",
                keys: Object.keys(m || {}).slice(0, 8),
                contentKind: Array.isArray(m?.content) ? `array:${m.content.length}` : typeof m?.content,
                texto: extractText(m).slice(0, 90),
              })),
              via: summary ? "modelo" : "fallback",
              resumoChars: (summary || fallback).length,
            });
            event.result = { summary: summary || fallback };
          } catch (e) {
            debug("compaction-fail", { err: String(e) });
          }
        });
      } catch (e) {
        debug("compaction-hook-fail", { err: String(e) });
      }
    }

    // ---------- 3. guard de delete raiz ----------
    try {
      await ctx.tool.hook("execute.before", (event) => {
        try {
          const tool = String(event?.tool || "").toLowerCase();
          if (tool !== "bash" && tool !== "shell") return;
          const input = event?.input;
          if (!input || typeof input !== "object") return;
          const command = input.command;
          if (typeof command !== "string" || !command) return;
          if (ROOT_DELETE.test(command)) {
            input.command =
              "echo 'DENIED by memory-termux: unanchored root delete. " +
              "Rescue ladder: git commit > quarantine dir > verified snapshot. " +
              "Narrow the path.' >&2; exit 1";
          }
        } catch {}
      });
    } catch (e) {
      debug("tool-hook-fail", { err: String(e) });
    }

    // ---------- 4. trim do catalogo (meta-tool: gh CLI no lugar do MCP github) ----------
    // O MCP github expoe 46 tools: cada schema entra em TODO request (Code Mode
    // catalogo). O `gh` CLI esta autenticado (scopes repo/read:org/gist) e cobre
    // tudo — a skill `github-cli` ensina o padrao. Medido no Linux: 48 -> 19 tools
    // = -3.397 tok/request. Aqui: 46 tools do github saem do catalogo.
    // Reversivel: MEMORY_TERMUX_MCP_TRIM=0 (ou `disabled` no config) religa.
    if (process.env.MEMORY_TERMUX_MCP_TRIM !== "0") {
      try {
        await ctx.mcp.transform((editor) => {
          editor.update("github", (mcp) => {
            mcp.disabled = true;
          });
        });
        mark("mcp-trim", { github: "disabled", alternativa: "gh CLI + skill github-cli" });
      } catch (e) {
        debug("mcp-trim-fail", { err: String(e) });
      }
    }

    // ---------- 4. AUTO-ACORDAR (visivel NO TUI, nada de background) ----------
    // Quando a sessao termina o turno e fica ociosa, se houver auto-tarefa na fila,
    // o plugin ADMITE um prompt sintetico NA MESMA SESSAO: o agente continua
    // trabalhando e o dono VE isso na conversa do OpenCode.
    // Orcamento: max N wakes/hora + gap minimo (auto-wake); fila vazia = para.
    try {
      const runCmd = (args, timeoutMs = 12000) => {
        try {
          return execFileSync("bash", args, {
            encoding: "utf8",
            timeout: timeoutMs,
            maxBuffer: 1024 * 1024,
          });
        } catch {
          return "";
        }
      };
      await ctx.session.hook("experimental.idle", async (event) => {
        try {
          const sid = event?.sessionID || "";
          if (!sid) return;
          let nightSid = "";
          try {
            nightSid = readFileSync(`${HOME}/.local/state/night-session`, "utf8").trim();
          } catch {}
          if (nightSid && nightSid === sid) return;
          traceIdle({ event: "idle", sid: sid.slice(0, 40) });
          // (20/11) olhar a fila ANTES do budget: gastar o orcamento em idle
          // com fila vazia pode deixar a frota travada quando a tarefa chega.
          let task = String(runCmd([`${HOME}/bin/auto-wake`, "peek"], 12000) || "").trim();
          traceIdle({ event: "peek", found: !!task });
          if (!task) {
            runCmd([`${HOME}/bin/auto-improve`, "--once"], 60000);
            task = String(runCmd([`${HOME}/bin/auto-wake`, "peek"], 12000) || "").trim();
            traceIdle({ event: "refill", found: !!task });
          }
          if (!task) return;
          const budget = runCmd([`${HOME}/bin/auto-wake`, "budget"], 12000);
          const allowed = String(budget || "").includes("OK");
          traceIdle({ event: "budget", allowed });
          if (!allowed) return;
          task = String(runCmd([`${HOME}/bin/auto-wake`, "next"], 12000) || "").trim();
          if (!task) return;
          traceIdle({ event: "wake", task: task.slice(0, 100) });
          // Injetar /goal <tarefa> para o loop nativo do /goal continuar sozinho.
          // O objetivo e mantido no servidor (sobrevive a compactacao) e so para quando
          // o juiz diz "done"/"blocked" ou 50 rodadas / 3 stall s.
          // Assim o agente continua trabalhando sozinho ate provar a tarefa.
          const goalText = [
            "/goal " + task,
            "",
            "TURNO CONTINUO (auto-wake) — o dono nao esta presente; siga sem perguntar nada.",
            "",
            "Regras: meca antes de agir; nada de 'deve funcionar'; nao apague nada (use phone-fs propose",
            "para mover); nao reinicie o opencode; segredos fora do bus/repo; se precisar de acao do dono,",
            "registre no bus e siga com o resto.",
            "Ao concluir com sucesso, marque ESTA tarefa como concluida:",
            "auto-wake complete \"<a mesma tarefa>\" --reason \"<evidencia>\".",
            "Se ela continuar pendente, devolva com auto-wake requeue \"<a mesma tarefa>\" --reason \"<motivo>\".",
            "Depois escreva 1 linha de status e ENFILEIRE a proxima tarefa com",
            "auto-wake enqueue (ou pare se nao houver mais nada util).",
          ].join("\n");
          await ctx.session.synthetic({ sessionID: sid, text: goalText });
          // (20/11) precisão por wake: snapshot idempotente em JSONL, alimenta
          // o gate que só amplia MAX_REMOTE com 10 wakes e precisão >=0,8.
          runCmd([`${HOME}/bin/auto-improve`, "--snapshot"], 60000);
          mark("auto-wake", { sessionID: sid, task: task.slice(0, 120) });
        } catch (e) {
          debug("auto-wake-fail", { err: String(e) });
        }
      });
      mark("auto-wake-hook", { registrado: true });
    } catch (e) {
      debug("auto-wake-hook-fail", { err: String(e) });
      mark("auto-wake-hook-fail", { err: String(e).slice(0, 160) });
    }

    return () => {};
  },
};
