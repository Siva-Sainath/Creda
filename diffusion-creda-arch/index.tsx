import { createMemo, For } from "solid-js";
import { useTicker } from "@diffusionstudio/jsx";
import { ICON } from "./icons";

/** @inspect number path="Motion/Duration" min=40 max=90 step=1 */
const duration = 60;

/** @inspect select options="autoplay,01 Start,02 Clients,03 Edge,04 Case,05 Evidence,06 Judge,07 Full" path="Deck/Play" */
const play = "autoplay";

type Look = { t: number; lx: number; ly: number; z: number; kicker: string; copy: string };

const LOOKS: Look[] = [
  { t: 0.0, lx: 250, ly: 640, z: 1.12, kicker: "01  START", copy: "A job seeker pastes an offer." },
  { t: 6.5, lx: 250, ly: 640, z: 1.12, kicker: "01  START", copy: "A job seeker pastes an offer." },
  { t: 8.5, lx: 380, ly: 640, z: 1.14, kicker: "02  CLIENTS", copy: "Telegram bot. Amplify UI." },
  { t: 14.5, lx: 380, ly: 640, z: 1.14, kicker: "02  CLIENTS", copy: "Telegram bot. Amplify UI." },
  { t: 16.5, lx: 660, ly: 650, z: 1.18, kicker: "03  EDGE", copy: "HTTPS and webhooks hit API Gateway." },
  { t: 22.5, lx: 660, ly: 650, z: 1.18, kicker: "03  EDGE", copy: "HTTPS and webhooks hit API Gateway." },
  { t: 24.5, lx: 1000, ly: 640, z: 1.12, kicker: "04  CASE", copy: "Intake writes Cases and Evidence." },
  { t: 30.5, lx: 1000, ly: 640, z: 1.12, kicker: "04  CASE", copy: "Intake writes Cases and Evidence." },
  { t: 32.5, lx: 840, ly: 220, z: 1.38, kicker: "05  EVIDENCE", copy: "Queues feed Gatherer + Searcher." },
  { t: 39.5, lx: 840, ly: 220, z: 1.38, kicker: "05  EVIDENCE", copy: "Queues feed Gatherer + Searcher." },
  { t: 41.5, lx: 1320, ly: 230, z: 1.18, kicker: "06  JUDGE", copy: "Qwen-VL stamps the verdict." },
  { t: 48.0, lx: 1320, ly: 230, z: 1.18, kicker: "06  JUDGE", copy: "Qwen-VL stamps the verdict." },
  { t: 50.5, lx: 960, ly: 500, z: 1.0, kicker: "CREDA", copy: "ap-south-1 · the full path." },
  { t: 60.0, lx: 960, ly: 500, z: 1.0, kicker: "CREDA", copy: "ap-south-1 · the full path." },
];

const SLIDE_TIME: Record<string, number> = {
  "01 Start": 3,
  "02 Clients": 11,
  "03 Edge": 19,
  "04 Case": 27,
  "05 Evidence": 36,
  "06 Judge": 45,
  "07 Full": 55,
};

function clamp01(x: number) {
  return Math.max(0, Math.min(1, x));
}
function inOut(t: number) {
  t = clamp01(t);
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}
function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t;
}
function clock(time: number) {
  if (play === "autoplay") return time;
  return SLIDE_TIME[play] ?? time;
}
function cameraAt(time: number) {
  let i = 0;
  while (i < LOOKS.length - 2 && time >= LOOKS[i + 1].t) i += 1;
  const a = LOOKS[i];
  const b = LOOKS[i + 1];
  const u = inOut((time - a.t) / Math.max(0.001, b.t - a.t));
  const z = lerp(a.z, b.z, u);
  const lx = lerp(a.lx, b.lx, u);
  const ly = lerp(a.ly, b.ly, u);
  return {
    x: Math.round(960 - lx * z),
    y: Math.round(540 - ly * z),
    z,
    kicker: u < 0.5 ? a.kicker : b.kicker,
    copy: u < 0.5 ? a.copy : b.copy,
    progress: Math.round(64 + 1792 * clamp01(time / duration)),
  };
}

const L = {
  seeker: { l: 56, t: 575, w: 130 },
  clients: { l: 250, t: 480, w: 220, h: 300 },
  edge: { l: 560, t: 535, w: 210, h: 220 },
  cse: { l: 850, t: 480, w: 500, h: 300 },
  tools: { l: 600, t: 90, w: 480, h: 270 },
  llm: { l: 1220, t: 110, w: 480, h: 230 },
};

