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

  http.get('/health', () => {
    return HttpResponse.json({
      status: 'ok',
    })
  }),
]
