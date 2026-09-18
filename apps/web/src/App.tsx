import { useEffect, useMemo, useState } from "react";
import { Activity, Anchor, CheckCircle2, FileText, Layers, Radar, Route, Ship } from "lucide-react";

type Score = {
  proximity: number;
  temporal_overlap: number;
  trajectory_consistency: number;
  drift_consistency: number;
  behavioral_anomaly: number;
  total: number;
};

type Candidate = {
  mmsi: string;
  vessel_name: string;
  explanation: string;
  evidence_ids: string[];
  score: Score;
  disclaimer: string;
};

type Evidence = {
  id: string;
  source: string;
  title: string;
  excerpt: string;
};

type PipelineStep = {
  name: string;
  status: string;
  detail: string;
};

type DemoResult = {
  case: {
    case_number: string;
    status: string;
    detections: Array<{ confidence: number; estimated_age_hours: number; geometry: { area_km2: number } }>;
    drift_simulations: Array<{ confidence: number; trajectory_count: number }>;
    candidates: Candidate[];
    evidence: Evidence[];
    report: {
      executive_summary: string;
      claims: Array<{ claim: string; evidence_ids: string[]; confidence: number }>;
      disclaimer: string;
    };
  };
  steps: PipelineStep[];
  ground_truth_mmsi: string;
};

const fallback: DemoResult = {
  case: {
    case_number: "OT-2026-0001",
    status: "complete",
    detections: [{ confidence: 0.91, estimated_age_hours: 2.5, geometry: { area_km2: 11.8 } }],
    drift_simulations: [{ confidence: 0.73, trajectory_count: 250 }],
    candidates: [
      {
        mmsi: "419001247",
        vessel_name: "MT Samudra",
        explanation: "Highest-ranked synthetic candidate from temporal overlap and origin proximity.",
        evidence_ids: ["ais-419001247", "drift-ensemble-001"],
        disclaimer: "Investigative ranking only; not definitive attribution.",
        score: {
          proximity: 87,
          temporal_overlap: 91,
          trajectory_consistency: 82,
          drift_consistency: 78,
          behavioral_anomaly: 80,
          total: 84.95
        }
      }
    ],
    evidence: [
      {
        id: "drift-ensemble-001",
        source: "Baseline drift engine",
        title: "Backward Monte Carlo origin estimate",
        excerpt: "A 250-particle ensemble places the probable release region west-southwest of the observed slick."
      }
    ],
    report: {
      executive_summary: "Synthetic demo result with evidence-grounded candidate ranking.",
      claims: [
        {
          claim: "The top vessel is an investigative candidate only.",
          evidence_ids: ["drift-ensemble-001"],
          confidence: 0.73
        }
      ],
      disclaimer: "Candidate vessels are ranked for investigation, not legal attribution."
    }
  },
  steps: [{ name: "Local fallback loaded", status: "complete", detail: "API unavailable; embedded demo shown." }],
  ground_truth_mmsi: "419001247"
};

export function App() {
  const [data, setData] = useState<DemoResult>(fallback);
  const [selectedMmsi, setSelectedMmsi] = useState(fallback.case.candidates[0].mmsi);

  useEffect(() => {
    fetch("/api/v1/dev/fixtures/investigations")
      .then((response) => (response.ok ? response.json() : fallback))
      .then((result: DemoResult) => {
        setData(result);
        setSelectedMmsi(result.case.candidates[0]?.mmsi ?? "");
      })
      .catch(() => setData(fallback));
  }, []);

  const selected = useMemo(
    () => data.case.candidates.find((candidate) => candidate.mmsi === selectedMmsi) ?? data.case.candidates[0],
    [data.case.candidates, selectedMmsi]
  );
  const detection = data.case.detections[0];
  const drift = data.case.drift_simulations[0];

  return (
    <main className="shell">
      <aside className="rail" aria-label="Primary navigation">
        <div className="brand">OT</div>
        <button aria-label="Dashboard"><Radar size={20} /></button>
        <button aria-label="Map layers"><Layers size={20} /></button>
        <button aria-label="Vessel candidates"><Ship size={20} /></button>
        <button aria-label="Reports"><FileText size={20} /></button>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">SIH 26143 local prototype · {data.case.case_number}</p>
            <h1>OCEANTRACE</h1>
          </div>
          <button className="primary"><Activity size={18} /> Investigate spill</button>
        </header>

        <section className="mapPane" aria-label="Investigation map preview">
          <div className="gridSea" />
          <div className="slick" />
          <div className="origin">Origin region</div>
          <svg className="tracks" viewBox="0 0 900 420" role="img" aria-label="Synthetic drift and AIS tracks">
            <path d="M238 265 C 318 215, 402 178, 514 120" />
            <path className="ais" d="M120 300 C 260 245, 390 240, 690 92" />
            <path className="ais muted" d="M80 92 C 252 140, 418 210, 785 230" />
          </svg>
          <div className="layerPanel">
            <span><Layers size={16} /> Layers</span>
            <label><input type="checkbox" defaultChecked /> Spill polygon</label>
            <label><input type="checkbox" defaultChecked /> Origin region</label>
            <label><input type="checkbox" defaultChecked /> AIS tracks</label>
          </div>
        </section>

        <section className="lower">
          <section className="summary" aria-label="Investigation summary">
            <div><span>Spill area</span><strong>{detection.geometry.area_km2.toFixed(1)} km2</strong></div>
            <div><span>Detection confidence</span><strong>{Math.round(detection.confidence * 100)}%</strong></div>
            <div><span>Drift confidence</span><strong>{Math.round(drift.confidence * 100)}%</strong></div>
            <div><span>Particles</span><strong>{drift.trajectory_count}</strong></div>
          </section>

          <section className="candidates" aria-label="Candidate vessels">
            <div className="sectionTitle"><Anchor size={18} /> Candidate ranking</div>
            {data.case.candidates.map((candidate) => (
              <button
                key={candidate.mmsi}
                className={candidate.mmsi === selected.mmsi ? "candidate active" : "candidate"}
                onClick={() => setSelectedMmsi(candidate.mmsi)}
              >
                <div>
                  <strong>{candidate.vessel_name}</strong>
                  <span>{candidate.mmsi} · {candidate.disclaimer}</span>
                </div>
                <meter min="0" max="100" value={candidate.score.total} />
                <b>{candidate.score.total.toFixed(1)}</b>
              </button>
            ))}
          </section>

          <section className="report" aria-label="Evidence report">
            <div className="sectionTitle"><Route size={18} /> Why this vessel?</div>
            <p>{selected.explanation}</p>
            {Object.entries(selected.score).map(([name, value]) => (
              <div className="scoreRow" key={name}>
                <span>{name.replaceAll("_", " ")}</span>
                <meter min="0" max="100" value={value} />
                <b>{value.toFixed(1)}</b>
              </div>
            ))}
          </section>
        </section>

        <section className="evidenceBand">
          <section>
            <div className="sectionTitle"><CheckCircle2 size={18} /> Pipeline</div>
            {data.steps.map((step) => (
              <p key={step.name}><strong>{step.name}</strong> · {step.detail}</p>
            ))}
          </section>
          <section>
            <div className="sectionTitle"><FileText size={18} /> Evidence and report</div>
            <p>{data.case.report.executive_summary}</p>
            {data.case.evidence.map((item) => (
              <p key={item.id}><strong>{item.title}</strong> · {item.excerpt}</p>
            ))}
          </section>
        </section>
      </section>
    </main>
  );
}
