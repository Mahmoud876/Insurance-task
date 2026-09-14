import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import '@testing-library/jest-dom';
import { useState } from 'react';
import ProcedureCodeInput from '../ProcedureCodeInput';

afterEach(() => {
  cleanup();
});

function TestWrapper() {
  const [value, setValue] = useState('');
  return <ProcedureCodeInput value={value} onChange={setValue} />;
}

describe('ProcedureCodeInput', () => {
  it('should call onChange when text is entered', () => {
    const onChange = vi.fn();
    render(<ProcedureCodeInput value="" onChange={onChange} />);

    const input = screen.getByPlaceholderText('Procedure');
    fireEvent.change(input, { target: { value: 'd0120' } });

    expect(onChange).toHaveBeenCalledWith('D0120');
  });

  it('should fetch and show options when typing', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [
        { code: 'D0120', category: 'Preventive' },
        { code: 'D0140', category: 'Preventive' }
      ]
    });

    render(<TestWrapper />);

    const input = screen.getByPlaceholderText('Procedure');
    fireEvent.change(input, { target: { value: 'D01' } });

    await waitFor(() => {
      expect(screen.getByText('D0120')).toBeInTheDocument();
    }, { timeout: 2000 });

    expect(screen.getByText('D0140')).toBeInTheDocument();
  });

  it('should select an option when clicked', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [
        { code: 'D0120', category: 'Preventive' }
      ]
    });

    render(<TestWrapper />);

    const input = screen.getByPlaceholderText('Procedure');
    fireEvent.change(input, { target: { value: 'D01' } });

    const option = await screen.findByText('D0120', {}, { timeout: 2000 });
    fireEvent.click(option);

    expect(screen.getByDisplayValue('D0120')).toBeInTheDocument();
  });
});
