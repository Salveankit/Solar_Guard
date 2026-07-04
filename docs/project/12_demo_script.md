# 12 — Client and Leadership Demo Script

## 1. Demo objective

In 8–10 minutes, show that the team can transform raw solar telemetry into an explainable and actionable daily service plan. The application, not the slide deck, is the main evidence.

## 2. Pre-demo checklist

- Demo data loaded.
- Latest analysis completed.
- Pre-trained model and baseline available.
- One primary and one backup priority site known.
- Route plan generated once and reproducible.
- Internet-independent textual route verified.
- Daily O&M CSV export tested.
- Screenshots and backup walkthrough available.
- Browser zoom and laptop resolution checked.

## 3. Opening — 45 seconds

Suggested narrative:

> A rooftop-solar EPC managing hundreds or thousands of sites cannot inspect every inverter dashboard each morning. The actual decision is not just which chart looks low; it is which site genuinely needs attention, what evidence supports that conclusion, whether a remote action is enough, and where technicians should go tomorrow. SolarGuard demonstrates that complete decision workflow.

State clearly:

> This is a capability-demonstration POC using operationally realistic simulated data. It validates the workflow and engineering approach, not production field accuracy.

## 4. Command Centre — 90 seconds

Show:

- 30 monitored sites;
- healthy versus attention-required sites;
- communication issues;
- remote-check candidates;
- recommended field visits;
- energy value at risk;
- recoverable energy estimate.

Narrative:

> Instead of manually opening 30 dashboards, the operations manager gets one prioritised morning view. Notice that communication issues are separated from true production underperformance, so missing data does not automatically trigger a technician visit.

Open the top-priority site.

## 5. Site Diagnostics — 2 minutes

Use a sudden-outage example such as MH-142.

Show:

- expected versus actual output;
- irradiance remained healthy;
- anomaly window;
- expected and actual daily energy;
- probable issue and confidence;
- supporting evidence;
- limitation and recommended action.

Narrative:

> The system does not claim a confirmed component failure from limited telemetry. It says that an inverter or grid-side interruption is probable, explains the evidence, and recommends a remote diagnostic before dispatch. That distinction is deliberate and makes the output operationally trustworthy.

Show priority breakdown.

> The priority is not a magic AI number. It combines energy impact, persistence, confidence, complaint urgency, SLA risk, and route benefit.

## 6. Communication issue — 45 seconds

Open or mention a communication-failure site.

Narrative:

> Here, telemetry is missing rather than actually zero. SolarGuard recommends a connectivity or data-logger check and avoids an immediate truck roll. This is a simple but valuable operational distinction.

## 7. Cleaning economics — 60 seconds

Open a gradual-underperformance candidate.

Show:

- multi-day decline;
- probable soiling/degradation;
- projected recoverable value;
- cleaning cost;
- rainfall forecast;
- schedule/defer decision.

Narrative:

> We do not schedule cleaning just because output is low. We compare the expected recoverable value with cleaning cost and near-term rain. This converts analytics into a business decision.

## 8. Service Queue — 60 seconds

Show ranked incidents and filters.

Narrative:

> The queue combines technical severity with business urgency. The manager can separate remote checks, cleaning candidates, field visits, and insufficient-evidence cases. Unknown cases remain visible rather than being forced into a confident diagnosis.

## 9. Technician Plan — 90 seconds

Generate or open tomorrow's plan.

Show:

- two technicians;
- ordered stops;
- skill compatibility;
- distance and time;
- naive versus optimised distance;
- unassigned-job reason if present.

Narrative:

> Only incidents that genuinely require a physical visit enter the optimiser. OR-Tools then respects technician skills, shift capacity, and visit limits. The result is an actionable route, not simply markers connected on a map.

Show/download the O&M CSV.

## 10. Capability summary — 45 seconds

Say:

> This POC demonstrates data validation, domain-aware time-series modelling, explainable anomaly reasoning, business prioritisation, backend APIs, product UI, optimisation, testing, and reproducible deployment in one coherent workflow.

## 11. Limitations and production path — 45 seconds

State directly:

- synthetic data does not establish field accuracy;
- fault outputs are probable categories;
- current input is canonical CSV, not live multi-vendor APIs;
- route distance does not include live traffic.

Next phase:

1. Connect one real inverter export.
2. Pilot with one EPC and 50–200 sites.
3. Capture technician-confirmed outcomes.
4. Calibrate thresholds and confidence.
5. Add one vendor adapter and scheduled analysis.

## 12. Likely questions and answers

### “Where exactly is AI?”

> The ML component estimates weather-normalised healthy generation. Persistent residual patterns then support anomaly detection. We combine that with explainable evidence rules and optimisation. We intentionally do not use an LLM or synthetic-label classifier where it would add theatre rather than value.

### “Why not directly predict the fault?”

> Total generation alone cannot reliably separate dust, shading, grid, and component failures. The POC returns a probable issue with evidence and uncertainty. Real technician labels and richer electrical telemetry would support a stronger classifier in a pilot.

### “Is synthetic data useful?”

> It is useful for proving the end-to-end product and deterministic scenarios. It is not evidence of real-world diagnostic accuracy, which is why the next step is a limited real-data pilot.

### “What differentiates this from an inverter dashboard?”

> Inverter dashboards show telemetry and alarms. SolarGuard demonstrates a cross-site operational layer: expected-performance comparison, remote-versus-field decisions, economic prioritisation, and technician routing.

### “Can this support multiple inverter brands?”

> The analytics uses a canonical schema. Each vendor would require an adapter that maps its fields into that schema. The POC proves the standardised layer and CSV path; it does not claim existing support for every vendor API.

### “Why FastAPI and Streamlit?”

> Streamlit enables a fast polished POC, while FastAPI demonstrates reusable backend services and keeps business logic out of the UI. It is enough architecture to show capability without adding microservice overhead.

### “What is the main risk?”

> Data quality and fault ground truth. The production value will depend more on reliable telemetry, service outcomes, and vendor access than on adding a more complex model.

## 13. Statements to avoid

Do not say:

- 95% accurate fault diagnosis;
- confirmed dust or confirmed inverter failure;
- production ready;
- supports all inverter brands;
- guaranteed savings;
- live real-time monitoring if the demo is batch-based.

## 14. Closing line

> SolarGuard shows how our team can convert fragmented operational data into a trusted next action—what to inspect remotely, what to defer, and where technicians should go tomorrow.
