import { http, HttpResponse } from 'msw'

const claims = [
  {
    id: '07ac22e7-64f8-4129-9c78-3e96710ffaa2',
    patient_id: 'ff990597-4eb2-4275-91de-ded1f2910bc5',
    provider_id: '1424ae2b-7343-4bf1-9f49-123456789abc',
    status: 'DRAFT',
    total_amount: '100.00',
  },
]

const procedureCodes = [
  { code: 'D0120', category: 'preventive', short_desc: 'Periodic oral evaluation', requires_tooth: false, requires_surface: false, requires_quadrant: false },
  { code: 'D1110', category: 'preventive', short_desc: 'Prophylaxis - adult', requires_tooth: false, requires_surface: false, requires_quadrant: false },
  { code: 'D2140', category: 'restorative', short_desc: 'Amalgam 1 surface', requires_tooth: true, requires_surface: true, requires_quadrant: false },
  { code: 'D2740', category: 'restorative', short_desc: 'Crown porcelain fused to high noble metal', requires_tooth: true, requires_surface: false, requires_quadrant: false },
  { code: 'D4355', category: 'perio', short_desc: 'Full mouth debridement', requires_tooth: false, requires_surface: false, requires_quadrant: false },
  { code: 'D7210', category: 'oral_surgery', short_desc: 'Extraction, erupted tooth or exposed root', requires_tooth: true, requires_surface: false, requires_quadrant: false },
  { code: 'D0274', category: 'diagnostic', short_desc: 'Bitewings 4 images', requires_tooth: false, requires_surface: false, requires_quadrant: false },
  { code: 'D2392', category: 'restorative', short_desc: 'Composite 2 surfaces posterior', requires_tooth: true, requires_surface: true, requires_quadrant: false },
]

export const handlers = [
  http.post('/v1/claims', async ({ request }) => {
    const body = await request.json()

    const claim = {
      id: crypto.randomUUID(),
      patient_id: body.patient_id,
      provider_id: body.provider_id,
      status: 'DRAFT',
      total_amount: body.total_amount ?? '0.00',
    }

    claims.push(claim)

    return HttpResponse.json(claim, { status: 201 })
  }),

  http.get('/v1/claims', () => {
    return HttpResponse.json({
      items: claims,
      next_cursor: null,
    })
  }),

  http.get('/v1/claims/:claim_id', ({ params }) => {
    const claim = claims.find((claim) => claim.id === params.claim_id)

    if (!claim) {
      return HttpResponse.json(
        { detail: 'Claim not found' },
        { status: 404 },
      )
    }

    return HttpResponse.json(claim)
  }),

  http.patch('/v1/claims/:claim_id', async ({ params, request }) => {
    const claim = claims.find((claim) => claim.id === params.claim_id)

    if (!claim) {
      return HttpResponse.json(
        { detail: 'Claim not found' },
        { status: 404 },
      )
    }

    const body = await request.json()

    if (body.status !== undefined) {
      claim.status = body.status
    }

    if (body.total_amount !== undefined) {
      claim.total_amount = body.total_amount
    }

    return HttpResponse.json(claim)
  }),

  http.delete('/v1/claims/:claim_id', ({ params }) => {
    const index = claims.findIndex(
      (claim) => claim.id === params.claim_id,
    )

    if (index === -1) {
      return HttpResponse.json(
        { detail: 'Claim not found' },
        { status: 404 },
      )
    }

    claims.splice(index, 1)

    return new HttpResponse(null, { status: 204 })
  }),

  http.put('/v1/claims/:claim_id/lines', async ({ params, request }) => {
    const claim = claims.find((claim) => claim.id === params.claim_id)

    if (!claim) {
      return HttpResponse.json(
        { detail: 'Claim not found' },
        { status: 404 },
      )
    }

    const lines = await request.json()

    return HttpResponse.json(
      lines.map((line) => ({
        id: crypto.randomUUID(),
        procedure_code: line.procedure_code,
        tooth_number: line.tooth_number ?? null,
        surface: line.surface ?? null,
        charge_amount: String(line.charge_amount),
      })),
    )
  }),

  http.get('/v1/reference/procedure-codes', ({ request }) => {
    const url = new URL(request.url)
    const query = (url.searchParams.get('query') ?? '').trim().toLowerCase()

    const matches = procedureCodes.filter((code) => {
      if (!query) {
        return true
      }

      return (
        code.code.toLowerCase().includes(query) ||
        code.category.toLowerCase().includes(query) ||
        code.short_desc.toLowerCase().includes(query)
      )
    })

    return HttpResponse.json(matches.slice(0, 8))
  }),

  http.get('/health', () => {
    return HttpResponse.json({
      status: 'ok',
    })
  }),
]
