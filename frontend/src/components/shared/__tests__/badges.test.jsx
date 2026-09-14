import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import '@testing-library/jest-dom';
import { ScorePill } from '../ScorePill';
import { SeverityBadge } from '../SeverityBadge';
import React from 'react';

describe('ScorePill', () => {
  it('should render green for high scores', () => {
    render(<ScorePill score={90} />);
    expect(screen.getByText('90%')).toHaveClass('text-emerald-700');
  });

  it('should render amber for medium scores', () => {
    render(<ScorePill score={70} />);
    expect(screen.getByText('70%')).toHaveClass('text-amber-700');
  });

  it('should render red for low scores', () => {
    render(<ScorePill score={50} />);
    expect(screen.getByText('50%')).toHaveClass('text-red-700');
  });
});

describe('SeverityBadge', () => {
  it('should render the correct label for HIGH severity', () => {
    render(<SeverityBadge severity="HIGH" />);
    expect(screen.getByText('High')).toBeInTheDocument();
  });

  it('should throw error for unknown severity', () => {
    // Suppress console.error for this test
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<SeverityBadge severity="UNKNOWN" />)).toThrow('Unknown severity: UNKNOWN');
    spy.mockRestore();
  });
});
