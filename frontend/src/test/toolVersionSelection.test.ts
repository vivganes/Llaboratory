/**
 * Unit tests for the tool-version selection logic extracted from PlanBuilder.
 * These test the pure functions that manage which tool version IDs are selected,
 * ensuring the bug (multiple versions of the same tool being silently included)
 * cannot regress.
 */
import type { Tool, ToolVersion } from '../types'

// ── helpers mirroring PlanBuilder logic ──────────────────────────────────────

function makeVersion(toolId: string, versionNumber: number): ToolVersion {
  return {
    id: `${toolId}-v${versionNumber}`,
    tool_id: toolId,
    version_number: versionNumber,
    created_at: '2024-01-01T00:00:00Z',
    display_name: `tool_${toolId}`,
    model_facing_description: '',
    parameter_schema: { type: 'object', properties: {} },
    response_mode: 'static',
    static_response: {},
    dynamic_code: null,
    dynamic_approved: 1,
  }
}

function makeTool(id: string, versionCount: number): Tool {
  return {
    id,
    name: `Tool ${id}`,
    description: '',
    tags: [],
    created_at: '2024-01-01T00:00:00Z',
    versions: Array.from({ length: versionCount }, (_, i) => makeVersion(id, i + 1)),
  }
}

function selectedVersionForTool(toolId: string, allTools: Tool[], selectedIds: string[]): string | null {
  const tool = allTools.find(t => t.id === toolId)
  if (!tool) return null
  return tool.versions.find(v => selectedIds.includes(v.id))?.id ?? null
}

function toggleTool(tool: Tool, selectedIds: string[]): string[] {
  const current = selectedVersionForTool(tool.id, [tool], selectedIds)
  if (current) {
    return selectedIds.filter(id => id !== current)
  }
  const latest = tool.versions[tool.versions.length - 1]
  return latest ? [...selectedIds, latest.id] : selectedIds
}

function changeToolVersion(toolId: string, newVersionId: string, allTools: Tool[], selectedIds: string[]): string[] {
  const tool = allTools.find(t => t.id === toolId)
  if (!tool) return selectedIds
  const allVersionIds = tool.versions.map(v => v.id)
  return [...selectedIds.filter(id => !allVersionIds.includes(id)), newVersionId]
}

// ── tests ─────────────────────────────────────────────────────────────────────

describe('selectedVersionForTool', () => {
  const tools = [makeTool('a', 3), makeTool('b', 2)]

  test('returns null when no version selected', () => {
    expect(selectedVersionForTool('a', tools, [])).toBeNull()
  })

  test('returns matching version id', () => {
    expect(selectedVersionForTool('a', tools, ['a-v2'])).toBe('a-v2')
  })

  test('returns null for unknown tool', () => {
    expect(selectedVersionForTool('z', tools, ['a-v1'])).toBeNull()
  })

  test('only one version per tool can be active', () => {
    // If somehow both v1 and v2 are in the list, returns the first match
    const result = selectedVersionForTool('a', tools, ['a-v1', 'a-v2'])
    expect(result).toBe('a-v1')
  })
})

describe('toggleTool', () => {
  const tool = makeTool('a', 3)

  test('selecting an unselected tool adds the latest version', () => {
    const result = toggleTool(tool, [])
    expect(result).toContain('a-v3')
    expect(result).toHaveLength(1)
  })

  test('deselecting removes the selected version', () => {
    const result = toggleTool(tool, ['a-v2'])
    expect(result).not.toContain('a-v2')
    expect(result).toHaveLength(0)
  })

  test('toggling does not affect other tools', () => {
    const result = toggleTool(tool, ['b-v1'])
    expect(result).toContain('b-v1')
    expect(result).toContain('a-v3')
  })

  test('deselecting does not affect other tools', () => {
    const result = toggleTool(tool, ['a-v1', 'b-v1'])
    expect(result).not.toContain('a-v1')
    expect(result).toContain('b-v1')
  })
})

describe('changeToolVersion', () => {
  const tools = [makeTool('a', 3), makeTool('b', 2)]

  test('replaces old version with new version for same tool', () => {
    const result = changeToolVersion('a', 'a-v3', tools, ['a-v1', 'b-v1'])
    expect(result).toContain('a-v3')
    expect(result).not.toContain('a-v1')
    expect(result).toContain('b-v1')
  })

  test('never includes two versions of the same tool', () => {
    const result = changeToolVersion('a', 'a-v2', tools, ['a-v1'])
    const aVersions = result.filter(id => id.startsWith('a-'))
    expect(aVersions).toHaveLength(1)
    expect(aVersions[0]).toBe('a-v2')
  })

  test('does nothing for unknown tool', () => {
    const initial = ['a-v1', 'b-v1']
    const result = changeToolVersion('z', 'z-v1', tools, initial)
    expect(result).toEqual(initial)
  })
})

describe('round-trip: load plan then change version', () => {
  const tools = [makeTool('search', 2), makeTool('calc', 1)]

  test('plan with v1 selected shows v1, upgrade to v2 keeps only v2', () => {
    // Plan was saved with v1
    const initialSelected = ['search-v1']

    // User changes to v2
    const after = changeToolVersion('search', 'search-v2', tools, initialSelected)

    expect(after).toContain('search-v2')
    expect(after).not.toContain('search-v1')
    expect(after).toHaveLength(1)
  })

  test('multiple tools can each independently have versions changed', () => {
    let selected = ['search-v1', 'calc-v1']
    selected = changeToolVersion('search', 'search-v2', tools, selected)
    expect(selected).toContain('search-v2')
    expect(selected).toContain('calc-v1')
    expect(selected).toHaveLength(2)
  })
})
