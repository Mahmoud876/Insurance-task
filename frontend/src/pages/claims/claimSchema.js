import { z } from 'zod';

const moneyString = z
  .string()
  .transform((value) => value.trim())
  .pipe(
   z
     .string()
     .refine(
       (value) => value === '' || /^[-+]?(?:\d+\.?\d*|\d*\.\d+)$/.test(value),
       'Enter a valid currency amount',
     ),
  );

export const claimLineSchema = z.object({
  procedure_code: z.string().trim().min(1, 'Procedure code is required'),
  tooth_number: z.string().optional().or(z.literal('')),
  surface: z.string().optional().or(z.literal('')),
  charge_amount: moneyString.default(''),
});

export const claimSchema = z.object({
  patient_id: z.string().trim().min(1, 'Patient is required'),
  provider_id: z.string().trim().min(1, 'Provider is required'),
  payer_id: z.string().optional().or(z.literal('')),
  service_date_from: z.string().min(1, 'Service date is required'),
  service_date_to: z.string().min(1, 'Service date is required'),
  total_amount: moneyString.default(''),
  lines: z.array(claimLineSchema).min(1, 'At least one line item is required'),
});

export const defaultClaimValues = {
  patient_id: '',
  provider_id: '',
  payer_id: '',
  service_date_from: '',
  service_date_to: '',
  total_amount: '0.00',
  lines: [
   {
     procedure_code: '',
     tooth_number: '',
     surface: '',
     charge_amount: '',
   },
  ],
};

export const createEmptyLine = () => ({
  procedure_code: '',
  tooth_number: '',
  surface: '',
  charge_amount: '',
});

