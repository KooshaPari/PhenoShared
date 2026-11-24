/**
 * RICE Score Card Component
 * Reach, Impact, Confidence, Effort scoring for product prioritization
 */

import { useState } from "react";

import { cn } from "@/lib/utils";

interface RICEScore {
  reach: number;
  impact: number;
  confidence: number;
  effort: number;
  rice_score: number;
}

interface RICEScoreCardProps {
  initialValues?: Partial<RICEScore>;
  onCalculate?: (score: RICEScore) => void;
  readOnly?: boolean;
  className?: string;
}

const impactLevels = [
  { description: "3x improvement", label: "Massive", value: 3 },
  { description: "2x improvement", label: "High", value: 2 },
  { description: "Notable improvement", label: "Medium", value: 1 },
  { description: "Minor improvement", label: "Low", value: 0.5 },
  { description: "Barely noticeable", label: "Minimal", value: 0.25 },
];

const confidenceLevels = [
  { description: "Strong evidence", label: "High", value: 100 },
  { description: "Some evidence", label: "Medium", value: 80 },
  { description: "Limited evidence", label: "Low", value: 50 },
];

function getScoreColor(score: number): string {
  if (score >= 1000) {
    return "text-green-600";
  }
  if (score >= 500) {
    return "text-blue-600";
  }
  if (score >= 100) {
    return "text-yellow-600";
  }
  return "text-gray-600";
}

export function RICEScoreCard({
  initialValues,
  onCalculate,
  readOnly = false,
  className,
}: RICEScoreCardProps) {
  const [reach, setReach] = useState(initialValues?.reach ?? 1000);
  const [impact, setImpact] = useState(initialValues?.impact ?? 1);
  const [confidence, setConfidence] = useState(initialValues?.confidence ?? 80);
  const [effort, setEffort] = useState(initialValues?.effort ?? 1);

  // Calculate RICE score
  const riceScore = effort > 0 ? (reach * impact * (confidence / 100)) / effort : 0;

  const handleCalculate = () => {
    if (onCalculate) {
      onCalculate({
        confidence,
        effort,
        impact,
        reach,
        rice_score: riceScore,
      });
    }
  };

  return (
    <div className={cn("rounded-lg border p-4 space-y-4", className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">RICE Score</h3>
          <p className="text-muted-foreground text-sm">Reach × Impact × Confidence ÷ Effort</p>
        </div>
        <div className="text-right">
          <div className={cn("text-3xl font-bold", getScoreColor(riceScore))}>
            {riceScore.toFixed(0)}
          </div>
          <div className="text-muted-foreground text-sm">RICE Score</div>
        </div>
      </div>

      {/* Formula Display */}
      <div className="bg-muted rounded-lg p-3 text-sm">
        <div className="text-center font-mono">
          ({reach} × {impact} × {confidence}%) ÷ {effort} = {riceScore.toFixed(0)}
        </div>
      </div>

      {/* Inputs */}
      <div className="space-y-4">
        {/* Reach */}
        <div className="space-y-1.5">
          <div className="flex justify-between text-sm">
            <span className="font-medium">Reach</span>
            <span className="font-mono">{reach.toLocaleString()}</span>
          </div>
          <p className="text-muted-foreground text-xs">
            Number of users/customers affected per time period
          </p>
          {!readOnly ? (
            <input
              type="number"
              value={reach}
              onChange={(e) => {
                setReach(Math.max(0, Number.parseInt(e.target.value, 10) || 0));
              }}
              className="w-full rounded-md border px-3 py-2 text-sm"
              min={0}
            />
          ) : (
            <div className="bg-muted h-2 overflow-hidden rounded-full">
              <div
                className="h-full rounded-full bg-blue-500"
                style={{ width: `${Math.min((reach / 10_000) * 100, 100)}%` }}
              />
            </div>
          )}
        </div>

        {/* Impact */}
        <div className="space-y-1.5">
          <div className="flex justify-between text-sm">
            <span className="font-medium">Impact</span>
            <span className="font-mono">{impact}x</span>
          </div>
          <p className="text-muted-foreground text-xs">How much will this impact each user?</p>
          {!readOnly ? (
            <div className="flex gap-1">
              {impactLevels.map((level) => (
                <button
                  key={level.value}
                  onClick={() => {
                    setImpact(level.value);
                  }}
                  className={cn(
                    "flex-1 py-2 text-xs rounded border transition-colors",
                    impact === level.value
                      ? "bg-primary text-primary-foreground border-primary"
                      : "bg-muted hover:bg-muted/80 border-transparent",
                  )}
                  title={level.description}
                >
                  {level.label}
                </button>
              ))}
            </div>
          ) : (
            <div className="text-sm">
              {impactLevels.find((l) => l.value === impact)?.label ?? impact}
            </div>
          )}
        </div>

        {/* Confidence */}
        <div className="space-y-1.5">
          <div className="flex justify-between text-sm">
            <span className="font-medium">Confidence</span>
            <span className="font-mono">{confidence}%</span>
          </div>
          <p className="text-muted-foreground text-xs">How confident are you in your estimates?</p>
          {!readOnly ? (
            <div className="flex gap-1">
              {confidenceLevels.map((level) => (
                <button
                  key={level.value}
                  onClick={() => {
                    setConfidence(level.value);
                  }}
                  className={cn(
                    "flex-1 py-2 text-xs rounded border transition-colors",
                    confidence === level.value
                      ? "bg-primary text-primary-foreground border-primary"
                      : "bg-muted hover:bg-muted/80 border-transparent",
                  )}
                  title={level.description}
                >
                  {level.label}
                </button>
              ))}
            </div>
          ) : (
            <div className="bg-muted h-2 overflow-hidden rounded-full">
              <div
                className="h-full rounded-full bg-green-500"
                style={{ width: `${confidence}%` }}
              />
            </div>
          )}
        </div>

        {/* Effort */}
        <div className="space-y-1.5">
          <div className="flex justify-between text-sm">
            <span className="font-medium">Effort</span>
            <span className="font-mono">{effort} person-weeks</span>
          </div>
          <p className="text-muted-foreground text-xs">Estimated effort in person-weeks</p>
          {!readOnly ? (
            <input
              type="number"
              value={effort}
              onChange={(e) => {
                setEffort(Math.max(0.1, Number.parseFloat(e.target.value) || 0.1));
              }}
              className="w-full rounded-md border px-3 py-2 text-sm"
              min={0.1}
              step={0.5}
            />
          ) : (
            <div className="bg-muted h-2 overflow-hidden rounded-full">
              <div
                className="h-full rounded-full bg-orange-500"
                style={{ width: `${Math.min((effort / 20) * 100, 100)}%` }}
              />
            </div>
          )}
        </div>
      </div>

      {/* Calculate Button */}
      {!readOnly && onCalculate && (
        <button
          onClick={handleCalculate}
          className="bg-primary text-primary-foreground hover:bg-primary/90 w-full rounded-md px-4 py-2 transition-colors"
        >
          Save RICE Score
        </button>
      )}
    </div>
  );
}

interface RICEScoreBadgeProps {
  score: number;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function RICEScoreBadge({ score, size = "md", className }: RICEScoreBadgeProps) {
  let color = "bg-gray-100 text-gray-700 border-gray-300";
  if (score >= 1000) {
    color = "bg-green-100 text-green-700 border-green-300";
  } else if (score >= 500) {
    color = "bg-blue-100 text-blue-700 border-blue-300";
  } else if (score >= 100) {
    color = "bg-yellow-100 text-yellow-700 border-yellow-300";
  }

  const sizeClass = {
    lg: "text-base px-3 py-1.5",
    md: "text-sm px-2 py-1",
    sm: "text-xs px-1.5 py-0.5",
  }[size];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded border font-medium",
        color,
        sizeClass,
        className,
      )}
    >
      <span>📊</span>
      <span>RICE: {score.toFixed(0)}</span>
    </span>
  );
}

