import { describe, it, expect } from 'vitest';
import { makeFindings } from '../FindingsWorkbench';

describe('makeFindings', () => {
  it('should return no findings for a valid claim', () => {
    const values = {
      patient_id: 'P1',
      provider_id: 'PR1',
      payer_id: 'PY1',
      service_date_from: '2026-01-01',
      total_amount: '100.00',
      lines: [
        { procedure_code: 'D0120', tooth_number: '', surface: '', charge_amount: '100.00' }
      ],
      narrative: 'Patient came in for a checkup.',
      attachments: []
    };
    const findings = makeFindings(values);
    expect(findings).toHaveLength(0);
  });

  it('should require a narrative for D7/D8 codes', () => {
    const values = {
      lines: [
        { procedure_code: 'D7110', charge_amount: '100.00' }
      ],
      narrative: '',
      attachments: []
    };
    const findings = makeFindings(values);
    expect(findings).toContainEqual(expect.objectContaining({ code: 'NARRATIVE_REQUIRED', severity: 'ERROR' }));
  });

  it('should require a radiograph for D7/D8 codes', () => {
    const values = {
      lines: [
        { procedure_code: 'D7110', charge_amount: '100.00' }
      ],
      narrative: 'Valid narrative',
      attachments: []
    };
    const findings = makeFindings(values);
    expect(findings).toContainEqual(expect.objectContaining({ code: 'RADIOGRAPH_REQUIRED', severity: 'ERROR' }));
  });

  it('should flag non-positive fees', () => {
    const values = {
      lines: [
        { procedure_code: 'D0120', charge_amount: '0.00' }
      ]
    };
    const findings = makeFindings(values);
    expect(findings).toContainEqual(expect.objectContaining({ code: 'NON_POSITIVE_FEE', severity: 'ERROR' }));
  });

  it('should flag line total mismatch', () => {
    const values = {
      total_amount: '100.00',
      lines: [
        { procedure_code: 'D0120', charge_amount: '50.00' }
      ]
    };
    const findings = makeFindings(values);
    expect(findings).toContainEqual(expect.objectContaining({ code: 'LINE_FEES_DO_NOT_SUM_TO_TOTAL', severity: 'ERROR' }));
  });
});
