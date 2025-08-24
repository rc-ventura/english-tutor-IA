import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import PronunciationProgress from '../PronunciationProgress';

// Mock para react-tooltip
vi.mock('react-tooltip', () => ({
  Tooltip: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="tooltip">{children}</div>
  ),
}));

describe('PronunciationProgress', () => {
  it('should not render when recent score is null', () => {
    const { container } = render(
      <PronunciationProgress
        recent={null}
        average={null}
        trend={null}
      />
    );

    expect(container.firstChild).toBeNull();
  });

  it('should render only the recent score when showDetails is false', () => {
    render(
      <PronunciationProgress
        recent={75}
        average={80}
        trend="up"
        showDetails={false}
      />
    );

    // Deve mostrar o score recente
    const scoreElement = screen.getByText('75.0');
    expect(scoreElement).toBeInTheDocument();

    // Não deve mostrar o texto "Atual"
    expect(screen.queryByText('Atual')).not.toBeInTheDocument();

    // Não deve mostrar a média
    expect(screen.queryByText('80.0')).not.toBeInTheDocument();

    // Não deve mostrar tendência
    expect(screen.queryByText('↗️')).not.toBeInTheDocument();
  });

  it('should render full details when showDetails is true', () => {
    render(
      <PronunciationProgress
        recent={75}
        average={80}
        trend="up"
        showDetails={true}
      />
    );

    // Deve mostrar o score recente
    expect(screen.getByText('75.0')).toBeInTheDocument();

    // Deve mostrar o texto "Atual"
    expect(screen.getByText('Atual')).toBeInTheDocument();

    // Deve mostrar a média
    expect(screen.getByText('80.0')).toBeInTheDocument();

    // Deve mostrar o texto "Média"
    expect(screen.getByText('Média')).toBeInTheDocument();

    // Deve mostrar tendência
    expect(screen.getByText('↗️')).toBeInTheDocument();
  });

  it('should apply correct color class based on score value', () => {
    const { rerender } = render(
      <PronunciationProgress
        recent={90}
        average={null}
        trend={null}
      />
    );

    // Score alto (≥85) deve ter classe text-green-600
    let scoreElement = screen.getByText('90.0');
    expect(scoreElement.className).toContain('text-green-600');

    // Score médio (≥70 e <85) deve ter classe text-yellow-600
    rerender(<PronunciationProgress recent={75} average={null} trend={null} />);
    scoreElement = screen.getByText('75.0');
    expect(scoreElement.className).toContain('text-yellow-600');

    // Score baixo (<70) deve ter classe text-red-600
    rerender(<PronunciationProgress recent={60} average={null} trend={null} />);
    scoreElement = screen.getByText('60.0');
    expect(scoreElement.className).toContain('text-red-600');
  });

  it('should render different trend icons based on trend value', () => {
    const { rerender } = render(
      <PronunciationProgress
        recent={75}
        average={80}
        trend="up"
        showDetails={true}
      />
    );

    // Tendência "up" deve mostrar seta para cima
    expect(screen.getByText('↗️')).toBeInTheDocument();
    expect(screen.getByText('↗️').className).toContain('text-green-600');

    // Tendência "down" deve mostrar seta para baixo
    rerender(<PronunciationProgress recent={75} average={80} trend="down" showDetails={true} />);
    expect(screen.getByText('↘️')).toBeInTheDocument();
    expect(screen.getByText('↘️').className).toContain('text-red-600');

    // Tendência "stable" deve mostrar seta horizontal
    rerender(<PronunciationProgress recent={75} average={80} trend="stable" showDetails={true} />);
    expect(screen.getByText('→')).toBeInTheDocument();
    expect(screen.getByText('→').className).toContain('text-gray-600');
  });

  it('should render tooltip with correct information', () => {
    render(
      <PronunciationProgress
        recent={75}
        average={80}
        trend="up"
      />
    );

    const tooltip = screen.getByTestId('tooltip');

    // Verifica conteúdo do tooltip
    expect(tooltip).toHaveTextContent('Pontuação de pronúncia: 75.0/100');
    expect(tooltip).toHaveTextContent('Média (últimos 5): 80.0/100');
    expect(tooltip).toHaveTextContent('Tendência: Melhorando ↗️');
    expect(tooltip).toHaveTextContent('Baseado nas suas sessões de fala recentes');
  });
});
