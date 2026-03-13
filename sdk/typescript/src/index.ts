/**
 * StateWeave TypeScript SDK — Universal Schema Types
 *
 * Core type definitions for consuming StateWeave payloads in TypeScript/JavaScript.
 * This enables interoperability with Node.js agent frameworks.
 *
 * @example
 * ```ts
 * import { StateWeavePayload, CognitiveState } from '@stateweave/sdk';
 *
 * const payload: StateWeavePayload = JSON.parse(rawBytes);
 * console.log(payload.cognitive_state.conversation_history);
 * ```
 */

// ── Core Schema Types ──

export type MessageRole = "human" | "ai" | "system" | "tool";

export interface Message {
  role: MessageRole;
  content: string;
  name?: string;
  tool_call_id?: string;
  metadata?: Record<string, unknown>;
}

export interface GoalNode {
  goal_id: string;
  description: string;
  status: "active" | "completed" | "failed" | "pending";
  sub_goals?: string[];
  priority?: number;
}

export interface CognitiveState {
  conversation_history: Message[];
  working_memory: Record<string, unknown>;
  goal_tree: Record<string, GoalNode>;
  tool_results_cache: Record<string, unknown>;
  trust_parameters: Record<string, unknown>;
  long_term_memory: Record<string, unknown>;
  episodic_memory: Array<Record<string, unknown>>;
}

export interface AgentMetadata {
  agent_id: string;
  agent_name?: string;
  created_at?: string;
  access_policy?: string;
  retention_policy?: string;
  custom_metadata?: Record<string, unknown>;
}

export type NonPortableSeverity = "INFO" | "WARNING" | "CRITICAL";

export interface NonPortableWarning {
  field: string;
  reason: string;
  severity: NonPortableSeverity;
  source_framework: string;
  remediation?: string;
}

export interface AuditEntry {
  timestamp: string;
  action: string;
  source_framework?: string;
  target_framework?: string;
  agent_id?: string;
  details?: Record<string, unknown>;
}

export interface PayloadSignature {
  algorithm: string;
  public_key_id: string;
  signature_b64: string;
  signed_at?: string;
}

export interface StateWeavePayload {
  stateweave_version: string;
  schema_version: string;
  source_framework: string;
  cognitive_state: CognitiveState;
  metadata: AgentMetadata;
  audit_trail: AuditEntry[];
  non_portable_warnings: NonPortableWarning[];
  signature?: PayloadSignature;
  created_at: string;
}

// ── Diff Types ──

export type DiffChangeType = "added" | "removed" | "modified";

export interface DiffEntry {
  path: string;
  change_type: DiffChangeType;
  old_value?: unknown;
  new_value?: unknown;
}

export interface DiffReport {
  entries: DiffEntry[];
  added_count: number;
  removed_count: number;
  modified_count: number;
}

// ── REST API Types ──

export interface HealthResponse {
  status: "healthy";
  version: string;
  adapters: number;
}

export interface AdapterInfo {
  name: string;
  tier: "tier_1" | "tier_2" | "community";
  framework_name: string;
}

export interface ExportRequest {
  framework: string;
  agent_id: string;
}

export interface ImportRequest {
  framework: string;
  payload: StateWeavePayload;
}

export interface DetectRequest {
  state: Record<string, unknown>;
}

export interface DetectResponse {
  detected_framework: string;
}

// ── Client ──

/**
 * StateWeave REST API client.
 *
 * @example
 * ```ts
 * const client = new StateWeaveClient("http://localhost:8080");
 * const health = await client.health();
 * const adapters = await client.adapters();
 * ```
 */
export class StateWeaveClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://localhost:8080") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  async health(): Promise<HealthResponse> {
    const res = await fetch(`${this.baseUrl}/health`);
    return res.json();
  }

  async adapters(): Promise<{ adapters: AdapterInfo[] }> {
    const res = await fetch(`${this.baseUrl}/adapters`);
    return res.json();
  }

  async schema(): Promise<Record<string, unknown>> {
    const res = await fetch(`${this.baseUrl}/schema`);
    return res.json();
  }

  async exportState(framework: string, agentId: string): Promise<StateWeavePayload> {
    const res = await fetch(`${this.baseUrl}/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ framework, agent_id: agentId }),
    });
    return res.json();
  }

  async importState(framework: string, payload: StateWeavePayload): Promise<unknown> {
    const res = await fetch(`${this.baseUrl}/import`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ framework, payload }),
    });
    return res.json();
  }

  async detect(state: Record<string, unknown>): Promise<DetectResponse> {
    const res = await fetch(`${this.baseUrl}/detect`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ state }),
    });
    return res.json();
  }

  async diff(stateA: StateWeavePayload, stateB: StateWeavePayload): Promise<DiffReport> {
    const res = await fetch(`${this.baseUrl}/diff`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ state_a: stateA, state_b: stateB }),
    });
    return res.json();
  }
}
