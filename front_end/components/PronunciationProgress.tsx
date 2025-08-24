import React from 'react';
import { Tooltip } from 'react-tooltip';

// Interfaces
interface PronunciationProgressProps {
  recent: number | null;
  average: number | null;
  trend: "up" | "down" | "stable" | null;
  showDetails?: boolean;
}

/**
 * Componente para exibir o progresso de pronúncia
 * Mostra score recente, média e tendência
 */
const PronunciationProgress: React.FC<PronunciationProgressProps> = ({
  recent,
  average,
  trend,
  showDetails = false,
}) => {
  if (recent === null) {
    return null;
  }

  // Formatação dos números
  const formatScore = (score: number | null) => {
    if (score === null) return '-';
    return score.toFixed(1);
  };

  // Ícone de tendência
  const getTrendIcon = () => {
    if (trend === 'up') {
      return '↗️';
    } else if (trend === 'down') {
      return '↘️';
    } else if (trend === 'stable') {
      return '→';
    }
    return '';
  };

  // Cor de tendência
  const getTrendColor = () => {
    if (trend === 'up') {
      return 'text-green-600';
    } else if (trend === 'down') {
      return 'text-red-600';
    }
    return 'text-gray-600';
  };

  // Função para determinar a classe de cor baseada no score
  const getScoreColorClass = (score: number | null) => {
    if (score === null) return 'text-gray-500';
    if (score >= 85) return 'text-green-600';
    if (score >= 70) return 'text-yellow-600';
    return 'text-red-600';
  };

  // ID para tooltips
  const tooltipId = `pronunciation-progress-${Date.now().toString().slice(-6)}`;

  return (
    <div className="pronunciation-progress flex items-center gap-2">
      {/* Score recente */}
      <div className="flex flex-col items-center justify-center">
        <div className={`text-lg font-bold ${getScoreColorClass(recent)}`} data-tooltip-id={tooltipId}>
          {formatScore(recent)}
        </div>
        {showDetails && (
          <div className="text-xs text-gray-600">Atual</div>
        )}
      </div>

      {/* Mostrar detalhes adicionais quando showDetails é true */}
      {showDetails && average !== null && (
        <>
          {/* Tendência */}
          <div className={`text-lg ${getTrendColor()}`}>
            {getTrendIcon()}
          </div>

          {/* Média */}
          <div className="flex flex-col items-center justify-center">
            <div className={`text-lg font-bold ${getScoreColorClass(average)}`}>
              {formatScore(average)}
            </div>
            <div className="text-xs text-gray-600">Média</div>
          </div>
        </>
      )}

      {/* Tooltip */}
      <Tooltip id={tooltipId} place="top">
        <div className="text-sm">
          <p><strong>Pontuação de pronúncia:</strong> {formatScore(recent)}/100</p>
          {average !== null && (
            <p><strong>Média (últimos 5):</strong> {formatScore(average)}/100</p>
          )}
          {trend && (
            <p>
              <strong>Tendência:</strong> {' '}
              {trend === 'up' && 'Melhorando ↗️'}
              {trend === 'down' && 'Piorando ↘️'}
              {trend === 'stable' && 'Estável →'}
            </p>
          )}
          <p className="text-xs mt-1">Baseado nas suas sessões de fala recentes</p>
        </div>
      </Tooltip>
    </div>
  );
};

export default PronunciationProgress;