interface RICEBreakdownProps {
  reach: number;
  impact: number;
  confidence: number;
  effort: number;
  className?: string;
}

export function RICEBreakdown({
  reach,
  impact,
  confidence,
  effort,
  className,
}: RICEBreakdownProps) {
  const score = effort > 0 ? (reach * impact * (confidence / 100)) / effort : 0;

  return (
    <div className={cn("grid grid-cols-5 gap-2 text-center text-sm", className)}>
      <div className="rounded bg-blue-50 p-2">
        <div className="font-bold text-blue-700">{reach.toLocaleString()}</div>
        <div className="text-xs text-blue-600">Reach</div>
      </div>
      <div className="rounded bg-purple-50 p-2">
        <div className="font-bold text-purple-700">{impact}x</div>
        <div className="text-xs text-purple-600">Impact</div>
      </div>
      <div className="rounded bg-green-50 p-2">
        <div className="font-bold text-green-700">{confidence}%</div>
        <div className="text-xs text-green-600">Confidence</div>
      </div>
      <div className="rounded bg-orange-50 p-2">
        <div className="font-bold text-orange-700">{effort}w</div>
        <div className="text-xs text-orange-600">Effort</div>
      </div>
      <div className="bg-primary/10 rounded p-2">
        <div className="text-primary font-bold">{score.toFixed(0)}</div>
        <div className="text-primary/80 text-xs">Score</div>
      </div>
    </div>
  );
}