const P = {
  seeker: { x: L.seeker.l + 65, y: L.seeker.t + 36 },
  telegram: { x: L.clients.l + 45 + 65, y: L.clients.t + 44 + 36 },
  amplify: { x: L.clients.l + 45 + 65, y: L.clients.t + 168 + 36 },
  apigw: { x: L.edge.l + 40 + 65, y: L.edge.t + 56 + 36 },
  intake: { x: L.cse.l + 36 + 65, y: L.cse.t + 90 + 36 },
  cases: { x: L.cse.l + 300 + 65, y: L.cse.t + 44 + 36 },
  evidence: { x: L.cse.l + 300 + 65, y: L.cse.t + 168 + 36 },
  daily: { x: L.tools.l + 28 + 65, y: L.tools.t + 36 + 36 },
  worker: { x: L.tools.l + 28 + 65, y: L.tools.t + 148 + 36 },
  gatherer: { x: L.tools.l + 280 + 65, y: L.tools.t + 84 + 36 },
  qwen: { x: L.llm.l + 28 + 65, y: L.llm.t + 52 + 36 },
  gpu: { x: L.llm.l + 290 + 65, y: L.llm.t + 52 + 36 },
};

const EDGES: { d: string; from: number; layer: "flow" | "top"; dash?: boolean; label?: string; lx: number; ly: number }[] = [
  { d: `M${P.seeker.x},${P.telegram.y} H${L.clients.l}`, from: 0.4, layer: "flow", label: "paste offer", lx: 148, ly: P.telegram.y - 22 },
  { d: `M${P.seeker.x},${P.amplify.y} H${L.clients.l}`, from: 0.5, layer: "flow", label: "paste offer", lx: 148, ly: P.amplify.y + 8 },
  { d: `M${L.clients.l + L.clients.w},${P.telegram.y} C${L.clients.l + L.clients.w + 36},${P.telegram.y} ${L.edge.l - 36},${P.apigw.y} ${L.edge.l},${P.apigw.y}`, from: 8.5, layer: "flow", label: "webhook", lx: 478, ly: P.telegram.y - 22 },
  { d: `M${L.clients.l + L.clients.w},${P.amplify.y} C${L.clients.l + L.clients.w + 36},${P.amplify.y} ${L.edge.l - 36},${P.apigw.y} ${L.edge.l},${P.apigw.y}`, from: 8.6, layer: "flow", label: "HTTPS", lx: 492, ly: P.amplify.y + 8 },
  { d: `M${L.edge.l + L.edge.w},${P.apigw.y} H${L.cse.l}`, from: 16.5, layer: "flow" },
  { d: `M${P.intake.x + 75},${P.cases.y} H${P.cases.x - 75}`, from: 24.5, layer: "flow" },
  { d: `M${P.intake.x + 75},${P.evidence.y} H${P.evidence.x - 75}`, from: 24.6, layer: "flow" },
  { d: `M${P.amplify.x},${L.clients.t + L.clients.h} V818 H${P.cases.x} V${L.cse.t + L.cse.h}`, from: 26, layer: "flow", dash: true, label: "poll results", lx: 736, ly: 792 },
  { d: `M${P.worker.x},${L.tools.t + L.tools.h} V420 H${P.intake.x} V${L.cse.t}`, from: 50.5, layer: "flow", label: "enqueue", lx: 718, ly: 400 },
  { d: `M${P.daily.x + 65},${P.daily.y} H${P.gatherer.x - 75}`, from: 32.5, layer: "top", dash: true, label: "ATS index", lx: 790, ly: P.daily.y - 22 },
  { d: `M${P.worker.x + 65},${P.worker.y} C${P.worker.x + 110},${P.worker.y} ${P.gatherer.x - 110},${P.gatherer.y} ${P.gatherer.x - 75},${P.gatherer.y}`, from: 32.6, layer: "top" },
  { d: `M${P.gatherer.x},${L.tools.t + L.tools.h} V400 H${P.cases.x} V${L.cse.t}`, from: 50.5, layer: "flow" },
  { d: `M${L.tools.l + L.tools.w},${P.gatherer.y} H${L.llm.l}`, from: 41.5, layer: "top", label: "evidence packet", lx: 1096, ly: P.gatherer.y - 24 },
  { d: `M${P.qwen.x + 75},${P.qwen.y} H${P.gpu.x - 75}`, from: 41.6, layer: "top", label: "stamp + why", lx: 1418, ly: P.qwen.y - 24 },
];

function flowOpacity(time: number) {
  if (time < 32.2) return 1;
  if (time < 50.3) return 1 - clamp01((time - 32.2) / 0.55);
  return clamp01((time - 50.3) / 0.55);
}
function topOpacity(time: number) {
  return clamp01((time - 32.2) / 0.55);
}

