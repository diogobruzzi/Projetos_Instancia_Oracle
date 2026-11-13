# CLAUDE.md - n8n Workflow Development Configuration

## Project Overview
This configuration supports n8n workflow development using the n8n MCP server and n8n skills. The goal is to create high-quality, production-ready n8n workflows for automation tasks.

## Key Resources
- **n8n MCP Server**: https://github.com/czlonkowski/n8n-mcp (v2.97.0+ required)
- **n8n Skills**: https://github.com/czlonkowski/n8n-skills (14 complementary skills)

---

## n8n MCP Server - Core Capabilities

### Installation Options
- **Fastest (Cloud)**: `dashboard.n8n-mcp.com` (free tier: 100 tool calls/day)
- **Self-hosted**: npx, Docker, Railway, local (see [Self-Hosting Guide](https://github.com/czlonkowski/n8n-mcp/docs/SELF_HOSTING.md))

### Required n8n Connection Configuration
```bash
# Required environment variables
N8N_API_URL=https://your-n8n-instance.com
N8N_API_KEY=your_n8n_api_key_here  # Use read-only key recommended

# Optional: Cloudflare Access
N8N_CF_CLIENT_ID=your_cf_client_id
N8N_CF_CLIENT_SECRET=your_cf_client_secret

# Optional: Instance-level MCP
N8N_MCP_ACCESS_TOKEN=from_n8n_settings_instance_mcp
```

### Core MCP Tools (7 - Always Available)
| Tool | Purpose |
|------|---------|
| `tools_documentation` | Get docs for any MCP tool |
| `search_nodes` | Full-text search across 3,434 nodes (842 core + 2,592 community) |
| `get_node` | Node info (modes: minimal/standard/full/docs/search_properties/versions) |
| `validate_node` | Validation (modes: minimal/full with profiles) |
| `validate_workflow` | Complete workflow validation with 99% property coverage |
| `search_templates` | Search 2,352 templates (modes: keyword/by_nodes/by_task/by_metadata) |
| `get_template` | Get workflow JSON (modes: nodes_only/structure/full) |

### n8n Management Tools (21 - Requires API Config)
**Workflow**: create, get, update (full/partial), delete, list, validate, autofix, versions, deploy_template
**Execution**: test_workflow, executions, evaluations
**Resources**: explore_node_resources (dynamic dropdowns), manage_folders, manage_datatable
**Credentials**: manage_credentials
**Security**: audit_instance
**Agents**: manage_agents (n8n 2.34+)
**System**: health_check, list_catalog

### Safety Controls
- Set `DISABLED_TOOLS` and `DISABLED_TOOL_OPERATIONS` to disable write/destructive operations
- Combine with read-only n8n API key for defense in depth
- **NEVER edit production workflows directly** — always copy, test in dev, export backups, validate before deploying

---

## n8n Skills - 14 Complementary Skills

### Installation
```bash
# Recommended: Via Claude Code
/plugin install czlonkowski/n8n-skills

# Manual
git clone https://github.com/czlonkowski/n8n-skills.git
cp -r n8n-skills/skills/* ~/.claude/skills/
```

### Prerequisites
- n8n-mcp MCP server v2.97.0+
- `.mcp.json` configured

### Available Skills

| Skill | Purpose |
|-------|---------|
| **n8n Expression Syntax** | Core variables ($json, $node, $now), webhook data under `$json.body`, helpers (.pluck(), .sum(), $ifEmpty()) |
| **n8n MCP Tools Expert** | Tool selection guide, nodeType formats, validation profiles, smart parameters |
| **n8n Workflow Patterns** | 5 proven patterns: webhook processing, HTTP API, database, AI, scheduled |
| **n8n Validation Expert** | Validation loop workflow, error catalog, auto-sanitization, false positives guide |
| **n8n Node Configuration** | Property dependencies, operation-specific requirements, 8 AI connection types |
| **n8n Code JavaScript** | Data access ($input.all()), return format `[{json:{...}}]`, built-in helpers, 10 production patterns |
| **n8n Code Python** | Sandbox limits (no classes, no imports unless allowlisted), 12 import-free patterns |
| **n8n Code Tool** | AI-agent callable tool, returns **string** (not array), `query`/`_query` input binding |
| **n8n Error Handling** | Per-node error output, retryOnFail, 4xx/5xx response mapping, Error Trigger workflows |
| **n8n Binary & Data** | `$binary` vs `$json`, binary preservation across Merge, agent-tool binary boundary |
| **n8n Sub-workflows** | Execute Workflow Trigger with typed inputs, `mode: all` vs `each`, verb-first naming |
| **n8n AI Agents** | Agent vs LLM Chain vs Text Classifier, `$fromAI` anatomy, structured output, chat topology |
| **n8n Multi-Instance** | Per-call `instance` argument, `n8n_instances` tool, switch as shared default |
| **n8n Self-Hosting** | Docker Compose + Caddy, single vs queue mode, secret generation, Day-2 operations |

### Automatic Skill Activation
Skills activate based on your query:
- `"How do I write n8n expressions?"` → **Expression Syntax**
- `"Find me a Slack node"` → **MCP Tools Expert**
- `"Build a webhook workflow"` → **Workflow Patterns**
- `"Why is validation failing?"` → **Validation Expert**
- `"How do I access webhook data in a Code node?"` → **Code JavaScript**
- `"Why does my Code Tool throw 'Wrong output type returned'?"` → **Code Tool**

---

## Development Workflow

### 1. Workflow Creation Process (Enhanced with MCP/Skills)
1. **Requirements Analysis** - Understand the automation need, inputs, outputs, and error handling requirements
2. **Template Search** - `search_templates()` for existing solutions before building from scratch
3. **Node Discovery** - `search_nodes()` for appropriate nodes, `get_node()` with `includeExamples: true`
4. **Pattern Selection** - Use **Workflow Patterns** skill for proven architectures
5. **Implementation** - Build with explicit parameters (never trust defaults), guided by **Node Configuration** skill
6. **Code Nodes** - Use **Code JavaScript/Python** skills for custom logic (native-first approach)
7. **Validation Loop** - `validate_node()` (minimal → full) → `validate_workflow()` → **Validation Expert** for errors
8. **Error Handling** - Apply **Error Handling** skill patterns
9. **Testing** - `test_workflow()` in development environment
10. **Documentation** - Document purpose, configuration, and usage
11. **Deployment** - Deploy via `n8n_create_workflow()` with proper credentials

### 2. Best Practices (MCP/Skills Enhanced)
- **Native-first**: Service node → native node → short expression → Code node
- **Webhook data**: Always under `$json.body` (see Expression Syntax skill)
- **Code node return**: `[{json: {...}}]` format (see Code JavaScript skill)
- **Code Tool return**: String — use `JSON.stringify()` (see Code Tool skill)
- **Explicit parameters**: Never trust defaults — specify all required properties
- **Validation necessary but not sufficient**: Hooks route to risk-owning skills after `validate_workflow`
- **Version control**: Export workflow JSON after each successful validation

### 3. Code Review Standards
- Check for hardcoded credentials (use n8n credential system via `manage_credentials`)
- Validate error handling paths (per-node error output, Error Trigger workflows)
- Ensure proper data transformation between nodes ($json vs $binary)
- Verify rate limiting and API quota considerations
- Check for memory-efficient processing of large datasets
- Validate workflow with `validate_workflow()` before deployment

---

## Workflow Building Flow Example
When building "webhook to Slack workflow":
1. **Workflow Patterns** identifies webhook processing pattern
2. **MCP Tools Expert** searches webhook/Slack nodes via `search_nodes()`
3. **Node Configuration** guides setup of each node
4. **Code JavaScript** handles `$json.body` access for webhook payload
5. **Expression Syntax** maps data between nodes
6. **Validation Expert** validates final workflow with `validate_workflow()`
7. **Error Handling** adds retry/fallback logic
8. Deploy via `n8n_create_workflow()` or export JSON

---

## Environment Setup

### n8n Instance Connection
```bash
# Primary n8n instance
N8N_API_URL=https://your-n8n-instance.com
N8N_API_KEY=your_read_only_api_key

# Development instance (separate from production)
N8N_DEV_API_URL=https://dev-n8n.yourdomain.com
N8N_DEV_API_KEY=dev_read_only_api_key
```

### MCP Server Configuration (.mcp.json)
```json
{
  "mcpServers": {
    "n8n-mcp": {
      "command": "npx",
      "args": ["-y", "n8n-mcp"],
      "env": {
        "N8N_API_URL": "https://your-n8n-instance.com",
        "N8N_API_KEY": "your_read_only_api_key"
      }
    }
  }
}
```

### Self-Hosted n8n (via n8n Self-Hosting skill)
```bash
# Docker Compose + Caddy (recommended)
# Single mode for dev, queue mode for production
# See n8n Self-Hosting skill for complete setup
```

---

## Workflow Categories
- **Data Processing** - ETL, transformation, validation workflows
- **API Integrations** - Third-party service connections
- **Automation** - Scheduled tasks, webhooks, triggers
- **Monitoring** - Health checks, alerts, reporting
- **Business Logic** - Complex decision trees, multi-step processes
- **AI Workflows** - Agent, LLM Chain, Text Classifier patterns (see AI Agents skill)

---

## Quality Checklist
Before considering a workflow complete:
- [ ] Template searched via `search_templates()` before custom build
- [ ] Nodes selected via `search_nodes()` and validated with `get_node(includeExamples: true)`
- [ ] Workflow executes without errors on test data via `test_workflow()`
- [ ] Validation passes: `validate_node()` (full) → `validate_workflow()`
- [ ] **Validation Expert** skill confirms no false positives
- [ ] Error handling covers all failure scenarios (per-node + Error Trigger)
- [ ] Credentials properly configured via `manage_credentials` (not hardcoded)
- [ ] Webhook data accessed via `$json.body` (Expression Syntax skill)
- [ ] Code nodes return `[{json: {...}}]` format (Code JavaScript skill)
- [ ] Code Tools return string via `JSON.stringify()` (Code Tool skill)
- [ ] Workflow documented with purpose, configuration, and usage
- [ ] Performance tested with expected data volumes
- [ ] Version controlled (JSON export committed)
- [ ] Environment-specific configs separated (dev/prod instances)

---

## Commands Reference

### MCP Tools (via n8n-mcp)
```bash
# Discovery
search_nodes(query: "slack webhook")
get_node(nodeType: "n8n-nodes-base.webhook", includeExamples: true)
search_templates(mode: "by_task", task: "data processing")
get_template(templateId: "xxx", mode: "full")

# Validation
validate_node(nodeType: "n8n-nodes-base.httpRequest", mode: "full")
validate_workflow(workflow: {...})

# Management (requires API key)
n8n_create_workflow(workflow: {...})
n8n_test_workflow(workflowId: "xxx", inputData: {...})
n8n_manage_credentials(action: "list")
```

### Skill Invocation (automatic based on query)
```
/skill n8n-expression-syntax
/skill n8n-mcp-tools-expert
/skill n8n-workflow-patterns
/skill n8n-validation-expert
# ... etc for all 14 skills
```

---

## Critical Reminders

### Safety First
- **NEVER edit production workflows directly with AI**
- Always: Make a copy → Test in development → Export backups → Validate → Deploy
- Use read-only API keys where possible
- Disable destructive tools via `DISABLED_TOOLS` in production

### Native-First Hierarchy
1. **Service node** (e.g., Slack, GitHub, Notion native nodes)
2. **Native n8n node** (HTTP Request, Function, IF, Switch, etc.)
3. **Short expression** (using Expression Syntax skill helpers)
4. **Code node** (JavaScript/Python - last resort)

### Validation Reality Check
- `validate_workflow()` is **necessary but not sufficient**
- Post-validation hooks route findings to risk-owning skills
- Always run **Validation Expert** skill for production workflows

---

## Directory Structure (Planned)
```
/home/ubuntu/
├── CLAUDE.md                          # This file
├── .mcp.json                          # MCP server config
├── workflows/                         # Version-controlled workflow JSONs
│   ├── data-processing/
│   ├── api-integrations/
│   ├── automation/
│   ├── monitoring/
│   └── business-logic/
├── templates/                         # Custom workflow templates
├── credentials/                       # Credential templates (not secrets!)
└── docs/                              # Workflow documentation
```

---

## Notes
- This CLAUDE.md will be updated as MCP server and skills are fully integrated
- Workflow templates and patterns will be added to `workflows/` directory
- Shared credentials and configurations managed via n8n's credential system (`manage_credentials` tool)
- For multi-instance setups, use **n8n Multi-Instance** skill with per-call `instance` argument
- Self-hosting guidance in **n8n Self-Hosting** skill (Docker Compose + Caddy, queue mode for production)