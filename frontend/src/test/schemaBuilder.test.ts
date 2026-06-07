/**
 * Tests for the parameter schema builder logic used in ToolBuilder.
 * These are pure functions — no React needed.
 */

interface Param {
  name: string
  type: string
  description: string
  required: boolean
}

function paramsToSchema(params: Param[]): Record<string, unknown> {
  const props: Record<string, unknown> = {}
  const required: string[] = []
  for (const p of params) {
    props[p.name] = { type: p.type, description: p.description }
    if (p.required) required.push(p.name)
  }
  return { type: 'object', properties: props, required }
}

function schemaToParams(schema: Record<string, unknown>): Param[] {
  const props = (schema.properties as Record<string, Record<string, string>>) ?? {}
  const req = (schema.required as string[]) ?? []
  return Object.entries(props).map(([name, def]) => ({
    name,
    type: def.type ?? 'string',
    description: def.description ?? '',
    required: req.includes(name),
  }))
}

describe('paramsToSchema', () => {
  test('empty params produces empty schema', () => {
    expect(paramsToSchema([])).toEqual({ type: 'object', properties: {}, required: [] })
  })

  test('single optional param', () => {
    const schema = paramsToSchema([{ name: 'q', type: 'string', description: 'query', required: false }])
    expect(schema).toEqual({
      type: 'object',
      properties: { q: { type: 'string', description: 'query' } },
      required: [],
    })
  })

  test('required param appears in required array', () => {
    const schema = paramsToSchema([{ name: 'q', type: 'string', description: '', required: true }])
    expect((schema.required as string[])).toContain('q')
  })

  test('mixed required and optional', () => {
    const params: Param[] = [
      { name: 'q', type: 'string', description: 'search query', required: true },
      { name: 'limit', type: 'integer', description: 'max results', required: false },
    ]
    const schema = paramsToSchema(params)
    expect((schema.required as string[])).toEqual(['q'])
    expect((schema.properties as Record<string, unknown>)).toHaveProperty('limit')
  })

  test('preserves all types', () => {
    const types = ['string', 'number', 'integer', 'boolean', 'array', 'object']
    const params = types.map(t => ({ name: t, type: t, description: '', required: false }))
    const schema = paramsToSchema(params)
    for (const t of types) {
      expect((schema.properties as Record<string, Record<string, string>>)[t].type).toBe(t)
    }
  })
})

describe('schemaToParams', () => {
  test('empty schema produces empty params', () => {
    expect(schemaToParams({ type: 'object', properties: {}, required: [] })).toEqual([])
  })

  test('single param roundtrip', () => {
    const params: Param[] = [{ name: 'q', type: 'string', description: 'search', required: true }]
    expect(schemaToParams(paramsToSchema(params))).toEqual(params)
  })

  test('missing required array defaults to not required', () => {
    const schema = { type: 'object', properties: { x: { type: 'number', description: '' } } }
    const params = schemaToParams(schema)
    expect(params[0].required).toBe(false)
  })

  test('missing type defaults to string', () => {
    const schema = { type: 'object', properties: { x: { description: 'no type' } }, required: [] }
    const params = schemaToParams(schema)
    expect(params[0].type).toBe('string')
  })
})

describe('paramsToSchema / schemaToParams roundtrip', () => {
  test('complex params survive roundtrip', () => {
    const params: Param[] = [
      { name: 'query', type: 'string', description: 'search query', required: true },
      { name: 'limit', type: 'integer', description: 'max results', required: false },
      { name: 'include_metadata', type: 'boolean', description: '', required: false },
    ]
    expect(schemaToParams(paramsToSchema(params))).toEqual(params)
  })
})