export default function Project() {
  const { time } = useTicker();
  const t = () => clock(time());
  const cam = createMemo(() => cameraAt(t()));

  return (
    <stage background="#F4F7FB" camera={[0.42, 0, 0, 0.42, 137.74, 183.33]} id="do0s0o">
      <scene id="main" name="Creda architecture tour" width={1920} height={1080} fill="#F4F7FB" active>
        <group id="camera" x={cam().x} y={cam().y} scale={cam().z} end={duration}>
          <html id="diagram" x={0} y={0} width={1920} height={1080} end={duration}>
            <div
              style={{
                width: "1920px",
                height: "1080px",
                position: "relative",
                overflow: "visible",
                "background-color": "#F4F7FB",
                "font-family": "Inter, ui-sans-serif, system-ui",
                color: "#1B2430",
              }}
            >
              <svg width="1920" height="1080" viewBox="0 0 1920 1080" style={{ position: "absolute", inset: "0", overflow: "visible", "z-index": "0" }}>
                <For each={EDGES}>
                  {(e, i) => {
                    const band = () => (e.layer === "top" ? topOpacity(t()) : flowOpacity(t()));
                    const on = () => t() >= e.from && band() > 0.04;
                    const offset = () => -((t() * 80 + i() * 16) % 140);
                    return (
                      <path
                        d={e.d}
                        fill="none"
                        stroke={on() ? "#4C7DFF" : "#C5D4E8"}
                        stroke-width={2.4}
                        stroke-dasharray={e.dash || on() ? "12 9" : undefined}
                        stroke-dashoffset={on() ? offset() : 0}
                        stroke-linecap="round"
                        opacity={on() ? band() : 0}
                      />
                    );
                  }}
                </For>
              </svg>

              <For each={EDGES.filter((e) => e.label)}>
                {(e) => (
                  <div
                    style={{
                      position: "absolute",
                      left: `${e.lx}px`,
                      top: `${e.ly}px`,
                      padding: "3px 8px",
                      "border-radius": "6px",
                      "background-color": "#F4F7FB",
                      "font-size": "12px",
                      "font-weight": "600",
                      color: "#3A5BB8",
                      "white-space": "nowrap",
                      "letter-spacing": "0.01em",
                      "z-index": "3",
                      "line-height": "1",
                    }}
                  >
                    {t() >= e.from && (e.layer === "top" ? topOpacity(t()) : flowOpacity(t())) > 0.04 ? e.label : " "}
                  </div>
                )}
              </For>

              <Mark left={56} top={575} label="Job seeker" icon={ICON.users} opacity={flowOpacity(t())} />

              <GroupBox left={250} top={480} width={220} height={300} title="Clients" opacity={flowOpacity(t())}>
                <Node left={45} top={44} label="@CredashieldBot" icon={ICON.telegram} />
                <Node left={45} top={168} label="Amplify UI" icon={ICON.amplify} />
              </GroupBox>

              <GroupBox left={560} top={535} width={210} height={220} title="Edge" opacity={t() >= 8.4 ? flowOpacity(t()) : 0}>
                <Node left={40} top={56} label="API Gateway" icon={ICON.apigateway} />
              </GroupBox>

              <GroupBox left={850} top={480} width={500} height={300} title="Case" opacity={t() >= 16.4 ? flowOpacity(t()) : 0}>
                <Node left={36} top={90} label="Intake" icon={ICON.lambda} />
                <Node left={300} top={44} label="Cases" icon={ICON.dynamo} />
                <Node left={300} top={168} label="Evidence" icon={ICON.s3} />
              </GroupBox>

              <GroupBox left={600} top={90} width={480} height={270} title="Evidence tools" opacity={topOpacity(t())}>
                <Node left={28} top={36} label="Daily refresh" icon={ICON.eventbridge} />
                <Node left={28} top={148} label="Worker queue" icon={ICON.sqs} />
                <Node left={280} top={84} label="Gatherer + Searcher" icon={ICON.lambda} />
              </GroupBox>

              <GroupBox left={1220} top={110} width={480} height={230} title="LLM as judge" opacity={topOpacity(t())}>
                <Node left={28} top={52} label="Qwen queue" icon={ICON.sqs} />
                <Node left={290} top={52} label="g4dn + Qwen-VL" icon={ICON.ec2} />
              </GroupBox>
            </div>
          </html>
        </group>

        <html id="hud" x={0} y={0} width={1920} height={1080} end={duration}>
          <div
            style={{
              width: "1920px",
              height: "1080px",
              position: "relative",
              overflow: "hidden",
              "font-family": "Inter, ui-sans-serif, system-ui",
              "pointer-events": "none",
            }}
          >
            <div
              style={{
                position: "absolute",
                left: "0",
                top: "0",
                width: "1920px",
                height: "132px",
                background: "linear-gradient(180deg, #F4F7FB 70%, rgba(244,247,251,0))",
              }}
            />
            <div
              style={{
                position: "absolute",
                left: "64px",
                top: "36px",
                "font-size": "44px",
                "font-weight": "700",
                "letter-spacing": "-1px",
                color: "#121821",
                "line-height": "1",
                "white-space": "nowrap",
              }}
            >
              Creda
            </div>
            <div
              style={{
                position: "absolute",
                left: "66px",
                top: "88px",
                "font-size": "16px",
                "font-weight": "600",
                "letter-spacing": "3.4px",
                color: "#4C7DFF",
                "text-transform": "uppercase",
                "line-height": "1",
                "white-space": "nowrap",
              }}
            >
              ap-south-1
            </div>

            <div
              style={{
                position: "absolute",
                left: "0",
                top: "860px",
                width: "1920px",
                height: "40px",
                background: "linear-gradient(180deg, rgba(244,247,251,0), #F4F7FB)",
              }}
            />
            <div
              style={{
                position: "absolute",
                left: "0",
                top: "900px",
                width: "1920px",
                height: "180px",
                "background-color": "#F4F7FB",
              }}
            />
            <div
              style={{
                position: "absolute",
                left: "64px",
                top: "924px",
                "font-size": "13px",
                "font-weight": "600",
                "letter-spacing": "2.8px",
                color: "#4C7DFF",
                "line-height": "1",
                "white-space": "nowrap",
              }}
            >
              {cam().kicker}
            </div>
            <div
              style={{
                position: "absolute",
                left: "64px",
                top: "952px",
                width: "1792px",
                "font-size": "34px",
                "font-weight": "600",
                "letter-spacing": "-0.6px",
                color: "#121821",
                "line-height": "1.15",
                "white-space": "nowrap",
                overflow: "hidden",
              }}
            >
              {cam().copy}
            </div>
            <div
              style={{
                position: "absolute",
                left: "64px",
                top: "1034px",
                width: "1792px",
                height: "4px",
                "border-radius": "2px",
                "background-color": "#D5E0EE",
              }}
            />
            <div
              style={{
                position: "absolute",
                left: "64px",
                top: "1034px",
                width: `${cam().progress - 64}px`,
                height: "4px",
                "border-radius": "2px",
                "background-color": "#4C7DFF",
              }}
            />
          </div>
        </html>
      </scene>
    </stage>
  );
}

function GroupBox(props: { left: number; top: number; width: number; height: number; title: string; children: any; opacity?: number }) {
  return (
    <div
      style={{
        position: "absolute",
        left: `${props.left}px`,
        top: `${props.top}px`,
        width: `${props.width}px`,
        height: `${props.height}px`,
        "border-radius": "20px",
        "border-width": "1.5px",
        "border-style": "solid",
        "border-color": "#9BB7E6",
        "background-color": "#EAF1FB",
        "box-sizing": "border-box",
        "z-index": "2",
        opacity: props.opacity ?? 1,
      }}
    >
      <div
        style={{
          position: "absolute",
          left: "18px",
          top: "12px",
          "font-size": "13px",
          "font-weight": "600",
          color: "#2C4A86",
          "white-space": "nowrap",
        }}
      >
        {props.title}
      </div>
      {props.children}
    </div>
  );
}

function Node(props: { left: number; top: number; label: string; icon: string }) {
  return (
    <div
      style={{
        position: "absolute",
        left: `${props.left}px`,
        top: `${props.top}px`,
        width: "150px",
        "text-align": "center",
        "z-index": "2",
      }}
    >
      <div innerHTML={props.icon} style={{ margin: "0 auto", width: "72px", height: "72px" }} />
      <div
        style={{
          "margin-top": "8px",
          "font-size": "13px",
          "font-weight": "600",
          "line-height": "1.25",
          color: "#1B2430",
        }}
      >
        {props.label}
      </div>
    </div>
  );
}

function Mark(props: { left: number; top: number; label: string; icon: string; opacity?: number }) {
  return (
    <div
      style={{
        position: "absolute",
        left: `${props.left}px`,
        top: `${props.top}px`,
        width: "130px",
        "text-align": "center",
        "z-index": "2",
        opacity: props.opacity ?? 1,
      }}
    >
      <div innerHTML={props.icon} style={{ margin: "0 auto", width: "72px", height: "72px" }} />
      <div style={{ "margin-top": "8px", "font-size": "14px", "font-weight": "600", "white-space": "nowrap" }}>{props.label}</div>
    </div>
  );
}
